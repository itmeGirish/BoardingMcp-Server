"""
MCP Tool: Get fb verification status

Fetches fb verification status info from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="fb_verification_status",
    description=(
        "Fetches fb verification status info from the AiSensy Direct API. "
        "Returns verifcation status"
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
async def get_fb_verification_status() -> Dict[str, Any]:
    """
   get fb verification status
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Business info if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
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