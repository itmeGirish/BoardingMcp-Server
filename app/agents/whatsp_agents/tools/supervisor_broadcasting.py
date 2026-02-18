"""
Backend tools for broadcasting supervisor workflow

This module defines the LangChain tools that integrate with
the Direct API MCP server (port 9002) and database for the broadcasting workflow.

IMPORTANT: These tools run in LangGraph's ASGI context.
We use ThreadPoolExecutor to run MCP calls in separate threads with their own event loops.
This pattern matches the working onboarding implementation and avoids all async/event loop conflicts.
"""

import asyncio
import json
import re
import uuid
import concurrent.futures
import nest_asyncio
from langchain.tools import tool

from ....config import logger

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Thread pool for running MCP calls and DB operations in separate threads
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)


# ============================================
# DIRECT API MCP HELPER
# ============================================

def _call_direct_api_mcp(tool_name: str, params: dict) -> dict:
    """
    Generic helper to call a Direct API MCP tool (port 9002) synchronously.
    Creates a fresh MCP client in a new event loop to avoid conflicts.
    """
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.utils.whsp_onboarding_agent import parse_mcp_result_with_debug as parse_mcp_result

    async def _call():
        client = MultiServerMCPClient({
            "DirectApiMCP": {
                "url": "http://127.0.0.1:9002/mcp",
                "transport": "streamable-http"
            }
        })

        async with client.session("DirectApiMCP") as session:
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}

            if tool_name not in mcp_tools:
                return {"status": "failed", "error": f"MCP tool '{tool_name}' not found"}

            result = await mcp_tools[tool_name].ainvoke(params)
            return parse_mcp_result(result)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call())
    finally:
        loop.close()


# ============================================
# PHONE NUMBER VALIDATION HELPER
# ============================================

def _validate_phone_number(phone: str) -> bool:
    """Basic E.164 phone number validation."""
    cleaned = re.sub(r'[\s\-\(\)]', '', phone.strip())
    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    return bool(re.match(r'^\+[1-9]\d{6,14}$', cleaned))


def _normalize_phone_number(phone: str) -> str:
    """Normalize phone number to E.164 format."""
    cleaned = re.sub(r'[\s\-\(\)]', '', phone.strip())
    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    return cleaned


# ============================================
# STEP 1: INITIALIZE BROADCAST
# ============================================

def _run_initialize_broadcast_sync(user_id: str):
    """Initialize broadcast - check JWT exists, create BroadcastJob."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.memory_repo import MemoryRepository
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    with get_session() as session:
        memory_repo = MemoryRepository(session=session)
        memory_record = memory_repo.get_by_user_id(user_id)

        if not memory_record or not memory_record.get("jwt_token"):
            return {
                "status": "failed",
                "message": "User has not completed onboarding. No JWT token found. Please complete onboarding first."
            }

        is_first = memory_repo.is_first_broadcasting(
            user_id=user_id,
            project_id=memory_record["project_id"]
        )

        broadcast_repo = BroadcastJobRepository(session=session)
        job_id = str(uuid.uuid4())
        broadcast_repo.create_broadcast_job(
            job_id=job_id,
            user_id=user_id,
            project_id=memory_record["project_id"],
            phase="INITIALIZED"
        )

        return {
            "status": "success",
            "broadcast_job_id": job_id,
            "project_id": memory_record["project_id"],
            "first_broadcasting": is_first,
            "message": "Broadcast initialized. Please provide your contact list (phone numbers)."
        }


@tool
def initialize_broadcast(user_id: str) -> str:
    """
    Initialize a new broadcast campaign.

    Checks that the user has completed onboarding (JWT token exists)
    and creates a new BroadcastJob record in INITIALIZED phase.

    Args:
        user_id: User's unique identifier

    Returns:
        JSON string with broadcast_job_id, first_broadcasting flag, and status
    """
    logger.info("[BROADCAST] initialize_broadcast called for user: %s", user_id)
    try:
        future = _executor.submit(_run_initialize_broadcast_sync, user_id=user_id)
        result = future.result(timeout=30)
        if not isinstance(result, dict):
            result = {"error": "Invalid response format", "status": "failed"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] initialize_broadcast error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# STEP 2: PROCESS CONTACTS
# ============================================

def _run_process_contacts_sync(user_id: str, broadcast_job_id: str, phone_numbers: list):
    """Validate, normalize, and deduplicate phone numbers."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository

    valid = []
    invalid = []
    seen = set()
    processed_contacts = []

    for idx, phone in enumerate(phone_numbers):
        phone = str(phone).strip()
        if not phone:
            continue

        normalized = _normalize_phone_number(phone)
        if _validate_phone_number(normalized):
            if normalized not in seen:
                valid.append(normalized)
                seen.add(normalized)
                # Detect country code from E.164 number
                country = "IN" if normalized.startswith("+91") else "UNKNOWN"
                processed_contacts.append({
                    "phone_e164": normalized,
                    "name": None,
                    "email": None,
                    "country_code": country,
                    "quality_score": 50,  # Default score for basic validation
                    "custom_fields": None,
                    "source_row": idx + 1,
                    "validation_errors": None,
                    "is_duplicate": False,
                    "duplicate_of": None,
                })
            else:
                # Duplicate
                processed_contacts.append({
                    "phone_e164": normalized,
                    "country_code": "IN" if normalized.startswith("+91") else "UNKNOWN",
                    "quality_score": 0,
                    "source_row": idx + 1,
                    "is_duplicate": True,
                    "duplicate_of": normalized,
                })
        else:
            invalid.append(phone)

    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        repo.update_contacts(
            job_id=broadcast_job_id,
            contacts_data=json.dumps(valid),
            total=len(phone_numbers),
            valid=len(valid),
            invalid=len(invalid)
        )

        # Also insert into processed_contacts table for sub-agent tools
        if processed_contacts:
            pc_repo = ProcessedContactRepository(session=session)
            pc_repo.bulk_create(
                contacts=processed_contacts,
                broadcast_job_id=broadcast_job_id,
                user_id=user_id,
            )

    return {
        "status": "success" if len(valid) > 0 else "failed",
        "total_provided": len(phone_numbers),
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "duplicates_removed": len(phone_numbers) - len(valid) - len(invalid),
        "invalid_numbers": invalid[:10],  # Show first 10 invalid
        "message": f"Processed {len(phone_numbers)} contacts: {len(valid)} valid, {len(invalid)} invalid."
    }


@tool
def process_broadcast_contacts(user_id: str, broadcast_job_id: str, phone_numbers: list[str]) -> str:
    """
    Validate and normalize contact phone numbers for the broadcast.

    Accepts phone numbers in various formats, normalizes to E.164,
    removes duplicates, and stores valid contacts in the BroadcastJob.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID from initialize_broadcast
        phone_numbers: List of phone number strings to validate

    Returns:
        JSON string with validation results (valid_count, invalid_count, etc.)
    """
    logger.info("[BROADCAST] process_broadcast_contacts called: %d numbers", len(phone_numbers))
    try:
        future = _executor.submit(
            _run_process_contacts_sync,
            user_id=user_id,
            broadcast_job_id=broadcast_job_id,
            phone_numbers=phone_numbers
        )
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] process_broadcast_contacts error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# STEP 3: COMPLIANCE CHECK
# ============================================

def _run_check_compliance_sync(user_id: str, broadcast_job_id: str):
    """Check messaging health and compliance via MCP."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    # Call MCP to check messaging health
    health_result = _call_direct_api_mcp("get_messaging_health_status", {"node_id": user_id})

    compliance_status = "passed"
    details = []

    if health_result.get("status") == "failed":
        compliance_status = "failed"
        details.append(f"Health check failed: {health_result.get('error', 'Unknown error')}")

    # Store compliance result
    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        repo.update_compliance(
            job_id=broadcast_job_id,
            compliance_status=compliance_status,
            compliance_details=json.dumps(details) if details else None
        )

    return {
        "status": "success" if compliance_status == "passed" else "failed",
        "compliance_status": compliance_status,
        "health_data": health_result.get("data", {}),
        "details": details,
        "message": "Compliance checks passed." if compliance_status == "passed"
                   else "Compliance checks failed. See details."
    }


@tool
def check_broadcast_compliance(user_id: str, broadcast_job_id: str) -> str:
    """
    Check messaging compliance and account health for broadcasting.

    Verifies messaging tier, account health status, and rate limits
    via the WhatsApp Business API health endpoint.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with compliance status and health data
    """
    logger.info("[BROADCAST] check_broadcast_compliance called for user: %s", user_id)
    try:
        future = _executor.submit(
            _run_check_compliance_sync,
            user_id=user_id,
            broadcast_job_id=broadcast_job_id
        )
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] check_broadcast_compliance error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# STEP 4: SEGMENT AUDIENCE
# ============================================

def _run_segment_audience_sync(user_id: str, broadcast_job_id: str, segment_type: str, criteria: str = None):
    """Group contacts into segments."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        job = repo.get_by_id(broadcast_job_id)

        if not job:
            return {"status": "failed", "message": "Broadcast job not found"}

        valid_contacts = job["valid_contacts"]

        if segment_type == "all":
            segments = [{"name": "All Contacts", "criteria": "all", "contact_count": valid_contacts}]
        else:
            segments = [{"name": segment_type, "criteria": criteria or segment_type, "contact_count": valid_contacts}]

        repo.update_segments(broadcast_job_id, json.dumps(segments))

    return {
        "status": "success",
        "segments": segments,
        "total_contacts": valid_contacts,
        "message": f"Audience segmented: {len(segments)} segment(s) with {valid_contacts} contacts total."
    }


@tool
def segment_broadcast_audience(
    user_id: str,
    broadcast_job_id: str,
    segment_type: str = "all",
    criteria: str = None
) -> str:
    """
    Segment the broadcast audience into groups.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        segment_type: Segmentation type - "all" sends to everyone, or custom segment name
        criteria: Optional segmentation criteria description

    Returns:
        JSON string with segment details
    """
    logger.info("[BROADCAST] segment_broadcast_audience called: type=%s", segment_type)
    try:
        future = _executor.submit(
            _run_segment_audience_sync,
            user_id=user_id,
            broadcast_job_id=broadcast_job_id,
            segment_type=segment_type,
            criteria=criteria
        )
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] segment_broadcast_audience error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# STEP 5: TEMPLATE MANAGEMENT
# ============================================

@tool
def get_available_templates(user_id: str) -> str:
    """
    Fetch all available WhatsApp message templates for the user.

    Args:
        user_id: User's unique identifier

    Returns:
        JSON string with list of templates (name, category, language, status)
    """
    logger.info("[BROADCAST] get_available_templates called for user: %s", user_id)
    try:
        future = _executor.submit(
            _call_direct_api_mcp,
            tool_name="get_templates",
            params={"user_id": user_id}
        )
        result = future.result(timeout=30)
        if not isinstance(result, dict):
            result = {"error": "Invalid response format", "status": "failed"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] get_available_templates error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


@tool
def get_template_details(user_id: str, template_id: str) -> str:
    """
    Fetch details of a specific WhatsApp template by ID.

    Args:
        user_id: User's unique identifier
        template_id: The template ID to fetch

    Returns:
        JSON string with full template details (components, status, etc.)
    """
    logger.info("[BROADCAST] get_template_details called: template_id=%s", template_id)
    try:
        future = _executor.submit(
            _call_direct_api_mcp,
            tool_name="get_template_by_id",
            params={"user_id": user_id, "template_id": template_id}
        )
        result = future.result(timeout=30)
        if not isinstance(result, dict):
            result = {"error": "Invalid response format", "status": "failed"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] get_template_details error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


@tool
def create_broadcast_template(
    user_id: str,
    name: str,
    category: str,
    language: str,
    components: list[dict]
) -> str:
    """
    Create a new WhatsApp message template for broadcasting.

    Args:
        user_id: User's unique identifier
        name: Template name (lowercase, underscores, no spaces)
        category: Template category - MARKETING, UTILITY, or AUTHENTICATION
        language: Template language code (e.g., "en_US", "hi")
        components: Template components list (header, body, footer, buttons)

    Returns:
        JSON string with created template details and approval status
    """
    logger.info("[BROADCAST] create_broadcast_template called: name=%s, category=%s", name, category)
    try:
        future = _executor.submit(
            _call_direct_api_mcp,
            tool_name="submit_whatsapp_template_message",
            params={
                "user_id": user_id,
                "name": name,
                "category": category,
                "language": language,
                "components": components
            }
        )
        result = future.result(timeout=60)
        if not isinstance(result, dict):
            result = {"error": "Invalid response format", "status": "failed"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] create_broadcast_template error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


@tool
def edit_broadcast_template(
    user_id: str,
    template_id: str,
    components: list[dict]
) -> str:
    """
    Edit an existing WhatsApp message template.

    Args:
        user_id: User's unique identifier
        template_id: The template ID to edit
        components: Updated template components list

    Returns:
        JSON string with updated template details
    """
    logger.info("[BROADCAST] edit_broadcast_template called: template_id=%s", template_id)
    try:
        future = _executor.submit(
            _call_direct_api_mcp,
            tool_name="edit_template",
            params={
                "user_id": user_id,
                "template_id": template_id,
                "components": components
            }
        )
        result = future.result(timeout=60)
        if not isinstance(result, dict):
            result = {"error": "Invalid response format", "status": "failed"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] edit_broadcast_template error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# STEP 6: CHECK TEMPLATE APPROVAL
# ============================================

@tool
def check_template_approval_status(user_id: str, template_id: str) -> str:
    """
    Check the approval status of a WhatsApp template.

    Polls the template status to see if it has been approved or rejected
    by WhatsApp. Use this when a template is in PENDING state.

    Args:
        user_id: User's unique identifier
        template_id: The template ID to check

    Returns:
        JSON string with template status (APPROVED, PENDING, REJECTED)
    """
    logger.info("[BROADCAST] check_template_approval_status: template_id=%s", template_id)
    try:
        future = _executor.submit(
            _call_direct_api_mcp,
            tool_name="get_template_by_id",
            params={"user_id": user_id, "template_id": template_id}
        )
        result = future.result(timeout=30)
        if not isinstance(result, dict):
            result = {"error": "Invalid response format", "status": "failed"}

        # Extract template status from result
        template_data = result.get("data", {})
        template_status = template_data.get("status", "UNKNOWN") if isinstance(template_data, dict) else "UNKNOWN"

        return json.dumps({
            "status": "success",
            "template_status": template_status,
            "template_data": template_data,
            "message": f"Template status: {template_status}"
        }, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] check_template_approval_status error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# STEP 8: SEND BROADCAST MESSAGES
# ============================================

def _run_send_broadcast_sync(user_id: str, broadcast_job_id: str):
    """Send broadcast messages in batches using send_message MCP tool."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.utils.whsp_onboarding_agent import parse_mcp_result_with_debug as parse_mcp_result
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    # Load broadcast job from DB
    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        job = repo.get_by_id(broadcast_job_id)

    if not job:
        return {"status": "failed", "message": "Broadcast job not found"}

    contacts = json.loads(job["contacts_data"]) if job.get("contacts_data") else []
    template_name = job.get("template_name")
    template_language = job.get("template_language", "en_US")

    if not contacts:
        return {"status": "failed", "message": "No contacts to send to"}
    if not template_name:
        return {"status": "failed", "message": "No template selected"}

    async def _send_all():
        client = MultiServerMCPClient({
            "DirectApiMCP": {
                "url": "http://127.0.0.1:9002/mcp",
                "transport": "streamable-http"
            }
        })

        async with client.session("DirectApiMCP") as session:
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}
            send_tool = mcp_tools.get("send_message")

            if not send_tool:
                return {"status": "failed", "message": "send_message MCP tool not found"}

            sent = 0
            failed = 0
            errors = []

            for phone in contacts:
                try:
                    result = await send_tool.ainvoke({
                        "user_id": user_id,
                        "to": phone,
                        "message_type": "template",
                        "template_name": template_name,
                        "template_language_code": template_language,
                    })
                    parsed = parse_mcp_result(result)
                    if parsed.get("status") == "success":
                        sent += 1
                    else:
                        failed += 1
                        errors.append(f"{phone}: {parsed.get('error', 'Unknown error')}")
                except Exception as e:
                    failed += 1
                    errors.append(f"{phone}: {str(e)}")

            return {
                "status": "success",
                "total": len(contacts),
                "sent": sent,
                "failed": failed,
                "errors": errors[:5],
            }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        send_result = loop.run_until_complete(_send_all())
    finally:
        loop.close()

    # Update progress in DB
    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        repo.update_send_progress(
            broadcast_job_id,
            sent=send_result.get("sent", 0),
            failed=send_result.get("failed", 0)
        )

    send_result["message"] = (
        f"Broadcast complete: {send_result.get('sent', 0)} sent, "
        f"{send_result.get('failed', 0)} failed out of {send_result.get('total', 0)}."
    )
    return send_result


@tool
def send_broadcast_messages(user_id: str, broadcast_job_id: str) -> str:
    """
    Send broadcast messages to all validated contacts.

    Reads contacts and template from the BroadcastJob, then sends
    messages in sequence via the WhatsApp send_message API.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with send results (sent count, failed count, errors)
    """
    logger.info("[BROADCAST] send_broadcast_messages called for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(
            _run_send_broadcast_sync,
            user_id=user_id,
            broadcast_job_id=broadcast_job_id
        )
        result = future.result(timeout=300)  # 5 min timeout for sending
        if not isinstance(result, dict):
            result = {"error": "Invalid response format", "status": "failed"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] send_broadcast_messages error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# STATE MANAGEMENT TOOLS
# ============================================

def _run_update_phase_sync(broadcast_job_id: str, new_phase: str, error_message: str = None, scheduled_for: str = None):
    """Update broadcast phase in database."""
    from datetime import datetime as dt
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    # Parse scheduled_for ISO string to datetime if provided
    scheduled_dt = None
    if scheduled_for:
        try:
            scheduled_dt = dt.fromisoformat(scheduled_for.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            logger.warning("[BROADCAST] Invalid scheduled_for format: %s", scheduled_for)

    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        success = repo.update_phase(broadcast_job_id, new_phase, error_message, scheduled_for=scheduled_dt)

        if success:
            job = repo.get_by_id(broadcast_job_id)
            result = {
                "status": "success",
                "phase": new_phase,
                "previous_phase": job.get("previous_phase") if job else None,
                "message": f"Phase updated to {new_phase}"
            }
            if new_phase == "SCHEDULED" and job:
                result["scheduled_for"] = job.get("scheduled_for")
                result["message"] = f"Broadcast scheduled for {job.get('scheduled_for')}"
            return result
        else:
            return {
                "status": "failed",
                "message": f"Failed to update phase to {new_phase}. Invalid transition or job not found."
            }


@tool
def update_broadcast_phase(
    broadcast_job_id: str,
    new_phase: str,
    error_message: str = None,
    scheduled_for: str = None
) -> str:
    """
    Update the broadcast phase (state transition).

    Validates the transition against allowed state machine transitions.
    Records the previous phase and timestamps for terminal states.
    When transitioning to SCHEDULED, stores the scheduled send time.

    Args:
        broadcast_job_id: The broadcast job ID
        new_phase: Target phase (INITIALIZED, DATA_PROCESSING, COMPLIANCE_CHECK,
                   SEGMENTATION, CONTENT_CREATION, PENDING_APPROVAL, READY_TO_SEND,
                   SCHEDULED, SENDING, PAUSED, COMPLETED, FAILED, CANCELLED)
        error_message: Optional error message (used when transitioning to FAILED)
        scheduled_for: Optional ISO 8601 UTC datetime for SCHEDULED phase
                       (e.g., "2026-02-11T03:30:00+00:00"). Required when new_phase=SCHEDULED.

    Returns:
        JSON string with transition result
    """
    logger.info("[BROADCAST] update_broadcast_phase: job=%s -> %s (scheduled_for=%s)", broadcast_job_id, new_phase, scheduled_for)
    try:
        future = _executor.submit(
            _run_update_phase_sync,
            broadcast_job_id=broadcast_job_id,
            new_phase=new_phase,
            error_message=error_message,
            scheduled_for=scheduled_for
        )
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] update_broadcast_phase error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


def _run_get_broadcast_status_sync(broadcast_job_id: str):
    """Get current broadcast status from database."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        job = repo.get_by_id(broadcast_job_id)

        if job:
            return {"status": "success", "broadcast": job}
        else:
            return {"status": "failed", "message": "Broadcast job not found"}


@tool
def get_broadcast_status(broadcast_job_id: str) -> str:
    """
    Get the current status and details of a broadcast job.

    Use this to resume a broadcast or check progress.

    Args:
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with full broadcast job details (phase, contacts, template, progress)
    """
    logger.info("[BROADCAST] get_broadcast_status called: job=%s", broadcast_job_id)
    try:
        future = _executor.submit(
            _run_get_broadcast_status_sync,
            broadcast_job_id=broadcast_job_id
        )
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] get_broadcast_status error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# ANALYTICS
# ============================================

@tool
def get_broadcast_analytics(user_id: str) -> str:
    """
    Get WhatsApp Business Account analytics for delivery metrics.

    Provides insights on message delivery, read rates, and account health.

    Args:
        user_id: User's unique identifier

    Returns:
        JSON string with WABA analytics data
    """
    logger.info("[BROADCAST] get_broadcast_analytics called for user: %s", user_id)
    try:
        future = _executor.submit(
            _call_direct_api_mcp,
            tool_name="get_waba_analytics",
            params={"user_id": user_id}
        )
        result = future.result(timeout=30)
        if not isinstance(result, dict):
            result = {"error": "Invalid response format", "status": "failed"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[BROADCAST] get_broadcast_analytics error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# SUB-AGENT DELEGATION TOOLS
# ============================================

@tool
def delegate_to_data_processing(user_id: str, broadcast_job_id: str, project_id: str) -> str:
    """
    Delegate contact processing to the Data Processing Agent.

    Call this when transitioning to the DATA_PROCESSING phase.
    The Data Processing Agent will handle:
    - Beginner flow (FB verification for first-time broadcasters)
    - File parsing (Excel/CSV)
    - Phone validation & E.164 normalization
    - 4-stage deduplication
    - Quality scoring (0-100)

    The supervisor should call this INSTEAD of process_broadcast_contacts
    when entering the DATA_PROCESSING phase.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        project_id: Project ID for the broadcast

    Returns:
        JSON string confirming delegation to Data Processing Agent
    """
    logger.info("[BROADCAST] Delegating to Data Processing Agent for job: %s", broadcast_job_id)
    return json.dumps({
        "status": "delegated",
        "agent": "data_processing",
        "user_id": user_id,
        "broadcast_job_id": broadcast_job_id,
        "project_id": project_id,
        "message": "Handing off to Data Processing Agent for contact validation and processing."
    }, ensure_ascii=False)


@tool
def delegate_to_compliance(user_id: str, broadcast_job_id: str, project_id: str) -> str:
    """
    Delegate compliance checking to the Compliance Agent.

    Call this when transitioning to the COMPLIANCE_CHECK phase.
    The Compliance Agent will handle:
    - Opt-in verification (consent log check)
    - Suppression list filtering (global, campaign, temporary, bounce)
    - Time window restrictions (TRAI India, GDPR EU, etc.)
    - Account health & messaging tier checks via MCP

    The supervisor should call this INSTEAD of check_broadcast_compliance
    when entering the COMPLIANCE_CHECK phase.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        project_id: Project ID for the broadcast

    Returns:
        JSON string confirming delegation to Compliance Agent
    """
    logger.info("[BROADCAST] Delegating to Compliance Agent for job: %s", broadcast_job_id)
    return json.dumps({
        "status": "delegated",
        "agent": "compliance",
        "user_id": user_id,
        "broadcast_job_id": broadcast_job_id,
        "project_id": project_id,
        "message": "Handing off to Compliance Agent for opt-in, suppression, time window, and health checks."
    }, ensure_ascii=False)


@tool
def delegate_to_segmentation(user_id: str, broadcast_job_id: str, project_id: str) -> str:
    """
    Delegate audience segmentation to the Segmentation Agent.

    Call this when transitioning to the SEGMENTATION phase.
    The Segmentation Agent will handle:
    - Lifecycle stage classification (New, Engaged, Active, At-Risk, Dormant, Churned)
    - 24-hour window detection (free messaging for recent conversations)
    - Timezone clustering for optimal delivery timing (10AM-2PM local)
    - Frequency capping (marketing 2/week, promotional 1/week, combined 4/week)
    - Audience segment creation

    The supervisor should call this INSTEAD of segment_broadcast_audience
    when entering the SEGMENTATION phase.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        project_id: Project ID for the broadcast

    Returns:
        JSON string confirming delegation to Segmentation Agent
    """
    logger.info("[BROADCAST] Delegating to Segmentation Agent for job: %s", broadcast_job_id)
    return json.dumps({
        "status": "delegated",
        "agent": "segmentation",
        "user_id": user_id,
        "broadcast_job_id": broadcast_job_id,
        "project_id": project_id,
        "message": "Handing off to Segmentation Agent for lifecycle analysis, window detection, and audience grouping."
    }, ensure_ascii=False)


@tool
def delegate_to_content_creation(user_id: str, broadcast_job_id: str, project_id: str) -> str:
    """
    Delegate template management to the Content Creation Agent.

    Call this when transitioning to the CONTENT_CREATION phase.
    The Content Creation Agent will handle:
    - Listing available templates (text, image, video, document)
    - Creating new templates and submitting to WhatsApp for approval
    - Checking template approval status (PENDING -> APPROVED/REJECTED)
    - Rejection analysis and auto-fix suggestions
    - Editing and resubmitting rejected templates
    - Deleting templates by ID or by name
    - Selecting an APPROVED template for the broadcast job

    The supervisor should call this INSTEAD of get_available_templates / create_broadcast_template
    when entering the CONTENT_CREATION phase.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        project_id: Project ID for the broadcast

    Returns:
        JSON string confirming delegation to Content Creation Agent
    """
    logger.info("[BROADCAST] Delegating to Content Creation Agent for job: %s", broadcast_job_id)
    return json.dumps({
        "status": "delegated",
        "agent": "content_creation",
        "user_id": user_id,
        "broadcast_job_id": broadcast_job_id,
        "project_id": project_id,
        "message": "Handing off to Content Creation Agent for template management, approval, and selection."
    }, ensure_ascii=False)


@tool
def delegate_to_delivery(user_id: str, broadcast_job_id: str, project_id: str) -> str:
    """
    Delegate message dispatch to the Delivery Agent.

    Call this when transitioning to the SENDING phase.
    The Delivery Agent will handle:
    - Multi-priority queue preparation (5 levels)
    - BUSINESS POLICY: send_marketing_lite_message FIRST (cheaper)
    - Fallback to send_message for template-based delivery (media/buttons)
    - Rate limiting by WhatsApp messaging tier
    - Retry with exponential backoff (immediate, 30s, 2m, 10m, 1hr)
    - Error code handling (non-retryable: 131026, 131047, etc.)
    - Delivery tracking and mark-as-read

    The supervisor should call this INSTEAD of send_broadcast_messages
    when entering the SENDING phase.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        project_id: Project ID for the broadcast

    Returns:
        JSON string confirming delegation to Delivery Agent
    """
    logger.info("[BROADCAST] Delegating to Delivery Agent for job: %s", broadcast_job_id)
    return json.dumps({
        "status": "delegated",
        "agent": "delivery",
        "user_id": user_id,
        "broadcast_job_id": broadcast_job_id,
        "project_id": project_id,
        "message": "Handing off to Delivery Agent for message dispatch with lite-first policy, rate limiting, and retry logic."
    }, ensure_ascii=False)


@tool
def delegate_to_analytics(user_id: str, broadcast_job_id: str, project_id: str) -> str:
    """
    Delegate post-delivery analytics to the Analytics & Optimization Agent.

    Call this after broadcast COMPLETED or when user requests analytics.
    The Analytics Agent will handle:
    - Broadcast delivery report (sent, delivered, failed, read rates)
    - WABA-level analytics via MCP (message trends, engagement)
    - Messaging health & quality score monitoring via MCP
    - Broadcast history comparison across campaigns
    - AI-powered optimization recommendations

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        project_id: Project ID for the broadcast

    Returns:
        JSON string confirming delegation to Analytics Agent
    """
    logger.info("[BROADCAST] Delegating to Analytics Agent for job: %s", broadcast_job_id)
    return json.dumps({
        "status": "delegated",
        "agent": "analytics",
        "user_id": user_id,
        "broadcast_job_id": broadcast_job_id,
        "project_id": project_id,
        "message": "Handing off to Analytics Agent for delivery metrics, health monitoring, and optimization recommendations."
    }, ensure_ascii=False)


# ============================================
# TOOLS EXPORTS
# ============================================

BACKEND_TOOLS = [
    initialize_broadcast,
    process_broadcast_contacts,
    check_broadcast_compliance,
    segment_broadcast_audience,
    get_available_templates,
    get_template_details,
    create_broadcast_template,
    edit_broadcast_template,
    check_template_approval_status,
    send_broadcast_messages,
    update_broadcast_phase,
    get_broadcast_status,
    get_broadcast_analytics,
    delegate_to_data_processing,
    delegate_to_compliance,
    delegate_to_segmentation,
    delegate_to_content_creation,
    delegate_to_delivery,
    delegate_to_analytics,
]

BACKEND_TOOL_NAMES = {tool.name for tool in BACKEND_TOOLS}

# Sub-agent delegation tool names (for routing in call_model_node)
DELEGATION_TOOL_MAP = {
    "delegate_to_data_processing": "data_processing",
    "delegate_to_compliance": "compliance",
    "delegate_to_segmentation": "segmentation",
    "delegate_to_content_creation": "content_creation",
    "delegate_to_delivery": "delivery",
    "delegate_to_analytics": "analytics",
}
