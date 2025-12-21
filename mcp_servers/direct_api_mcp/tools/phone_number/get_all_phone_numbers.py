"""
MCP Tool: Get Phone Numbers

Fetches all phone numbers from the AiSensy Direct API.
"""
from typing import Dict, Any

from .. import mcp
from ...clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_phone_numbers",
    description=(
        "Fetches all phone numbers from the AiSensy Direct API. "
        "Returns a list of all phone numbers associated with the account "
        "including their status and configuration."
    ),
    tags={
        "phone",
        "numbers",
        "list",
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
async def get_all_phone_numbers() -> Dict[str, Any]:
    """
    Fetch all phone numbers.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (list): List of phone numbers if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_phone_numbers()
            
            if response.get("success"):
                data = response.get("data", [])
                count = len(data) if isinstance(data, list) else "unknown"
                logger.info(f"Successfully retrieved {count} phone numbers")
            else:
                logger.warning(
                    f"Failed to retrieve phone numbers: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching phone numbers: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }