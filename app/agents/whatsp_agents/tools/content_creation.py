"""
Backend tools for Content Creation Agent.

Full template lifecycle:
1. Create/submit template (text, image, video, document) via MCP
2. Check approval status via MCP + sync DB
3. Edit template and resubmit via MCP
4. Delete template by ID or by name via MCP + soft-delete in DB
5. List/filter user templates from DB
6. Select template for broadcast job

Uses MCP tools from direct_api_mcp (port 9002):
- submit_whatsapp_template_message
- get_template_by_id
- get_templates
- edit_template
- delete_wa_template_by_id
- delete_wa_template_by_name
"""

import asyncio
import json
import concurrent.futures
import nest_asyncio
from langchain.tools import tool

from ....config import logger

nest_asyncio.apply()
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)


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


# ============================================
# TOOL 1: LIST USER TEMPLATES
# ============================================

def _run_list_templates_sync(user_id: str, status_filter: str = None, category_filter: str = None):
    """List templates from local DB with optional filters."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.template_creation_repo import TemplateCreationRepository

    with get_session() as session:
        repo = TemplateCreationRepository(session=session)

        if status_filter:
            templates = repo.get_by_user_and_status(user_id, status_filter.upper())
        elif category_filter:
            templates = repo.get_by_user_and_category(user_id, category_filter.upper())
        else:
            templates = repo.get_by_user_id(user_id)

    # Summary format for display
    template_list = []
    for t in templates:
        template_list.append({
            "template_id": t["template_id"],
            "name": t["name"],
            "category": t["category"],
            "language": t["language"],
            "status": t["status"],
            "quality_rating": t.get("quality_rating"),
            "usage_count": t.get("usage_count", 0),
            "created_at": t.get("created_at"),
        })

    return {
        "status": "success",
        "total": len(template_list),
        "filters": {"status": status_filter, "category": category_filter},
        "templates": template_list,
        "message": f"Found {len(template_list)} template(s)" + (
            f" with status={status_filter}" if status_filter else
            f" in category={category_filter}" if category_filter else ""
        ) + ".",
    }


@tool
def list_user_templates(
    user_id: str,
    status_filter: str = None,
    category_filter: str = None,
) -> str:
    """
    List available WhatsApp templates for the user from local database.

    Can filter by status (APPROVED, PENDING, REJECTED, PAUSED, DISABLED)
    or by category (MARKETING, UTILITY, AUTHENTICATION).

    Args:
        user_id: User's unique identifier
        status_filter: Optional status filter (APPROVED, PENDING, REJECTED)
        category_filter: Optional category filter (MARKETING, UTILITY, AUTHENTICATION)

    Returns:
        JSON string with list of templates
    """
    logger.info("[CONTENT] list_user_templates for user: %s", user_id)
    try:
        future = _executor.submit(_run_list_templates_sync, user_id, status_filter, category_filter)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CONTENT] list_user_templates error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 2: GET TEMPLATE DETAIL
# ============================================

def _run_get_template_detail_sync(user_id: str, template_id: str):
    """Get full template details from MCP API + local DB."""
    # Fetch from WhatsApp API via MCP
    mcp_result = _call_direct_api_mcp("get_template_by_id", {
        "user_id": user_id, "template_id": template_id
    })

    # Also get from local DB for quality/usage data
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.template_creation_repo import TemplateCreationRepository

    with get_session() as session:
        repo = TemplateCreationRepository(session=session)
        local = repo.get_by_template_id(template_id)

        # Sync status from API to DB if changed
        if isinstance(mcp_result, dict) and mcp_result.get("success"):
            api_data = mcp_result.get("data", {})
            api_status = api_data.get("status", "").upper() if isinstance(api_data, dict) else ""
            if local and api_status and api_status != local.get("status"):
                rejected_reason = api_data.get("rejected_reason") if isinstance(api_data, dict) else None
                repo.update_status(template_id, api_status, rejected_reason)
                local = repo.get_by_template_id(template_id)

    combined = {}
    if isinstance(mcp_result, dict) and mcp_result.get("success"):
        combined["api_data"] = mcp_result.get("data", {})
    if local:
        combined["local_data"] = local

    return {
        "status": "success",
        "template_id": template_id,
        **combined,
        "message": f"Template details retrieved for {template_id}.",
    }


@tool
def get_template_detail(user_id: str, template_id: str) -> str:
    """
    Get full template details including components, status, and quality.

    Fetches from WhatsApp API via MCP and syncs status with local DB.
    Shows: components (header, body, footer, buttons), approval status,
    rejection reason if any, quality rating, usage count.

    Args:
        user_id: User's unique identifier
        template_id: WhatsApp template ID

    Returns:
        JSON string with full template details from API + local DB
    """
    logger.info("[CONTENT] get_template_detail: %s", template_id)
    try:
        future = _executor.submit(_run_get_template_detail_sync, user_id, template_id)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CONTENT] get_template_detail error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 3: SUBMIT TEMPLATE (CREATE NEW)
# ============================================

def _run_submit_template_sync(
    user_id: str, name: str, category: str, language: str, components: list
):
    """Submit new template to WhatsApp via MCP and store in DB."""
    # Submit to WhatsApp via MCP
    mcp_result = _call_direct_api_mcp("submit_whatsapp_template_message", {
        "user_id": user_id,
        "name": name,
        "category": category,
        "language": language,
        "components": components,
    })

    if not isinstance(mcp_result, dict) or not mcp_result.get("success"):
        error = mcp_result.get("error", "Unknown error") if isinstance(mcp_result, dict) else str(mcp_result)
        return {
            "status": "failed",
            "error": error,
            "message": f"Template submission failed: {error}",
        }

    # Extract template_id from API response
    api_data = mcp_result.get("data", {})
    template_id = ""
    if isinstance(api_data, dict):
        template_id = api_data.get("id", api_data.get("template_id", ""))

    # Store in local DB
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.template_creation_repo import TemplateCreationRepository
    from app.database.postgresql.postgresql_repositories.memory_repo import MemoryRepository

    with get_session() as session:
        memory_repo = MemoryRepository(session=session)
        memory = memory_repo.get_by_user_id(user_id)
        business_id = memory.get("business_id", "") if memory else ""
        project_id = memory.get("project_id", "") if memory else ""

        template_repo = TemplateCreationRepository(session=session)
        template_repo.create(
            template_id=str(template_id),
            user_id=user_id,
            business_id=business_id,
            name=name,
            category=category,
            language=language,
            components=components,
            project_id=project_id,
            status="PENDING",
        )

    return {
        "status": "success",
        "template_id": str(template_id),
        "name": name,
        "category": category,
        "language": language,
        "template_status": "PENDING",
        "api_response": api_data,
        "message": (
            f"Template '{name}' submitted successfully (ID: {template_id}). "
            f"Status: PENDING - awaiting WhatsApp approval (24-48 hours)."
        ),
    }


@tool
def submit_template(
    user_id: str,
    name: str,
    category: str,
    language: str,
    components: list,
) -> str:
    """
    Create and submit a new WhatsApp template for approval.

    Supports all template types: text, image, video, document headers.
    Submits to WhatsApp API via MCP and stores in local DB.

    Template name must be lowercase with underscores only.
    Categories: MARKETING, UTILITY, AUTHENTICATION.

    Components format:
    [
        {"type": "HEADER", "format": "TEXT", "text": "Hello!"},
        {"type": "BODY", "text": "Hi {{1}}, your order is ready!"},
        {"type": "FOOTER", "text": "Reply STOP to unsubscribe"},
        {"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": "OK"}]}
    ]

    For image/video/document headers use format: IMAGE, VIDEO, DOCUMENT
    with example.header_handle containing the media URL.

    Args:
        user_id: User's unique identifier
        name: Template name (lowercase, underscores, no spaces)
        category: MARKETING, UTILITY, or AUTHENTICATION
        language: Language code (e.g., "en", "en_US", "hi")
        components: List of template components

    Returns:
        JSON string with template ID, status, and API response
    """
    logger.info("[CONTENT] submit_template: name=%s, category=%s", name, category)
    try:
        future = _executor.submit(
            _run_submit_template_sync, user_id, name, category, language, components
        )
        result = future.result(timeout=60)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CONTENT] submit_template error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 4: CHECK TEMPLATE STATUS
# ============================================

def _run_check_template_status_sync(user_id: str, template_id: str):
    """Check template approval status from WhatsApp API and sync to DB."""
    mcp_result = _call_direct_api_mcp("get_template_by_id", {
        "user_id": user_id, "template_id": template_id
    })

    api_status = "UNKNOWN"
    rejected_reason = None

    if isinstance(mcp_result, dict) and mcp_result.get("success"):
        api_data = mcp_result.get("data", {})
        if isinstance(api_data, dict):
            api_status = api_data.get("status", "UNKNOWN").upper()
            rejected_reason = api_data.get("rejected_reason", api_data.get("quality_score", {}).get("reasons"))

    # Sync status to local DB
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.template_creation_repo import TemplateCreationRepository

    with get_session() as session:
        repo = TemplateCreationRepository(session=session)
        repo.update_status(template_id, api_status, rejected_reason=str(rejected_reason) if rejected_reason else None)

    return {
        "status": "success",
        "template_id": template_id,
        "template_status": api_status,
        "rejected_reason": rejected_reason,
        "message": (
            f"Template {template_id}: status is {api_status}."
            + (f" Rejection reason: {rejected_reason}" if rejected_reason and api_status == "REJECTED" else "")
        ),
    }


@tool
def check_template_status(user_id: str, template_id: str) -> str:
    """
    Check template approval status from WhatsApp and sync to local DB.

    Polls get_template_by_id MCP tool and updates local status.
    Returns: PENDING, APPROVED, REJECTED (with reason), PAUSED, DISABLED.

    Args:
        user_id: User's unique identifier
        template_id: WhatsApp template ID to check

    Returns:
        JSON string with current template status and rejection reason if any
    """
    logger.info("[CONTENT] check_template_status: %s", template_id)
    try:
        future = _executor.submit(_run_check_template_status_sync, user_id, template_id)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CONTENT] check_template_status error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 5: EDIT TEMPLATE
# ============================================

def _run_edit_template_sync(user_id: str, template_id: str, components: list):
    """Edit template via MCP and update local DB."""
    mcp_result = _call_direct_api_mcp("edit_template", {
        "user_id": user_id,
        "template_id": template_id,
        "components": components,
    })

    if not isinstance(mcp_result, dict) or not mcp_result.get("success"):
        error = mcp_result.get("error", "Unknown error") if isinstance(mcp_result, dict) else str(mcp_result)
        return {"status": "failed", "error": error, "message": f"Template edit failed: {error}"}

    # Update local DB (components + reset status to PENDING)
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.template_creation_repo import TemplateCreationRepository

    with get_session() as session:
        repo = TemplateCreationRepository(session=session)
        repo.update_components(template_id, components)

    return {
        "status": "success",
        "template_id": template_id,
        "template_status": "PENDING",
        "message": f"Template {template_id} edited and resubmitted. Status reset to PENDING.",
    }


@tool
def edit_template(user_id: str, template_id: str, components: list) -> str:
    """
    Edit an existing WhatsApp template and resubmit for approval.

    Updates the template components via MCP API and resets status to PENDING.
    Use this after a template is REJECTED to fix and resubmit.

    Args:
        user_id: User's unique identifier
        template_id: WhatsApp template ID to edit
        components: Updated template components list

    Returns:
        JSON string with edit result and new status
    """
    logger.info("[CONTENT] edit_template: %s", template_id)
    try:
        future = _executor.submit(_run_edit_template_sync, user_id, template_id, components)
        result = future.result(timeout=60)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CONTENT] edit_template error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 6: DELETE TEMPLATE BY ID
# ============================================

def _run_delete_by_id_sync(user_id: str, template_id: str, template_name: str):
    """Delete template by ID via MCP and soft-delete in DB."""
    mcp_result = _call_direct_api_mcp("delete_wa_template_by_id", {
        "user_id": user_id,
        "template_id": template_id,
        "template_name": template_name,
    })

    if not isinstance(mcp_result, dict) or not mcp_result.get("success"):
        error = mcp_result.get("error", "Unknown error") if isinstance(mcp_result, dict) else str(mcp_result)
        return {"status": "failed", "error": error, "message": f"Delete failed: {error}"}

    # Soft-delete in local DB
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.template_creation_repo import TemplateCreationRepository

    with get_session() as session:
        repo = TemplateCreationRepository(session=session)
        repo.soft_delete(template_id)

    return {
        "status": "success",
        "template_id": template_id,
        "template_name": template_name,
        "message": f"Template '{template_name}' (ID: {template_id}) deleted permanently from WhatsApp and archived in DB.",
    }


@tool
def delete_template_by_id(user_id: str, template_id: str, template_name: str) -> str:
    """
    Delete a WhatsApp template by ID and name.

    Permanently removes from WhatsApp via MCP and soft-deletes in local DB.
    WARNING: This action is IRREVERSIBLE.

    Args:
        user_id: User's unique identifier
        template_id: WhatsApp template ID to delete
        template_name: Template name (required by WhatsApp API)

    Returns:
        JSON string with deletion result
    """
    logger.info("[CONTENT] delete_template_by_id: %s (%s)", template_id, template_name)
    try:
        future = _executor.submit(_run_delete_by_id_sync, user_id, template_id, template_name)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CONTENT] delete_template_by_id error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 7: DELETE TEMPLATE BY NAME
# ============================================

def _run_delete_by_name_sync(user_id: str, template_name: str):
    """Delete template by name via MCP and soft-delete in DB."""
    mcp_result = _call_direct_api_mcp("delete_wa_template_by_name", {
        "template_name": template_name,
    })

    if not isinstance(mcp_result, dict) or not mcp_result.get("success"):
        error = mcp_result.get("error", "Unknown error") if isinstance(mcp_result, dict) else str(mcp_result)
        return {"status": "failed", "error": error, "message": f"Delete failed: {error}"}

    # Try to soft-delete matching template in local DB
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.template_creation_repo import TemplateCreationRepository

    with get_session() as session:
        repo = TemplateCreationRepository(session=session)
        user_templates = repo.get_by_user_id(user_id)
        for t in user_templates:
            if t["name"] == template_name:
                repo.soft_delete(t["template_id"])
                break

    return {
        "status": "success",
        "template_name": template_name,
        "message": f"Template '{template_name}' deleted permanently from WhatsApp and archived in DB.",
    }


@tool
def delete_template_by_name(user_id: str, template_name: str) -> str:
    """
    Delete a WhatsApp template by name.

    Permanently removes from WhatsApp via MCP and soft-deletes in local DB.
    WARNING: This action is IRREVERSIBLE. Deletes ALL versions of the named template.

    Args:
        user_id: User's unique identifier
        template_name: Template name to delete

    Returns:
        JSON string with deletion result
    """
    logger.info("[CONTENT] delete_template_by_name: %s", template_name)
    try:
        future = _executor.submit(_run_delete_by_name_sync, user_id, template_name)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CONTENT] delete_template_by_name error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 8: SELECT TEMPLATE FOR BROADCAST
# ============================================

def _run_select_template_sync(user_id: str, broadcast_job_id: str, template_id: str):
    """Select an approved template for a broadcast job."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.template_creation_repo import TemplateCreationRepository
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    with get_session() as session:
        template_repo = TemplateCreationRepository(session=session)
        broadcast_repo = BroadcastJobRepository(session=session)

        template = template_repo.get_by_template_id(template_id)
        if not template:
            return {"status": "failed", "message": f"Template {template_id} not found in DB."}

        if template["status"] != "APPROVED":
            return {
                "status": "failed",
                "template_status": template["status"],
                "message": f"Template is not APPROVED (current: {template['status']}). Only APPROVED templates can be used.",
            }

        # Update broadcast job with selected template
        broadcast_repo.update_template(
            job_id=broadcast_job_id,
            template_id=template["template_id"],
            template_name=template["name"],
            template_language=template["language"],
            template_category=template["category"],
            template_status=template["status"],
        )

        # Increment usage counter
        template_repo.increment_usage(template_id)

    return {
        "status": "success",
        "broadcast_job_id": broadcast_job_id,
        "template_id": template["template_id"],
        "template_name": template["name"],
        "template_category": template["category"],
        "template_language": template["language"],
        "message": (
            f"Template '{template['name']}' (APPROVED) selected for broadcast. "
            f"Ready to proceed to READY_TO_SEND phase."
        ),
    }


@tool
def select_template_for_broadcast(
    user_id: str, broadcast_job_id: str, template_id: str
) -> str:
    """
    Select an APPROVED template for a broadcast job.

    Links the template to the broadcast job. Only APPROVED templates
    can be selected. Increments the template usage counter.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        template_id: WhatsApp template ID to select

    Returns:
        JSON string with selection result
    """
    logger.info("[CONTENT] select_template_for_broadcast: template=%s, job=%s", template_id, broadcast_job_id)
    try:
        future = _executor.submit(_run_select_template_sync, user_id, broadcast_job_id, template_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CONTENT] select_template_for_broadcast error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOLS EXPORT
# ============================================

BACKEND_TOOLS = [
    list_user_templates,
    get_template_detail,
    submit_template,
    check_template_status,
    edit_template,
    delete_template_by_id,
    delete_template_by_name,
    select_template_for_broadcast,
]

BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
