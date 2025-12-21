"""
MCP Tool: Get Phone Number

Fetches the primary/default phone number from the AiSensy Direct API.
"""
from typing import Dict, Any

from .. import mcp
from ...clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_phone_number",
    description=(
        "Fetches the primary/default phone number from the AiSensy Direct API. "
        "Returns the phone number details including status and configuration "
        "for the default phone number associated with the account."
    ),
    tags={
        "phone",
        "number",
        "primary",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Phone Management"
    }
)
async def get_single_phone_number() -> Dict[str, Any]:
    """
    Fetch the primary/default phone number.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Phone number details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_phone_number()
            
            if response.get("success"):
                logger.info("Successfully retrieved phone number")
            else:
                logger.warning(
                    f"Failed to retrieve phone number: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching phone number: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }