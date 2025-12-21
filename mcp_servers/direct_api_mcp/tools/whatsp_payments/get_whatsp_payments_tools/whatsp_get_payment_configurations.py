"""
MCP Tool: Get Payment Configurations

Fetches all payment configurations from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_payment_configurations",
    description=(
        "Fetches all payment configurations from the AiSensy Direct API. "
        "Returns a list of all payment configurations including provider details, "
        "redirect URLs, and configuration settings."
    ),
    tags={
        "payment",
        "configurations",
        "list",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Payment Management"
    }
)
async def get_payment_configurations() -> Dict[str, Any]:
    """
    Fetch all payment configurations.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (list): List of payment configurations if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_payment_configurations()
            
            if response.get("success"):
                data = response.get("data", [])
                count = len(data) if isinstance(data, list) else "unknown"
                logger.info(f"Successfully retrieved {count} payment configurations")
            else:
                logger.warning(
                    f"Failed to retrieve payment configurations: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching payment configurations: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }