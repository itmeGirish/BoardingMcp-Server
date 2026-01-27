"""
CopilotKit tools for broadcasting workflow

This module defines the LangChain tools that integrate with
the MCP server and database for the broadcasting workflow.

IMPORTANT: These tools run in LangGraph's ASGI context.
We use ThreadPoolExecutor to run MCP calls in separate threads with their own event loops.
"""
import asyncio
import json
import logging
import concurrent.futures
import nest_asyncio
from langchain.tools import tool

from ...config import logger

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Thread pool for running MCP calls in separate threads
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


# ============================================
# SYNC WRAPPERS - Run calls in new event loop
# ============================================

def _run_load_temp_memory_sync(user_id: str):
    """Load TempMemory data from database synchronously."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories import MemoryRepository

    logger.info("Loading TempMemory for user_id: %s", user_id)

    with get_session() as session:
        memory_repo = MemoryRepository(session=session)
        memory_record = memory_repo.get_by_user_id(user_id)

    if not memory_record:
        logger.warning("No TempMemory found for user_id: %s", user_id)
        return {
            "status": "failed",
            "error": f"No TempMemory found for user_id: {user_id}. Please complete onboarding first."
        }

    logger.info("TempMemory loaded for user_id: %s, first_broadcasting: %s",
                user_id, memory_record.get("first_broadcasting"))
    return {
        "status": "success",
        "data": memory_record
    }


def _run_check_fb_verification_status_sync(user_id: str):
    """Run MCP fb_verification_status synchronously in a new event loop.

    Connects to Direct API MCP server (port 9002) to check FB verification status.
    """
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.utils.whsp_onboarding_agent import parse_mcp_result_with_debug as parse_mcp_result

    async def _call():
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Creating fresh MCP client for FB verification status check...")
        client = MultiServerMCPClient({
            "DirectApiMCP": {
                "url": "http://127.0.0.1:9002/mcp",
                "transport": "streamable-http"
            }
        })

        logger.info("Opening MCP session to Direct API server...")
        async with client.session("DirectApiMCP") as session:
            logger.info("Loading MCP tools from Direct API server...")
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}
            logger.info(f"Loaded {len(mcp_tools)} tools from Direct API server")

            fb_status_tool = mcp_tools["fb_verification_status"]

            logger.info(f"Calling fb_verification_status for user_id: {user_id}...")
            result = await fb_status_tool.ainvoke({
                "user_id": user_id
            })

            logger.info("Tool call completed, parsing result...")
            parsed = parse_mcp_result(result)
            logger.info(f"Result status: {parsed.get('status', 'unknown')}")
            return parsed

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call())
    finally:
        loop.close()


# ============================================
# TOOL: LOAD TEMP MEMORY
# ============================================

@tool
def load_temp_memory(user_id: str) -> str:
    """
    Load the user's TempMemory data from the database.

    This is the FIRST tool to call when starting the broadcasting workflow.
    It loads the user's JWT token, broadcasting status, and other runtime data
    from the temporary_notes table.

    The result contains:
    - first_broadcasting: True if this is the first broadcast (skip verification)
    - broadcasting_status: Current broadcasting activity status
    - jwt_token: JWT token for API calls
    - Other user/business/project identifiers

    Args:
        user_id: User's unique identifier

    Returns:
        JSON string containing TempMemory data or error
    """
    logger.info("[BROADCASTING] load_temp_memory called for user: %s", user_id)

    try:
        result = _run_load_temp_memory_sync(user_id=user_id)

        if not isinstance(result, dict):
            logger.error("Unexpected result type: %s", type(result))
            result = {"error": "Invalid response format", "status": "failed"}

        logger.info("[BROADCASTING] load_temp_memory result: %s", result.get('status', 'unknown'))
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        error_msg = str(e)
        logger.error("[BROADCASTING] load_temp_memory error: %s", e, exc_info=True)
        return json.dumps({"error": error_msg, "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL: CHECK FB VERIFICATION STATUS
# ============================================

@tool
def check_fb_verification_status(user_id: str) -> str:
    """
    Check the Facebook business verification status for broadcasting eligibility.

    This tool is called ONLY when first_broadcasting is False.
    It connects to the Direct API MCP server to check if the user's
    WhatsApp Business Account is verified for broadcasting.

    If verified (verificationStatus == "verified"), the user can proceed with broadcasting.
    If not verified, the user is ineligible for broadcasting.

    Args:
        user_id: User's unique identifier

    Returns:
        JSON string containing verification status or error
    """
    logger.info("[BROADCASTING] check_fb_verification_status called for user: %s", user_id)

    try:
        future = _executor.submit(_run_check_fb_verification_status_sync, user_id=user_id)
        logger.info("[BROADCASTING] Waiting for FB verification status (timeout: 30s)...")
        result = future.result(timeout=30)

        if not isinstance(result, dict):
            logger.error("MCP returned non-dict result: %s", type(result))
            result = {"error": "Invalid MCP response format", "status": "failed"}

        logger.info("[BROADCASTING] FB verification result: %s", result.get('status', 'unknown'))
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        error_msg = str(e)
        logger.error("[BROADCASTING] FB verification error: %s", e, exc_info=True)
        return json.dumps({"error": error_msg, "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOLS EXPORTS
# ============================================

BACKEND_TOOLS = [
    load_temp_memory,
    check_fb_verification_status,
]

# Set of tool names for O(1) lookup
BACKEND_TOOL_NAMES = {tool.name for tool in BACKEND_TOOLS}
