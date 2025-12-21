"""
MCP Tool: Get Profile

Fetches user profile from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_profile",
    description=(
        "Fetches user profile from the AiSensy Direct API. "
        "Returns profile details for the authenticated account including "
        "business information, contact details, and settings."
    ),
    tags={
        "profile",
        "user",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Profile Management"
    }
)
async def get_profile() -> Dict[str, Any]:
    """
    Fetch user profile.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Profile details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_profile()
            
            if response.get("success"):
                logger.info("Successfully retrieved profile")
            else:
                logger.warning(
                    f"Failed to retrieve profile: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching profile: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }