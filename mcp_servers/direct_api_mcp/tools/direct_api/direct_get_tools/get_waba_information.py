"""
MCP Tool: Get Business Info

Fetches WABA business info from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_business_info",
    description=(
        "Fetches WhatsApp Business Account (WABA) business info from the AiSensy Direct API. "
        "Returns comprehensive business details including account status, verification status, "
        "and other WABA-related information associated with the authenticated account."
    ),
    tags={
        "waba",
        "business",
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
async def get_business_info() -> Dict[str, Any]:
    """
    Fetch WABA business info.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Business info if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_business_info()
            
            if response.get("success"):
                logger.info("Successfully retrieved business info")
            else:
                logger.warning(
                    f"Failed to retrieve business info: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching business info: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }