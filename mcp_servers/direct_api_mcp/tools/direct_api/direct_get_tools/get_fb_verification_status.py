"""
MCP Tool: Get fb verification status

Fetches fb verification status info from the AiSensy Direct API.
Uses JWT token from TempMemory (temporary_notes) table.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import MemoryRepository


@mcp.tool(
    name="fb_verification_status",
    description=(
        "Fetches fb verification status info from the AiSensy Direct API. "
        "Returns verifcation status. Requires user_id to fetch JWT token from database."
    ),
    tags={
        "fb verifcation status",
        "info",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "WABA Management"
    }
)
async def get_fb_verification_status(user_id: str) -> Dict[str, Any]:
    """
    Get fb verification status using JWT token fetched from TempMemory.

    Args:
        user_id: User ID to fetch JWT token from temporary_notes table.

    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Business info if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Fetch JWT token from TempMemory
        logger.info(f"Fetching JWT token from TempMemory for user_id: {user_id}")
        with get_session() as session:
            memory_repo = MemoryRepository(session=session)
            memory_record = memory_repo.get_by_user_id(user_id)

        if not memory_record or not memory_record.get("jwt_token"):
            error_msg = f"No JWT token found in TempMemory for user_id: {user_id}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        jwt_token = memory_record["jwt_token"]
        logger.info(f"JWT token fetched successfully for user_id: {user_id}")

        async with get_direct_api_get_client(jwt_token) as client:
            response = await client.get_fb_verification_status()
            
            if response.get("success"):
                logger.info("Successfully get_fb_verification_status info")
            else:
                logger.warning(
                    f"Failed to retrieve business info: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching fb verification status: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }