"""
MCP Tool: Get Flows

Fetches all flows from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_flows",
    description=(
        "Fetches all flows from the AiSensy Direct API. "
        "Returns a list of all flows including their name, categories, "
        "status, and configuration."
    ),
    tags={
        "flows",
        "list",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Flow Management"
    }
)
async def get_flows() -> Dict[str, Any]:
    """
    Fetch all flows.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (list): List of flows if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_flows()
            
            if response.get("success"):
                data = response.get("data", [])
                count = len(data) if isinstance(data, list) else "unknown"
                logger.info(f"Successfully retrieved {count} flows")
            else:
                logger.warning(
                    f"Failed to retrieve flows: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching flows: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }