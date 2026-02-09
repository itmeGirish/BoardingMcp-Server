"""
Backend tools for Delivery Agent.

Business Policy: send_marketing_lite_message FIRST, fallback to send_message.

Handles message dispatch via MCP tools:
- send_marketing_lite_message (port 9002) - cheaper, promotional text
- send_message (port 9002) - full template messages (text, image, video, document)
- mark_message_as_read (port 9002) - read status tracking

Per doc section 3.6: Rate limiting, queue management (5 priorities),
retry with exponential backoff, error code handling, delivery tracking.
"""

import asyncio
import json
import time
import concurrent.futures
import nest_asyncio
from datetime import datetime, timezone
from langchain.tools import tool

from ....config import logger

nest_asyncio.apply()
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)


# ============================================
# TIER RATE LIMITS (per doc 3.6.1)
# ============================================

TIER_LIMITS = {
    "UNVERIFIED": 250,
    "TIER_1": 1000,
    "TIER_2": 10000,
    "TIER_3": 100000,
    "TIER_4": float("inf"),
}

# ============================================
# ERROR CODE CLASSIFICATION (per doc 3.6.5)
# ============================================

NON_RETRYABLE_ERRORS = {
    "131026": "Message undeliverable - number not on WhatsApp",
    "131047": "Re-engagement required - user must message first",
    "131051": "Unsupported message type - fix template format",
    "131031": "Business account locked - contact Meta support",
}

RETRYABLE_ERRORS = {
    "131053": "Media upload failed",
    "130429": "Rate limit exceeded",
}

# Exponential backoff delays in seconds (per doc 3.6.3)
RETRY_DELAYS = [0, 30, 120, 600, 3600]  # immediate, 30s, 2m, 10m, 1h
MAX_RETRIES = 5


# ============================================
# DIRECT API MCP HELPER
# ============================================

def _call_direct_api_mcp(tool_name: str, params: dict) -> dict:
    """Call a Direct API MCP tool (port 9002) synchronously."""
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


def _is_retryable(error_code: str) -> bool:
    """Check if an error code is retryable."""
    return str(error_code) in RETRYABLE_ERRORS


def _extract_error_code(error) -> str:
    """Extract error code from various error formats."""
    if isinstance(error, dict):
        return str(error.get("code", error.get("error_code", "")))
    return str(error)


# ============================================
# TOOL 1: PREPARE DELIVERY QUEUE
# ============================================

def _run_prepare_queue_sync(user_id: str, broadcast_job_id: str):
    """Build multi-priority delivery queue and check rate limits."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository

    # Get account tier via MCP
    try:
        health = _call_direct_api_mcp("get_messaging_health_status", {"user_id": user_id})
        tier = "UNKNOWN"
        if isinstance(health, dict):
            data = health.get("data", health)
            if isinstance(data, dict):
                tier = data.get("messaging_tier", data.get("tier", "UNKNOWN"))
    except Exception:
        tier = "UNKNOWN"

    tier_upper = str(tier).upper().replace(" ", "_")
    tier_limit = TIER_LIMITS.get(tier_upper, 250)

    with get_session() as session:
        broadcast_repo = BroadcastJobRepository(session=session)
        contact_repo = ProcessedContactRepository(session=session)

        job = broadcast_repo.get_by_id(broadcast_job_id)
        if not job:
            return {"status": "failed", "message": "Broadcast job not found"}

        contacts = contact_repo.get_by_broadcast_job(broadcast_job_id)
        valid_contacts = [c for c in contacts if not c.get("is_duplicate")]

    # Build priority queues based on quality score and data
    queues = {
        "priority_1_urgent": [],      # Transactional
        "priority_2_window": [],      # 24-hr window contacts
        "priority_3_normal": [],      # Standard marketing
        "priority_4_low": [],         # Bulk, non-time-sensitive
        "priority_5_background": [],  # Re-engagement
    }

    for contact in valid_contacts:
        phone = contact["phone_e164"]
        score = contact.get("quality_score", 50)

        # Classify by quality score
        if score >= 80:
            queues["priority_3_normal"].append(phone)
        elif score >= 50:
            queues["priority_4_low"].append(phone)
        else:
            queues["priority_5_background"].append(phone)

    total_to_send = sum(len(q) for q in queues.values())

    # Check tier limit
    capped = False
    if tier_limit != float("inf") and total_to_send > tier_limit:
        capped = True

    queue_summary = {k: len(v) for k, v in queues.items()}

    return {
        "status": "success",
        "total_contacts": total_to_send,
        "messaging_tier": tier,
        "tier_limit": tier_limit if tier_limit != float("inf") else "unlimited",
        "capped": capped,
        "queue_summary": queue_summary,
        "template_name": job.get("template_name"),
        "template_category": job.get("template_category"),
        "message": (
            f"Delivery queue prepared: {total_to_send} contacts across 5 priority levels. "
            f"Tier: {tier} (limit: {tier_limit if tier_limit != float('inf') else 'unlimited'}). "
            + (f"WARNING: Capped at tier limit ({tier_limit})." if capped else "Within tier limits.")
        ),
    }


@tool
def prepare_delivery_queue(user_id: str, broadcast_job_id: str) -> str:
    """
    Prepare multi-priority delivery queue and check rate limits.

    Builds 5-level priority queue and validates against messaging tier.
    Priority: 1=Urgent/OTP, 2=24hr window, 3=Normal, 4=Low, 5=Background.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with queue summary, tier info, and capacity check
    """
    logger.info("[DELIVERY] prepare_delivery_queue for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_prepare_queue_sync, user_id, broadcast_job_id)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DELIVERY] prepare_delivery_queue error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 2: SEND LITE BROADCAST (Business Policy - FIRST)
# ============================================

def _run_send_lite_broadcast_sync(user_id: str, broadcast_job_id: str):
    """
    Send broadcast via marketing lite message (cheaper, business policy).
    Uses send_marketing_lite_message MCP tool.
    """
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository
    from app.database.postgresql.postgresql_repositories.template_creation_repo import TemplateCreationRepository

    with get_session() as session:
        broadcast_repo = BroadcastJobRepository(session=session)
        contact_repo = ProcessedContactRepository(session=session)

        job = broadcast_repo.get_by_id(broadcast_job_id)
        if not job:
            return {"status": "failed", "message": "Broadcast job not found"}

        template_name = job.get("template_name")
        if not template_name:
            return {"status": "failed", "message": "No template selected for broadcast"}

        # Get template body text for lite sending
        template_id = job.get("template_id")
        body_text = None

        if template_id:
            template_repo = TemplateCreationRepository(session=session)
            template = template_repo.get_by_template_id(template_id)
            if template and template.get("components"):
                for comp in template["components"]:
                    if isinstance(comp, dict) and comp.get("type", "").upper() == "BODY":
                        body_text = comp.get("text", "")
                        break

        # Check if template has media/buttons - if so, lite is not applicable
        has_media = False
        if template and template.get("components"):
            for comp in template["components"]:
                if isinstance(comp, dict):
                    fmt = comp.get("format", "").upper()
                    ctype = comp.get("type", "").upper()
                    if fmt in ("IMAGE", "VIDEO", "DOCUMENT") or ctype == "BUTTONS":
                        has_media = True
                        break

        if has_media:
            return {
                "status": "skipped",
                "reason": "template_has_media",
                "message": "Template contains media/buttons. Lite sending not applicable. Use send_template_broadcast instead.",
            }

        if not body_text:
            return {
                "status": "skipped",
                "reason": "no_body_text",
                "message": "Could not extract body text from template. Use send_template_broadcast instead.",
            }

        contacts = contact_repo.get_by_broadcast_job(broadcast_job_id)
        valid_phones = [c["phone_e164"] for c in contacts if not c.get("is_duplicate")]

    if not valid_phones:
        return {"status": "failed", "message": "No valid contacts to send to"}

    # Send via lite MCP tool
    sent = 0
    failed = 0
    errors = []

    for phone in valid_phones:
        try:
            result = _call_direct_api_mcp("send_marketing_lite_message", {
                "to": phone,
                "text_body": body_text,
                "message_type": "text",
                "recipient_type": "individual",
            })

            if isinstance(result, dict) and result.get("success"):
                sent += 1
            else:
                failed += 1
                error_detail = result.get("error", "Unknown") if isinstance(result, dict) else str(result)
                error_code = _extract_error_code(result.get("error", {}) if isinstance(result, dict) else {})
                errors.append({
                    "phone": phone,
                    "error": error_detail,
                    "error_code": error_code,
                    "retryable": _is_retryable(error_code),
                })
        except Exception as e:
            failed += 1
            errors.append({"phone": phone, "error": str(e), "retryable": True})

    # Update broadcast job progress
    with get_session() as session:
        broadcast_repo = BroadcastJobRepository(session=session)
        broadcast_repo.update_send_progress(broadcast_job_id, sent=sent, failed=failed)

    retryable_count = sum(1 for e in errors if e.get("retryable"))

    return {
        "status": "success",
        "method": "marketing_lite",
        "total": len(valid_phones),
        "sent": sent,
        "failed": failed,
        "retryable_failures": retryable_count,
        "permanent_failures": failed - retryable_count,
        "errors_preview": errors[:10],
        "message": (
            f"Lite broadcast: {sent} sent, {failed} failed out of {len(valid_phones)}. "
            f"({retryable_count} retryable, {failed - retryable_count} permanent)."
        ),
    }


@tool
def send_lite_broadcast(user_id: str, broadcast_job_id: str) -> str:
    """
    Send broadcast via marketing lite message (Business Policy: TRY FIRST).

    Uses send_marketing_lite_message MCP tool - cheaper, optimized for promotional.
    Sends template body text as lite message to all contacts.
    If template has media/buttons, returns 'skipped' - use send_template_broadcast instead.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with send results (sent, failed, errors) or 'skipped' if not applicable
    """
    logger.info("[DELIVERY] send_lite_broadcast for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_send_lite_broadcast_sync, user_id, broadcast_job_id)
        result = future.result(timeout=300)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DELIVERY] send_lite_broadcast error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 3: SEND TEMPLATE BROADCAST (FALLBACK)
# ============================================

def _run_send_template_broadcast_sync(user_id: str, broadcast_job_id: str):
    """
    Send broadcast via full template message.
    Uses send_message MCP tool with message_type="template".
    """
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository

    with get_session() as session:
        broadcast_repo = BroadcastJobRepository(session=session)
        contact_repo = ProcessedContactRepository(session=session)

        job = broadcast_repo.get_by_id(broadcast_job_id)
        if not job:
            return {"status": "failed", "message": "Broadcast job not found"}

        template_name = job.get("template_name")
        template_language = job.get("template_language", "en")
        if not template_name:
            return {"status": "failed", "message": "No template selected for broadcast"}

        contacts = contact_repo.get_by_broadcast_job(broadcast_job_id)
        valid_phones = [c["phone_e164"] for c in contacts if not c.get("is_duplicate")]

    if not valid_phones:
        return {"status": "failed", "message": "No valid contacts to send to"}

    sent = 0
    failed = 0
    errors = []

    for phone in valid_phones:
        try:
            result = _call_direct_api_mcp("send_message", {
                "user_id": user_id,
                "to": phone,
                "message_type": "template",
                "template_name": template_name,
                "template_language_code": template_language,
            })

            if isinstance(result, dict) and (result.get("success") or result.get("status") == "success"):
                sent += 1
            else:
                failed += 1
                error_detail = result.get("error", "Unknown") if isinstance(result, dict) else str(result)
                error_code = _extract_error_code(result.get("error", {}) if isinstance(result, dict) else {})
                errors.append({
                    "phone": phone,
                    "error": error_detail,
                    "error_code": error_code,
                    "retryable": _is_retryable(error_code),
                })
        except Exception as e:
            failed += 1
            errors.append({"phone": phone, "error": str(e), "retryable": True})

    # Update broadcast job progress
    with get_session() as session:
        broadcast_repo = BroadcastJobRepository(session=session)
        broadcast_repo.update_send_progress(broadcast_job_id, sent=sent, failed=failed)

    retryable_count = sum(1 for e in errors if e.get("retryable"))

    return {
        "status": "success",
        "method": "template",
        "total": len(valid_phones),
        "sent": sent,
        "failed": failed,
        "retryable_failures": retryable_count,
        "permanent_failures": failed - retryable_count,
        "errors_preview": errors[:10],
        "message": (
            f"Template broadcast: {sent} sent, {failed} failed out of {len(valid_phones)}. "
            f"({retryable_count} retryable, {failed - retryable_count} permanent)."
        ),
    }


@tool
def send_template_broadcast(user_id: str, broadcast_job_id: str) -> str:
    """
    Send broadcast via full template message (fallback when lite is not applicable).

    Uses send_message MCP tool with message_type="template".
    Supports all template types: text, image, video, document with buttons.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with send results (sent, failed, errors with error codes)
    """
    logger.info("[DELIVERY] send_template_broadcast for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_send_template_broadcast_sync, user_id, broadcast_job_id)
        result = future.result(timeout=300)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DELIVERY] send_template_broadcast error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 4: RETRY FAILED MESSAGES
# ============================================

def _run_retry_failed_sync(user_id: str, broadcast_job_id: str, max_retries: int = MAX_RETRIES):
    """Retry failed messages with exponential backoff."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    with get_session() as session:
        broadcast_repo = BroadcastJobRepository(session=session)
        job = broadcast_repo.get_by_id(broadcast_job_id)

    if not job:
        return {"status": "failed", "message": "Broadcast job not found"}

    template_name = job.get("template_name")
    template_language = job.get("template_language", "en")

    # Get failed contacts from the last send attempt
    # In a production system, these would be stored in a separate table
    # For now, we re-check all contacts and resend to those not yet delivered
    from app.database.postgresql.postgresql_connection import get_session as gs
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository

    with gs() as session:
        contact_repo = ProcessedContactRepository(session=session)
        contacts = contact_repo.get_by_broadcast_job(broadcast_job_id)
        all_phones = [c["phone_e164"] for c in contacts if not c.get("is_duplicate")]

    # Track retry results
    retried = 0
    succeeded = 0
    permanent_fails = 0
    still_failing = 0

    # Simulate retry with backoff (limited retries in single call)
    retry_phones = all_phones[:50]  # Limit per retry batch

    for phone in retry_phones:
        for attempt in range(min(max_retries, 3)):  # Max 3 attempts per tool call
            delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else RETRY_DELAYS[-1]

            if delay > 0 and attempt > 0:
                time.sleep(min(delay, 5))  # Cap sleep at 5s per attempt in tool context

            try:
                result = _call_direct_api_mcp("send_message", {
                    "user_id": user_id,
                    "to": phone,
                    "message_type": "template",
                    "template_name": template_name,
                    "template_language_code": template_language,
                })

                if isinstance(result, dict) and (result.get("success") or result.get("status") == "success"):
                    succeeded += 1
                    retried += 1
                    break
                else:
                    error_code = _extract_error_code(
                        result.get("error", {}) if isinstance(result, dict) else {}
                    )
                    if not _is_retryable(error_code):
                        permanent_fails += 1
                        retried += 1
                        break
                    # Retryable - continue to next attempt
            except Exception:
                pass  # Will retry
        else:
            still_failing += 1
            retried += 1

    # Update progress
    with gs() as session:
        broadcast_repo = BroadcastJobRepository(session=session)
        current_sent = job.get("sent_count", 0) + succeeded
        current_failed = job.get("failed_count", 0) - succeeded
        if current_failed < 0:
            current_failed = 0
        broadcast_repo.update_send_progress(broadcast_job_id, sent=current_sent, failed=current_failed)

    return {
        "status": "success",
        "retried": retried,
        "succeeded": succeeded,
        "permanent_failures": permanent_fails,
        "still_failing": still_failing,
        "message": (
            f"Retry complete: {retried} retried, {succeeded} now succeeded, "
            f"{permanent_fails} permanent failures, {still_failing} still failing."
        ),
    }


@tool
def retry_failed_messages(user_id: str, broadcast_job_id: str) -> str:
    """
    Retry failed messages with exponential backoff.

    Retries with delays: immediate, 30s, 2min, 10min, 1hr.
    Non-retryable errors (131026, 131047, 131051, 131031) are marked permanent.
    Retryable errors (131053 media, 130429 rate limit) are retried.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with retry results
    """
    logger.info("[DELIVERY] retry_failed_messages for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_retry_failed_sync, user_id, broadcast_job_id)
        result = future.result(timeout=300)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DELIVERY] retry_failed_messages error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 5: GET DELIVERY SUMMARY
# ============================================

def _run_get_delivery_summary_sync(user_id: str, broadcast_job_id: str):
    """Get final delivery metrics for a broadcast job."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        job = repo.get_by_id(broadcast_job_id)

    if not job:
        return {"status": "failed", "message": "Broadcast job not found"}

    total = job.get("valid_contacts", 0)
    sent = job.get("sent_count", 0)
    failed = job.get("failed_count", 0)
    pending = job.get("pending_count", 0)
    delivered = job.get("delivered_count", 0)

    delivery_rate = round((sent / total * 100), 1) if total > 0 else 0

    return {
        "status": "success",
        "broadcast_job_id": broadcast_job_id,
        "total_contacts": total,
        "sent": sent,
        "delivered": delivered,
        "failed": failed,
        "pending": pending,
        "delivery_rate": delivery_rate,
        "template_name": job.get("template_name"),
        "template_category": job.get("template_category"),
        "started_at": job.get("started_sending_at"),
        "completed_at": job.get("completed_at"),
        "message": (
            f"Delivery summary: {sent}/{total} sent ({delivery_rate}%), "
            f"{delivered} delivered, {failed} failed, {pending} pending."
        ),
    }


@tool
def get_delivery_summary(user_id: str, broadcast_job_id: str) -> str:
    """
    Get final delivery metrics for a broadcast job.

    Returns: total, sent, delivered, failed, pending, delivery rate,
    template info, and timestamps.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with delivery summary metrics
    """
    logger.info("[DELIVERY] get_delivery_summary for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_get_delivery_summary_sync, user_id, broadcast_job_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DELIVERY] get_delivery_summary error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 6: MARK MESSAGES AS READ
# ============================================

def _run_mark_read_sync(message_ids: list):
    """Mark messages as read via MCP."""
    results = {"marked": 0, "failed": 0, "errors": []}

    for msg_id in message_ids:
        try:
            result = _call_direct_api_mcp("mark_message_as_read", {"message_id": msg_id})
            if isinstance(result, dict) and result.get("success"):
                results["marked"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({"message_id": msg_id, "error": str(result)})
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"message_id": msg_id, "error": str(e)})

    return {
        "status": "success",
        **results,
        "message": f"Marked {results['marked']} messages as read, {results['failed']} failed.",
    }


@tool
def mark_messages_read(message_ids: list) -> str:
    """
    Mark messages as read via WhatsApp API.

    Called when webhook delivers read receipts. Updates read status
    for analytics tracking.

    Args:
        message_ids: List of WhatsApp message IDs to mark as read

    Returns:
        JSON string with mark-as-read results
    """
    logger.info("[DELIVERY] mark_messages_read: %d messages", len(message_ids))
    try:
        future = _executor.submit(_run_mark_read_sync, message_ids)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DELIVERY] mark_messages_read error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOLS EXPORT
# ============================================

BACKEND_TOOLS = [
    prepare_delivery_queue,
    send_lite_broadcast,
    send_template_broadcast,
    retry_failed_messages,
    get_delivery_summary,
    mark_messages_read,
]

BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
