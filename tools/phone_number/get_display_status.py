"""
MCP Tool: Get Display Name Status

Fetches the display name status (FB verification status) from the AiSensy Direct API.
"""
from typing import Dict, Any

from .. import mcp
from ...clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_display_name_status",
    description=(
        "Fetches the display name status from the AiSensy Direct API. "
        "Returns the current Facebook Business verification status "
        "including verification state and submission status."
    ),
    tags={
        "display",
        "name",
        "status",
        "verification",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Verification Management"
    }
)
async def get_display_name_status() -> Dict[str, Any]:
    """
    Fetch the display name status.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Display name status if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_display_name_status()
            
            if response.get("success"):
                logger.info("Successfully retrieved display name status")
            else:
                logger.warning(
                    f"Failed to retrieve display name status: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching display name status: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }