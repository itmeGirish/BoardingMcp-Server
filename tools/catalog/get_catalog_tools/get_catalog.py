"""
MCP Tool: Get Catalog

Fetches the catalog from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_catalog",
    description=(
        "Fetches the catalog from the AiSensy Direct API. "
        "Returns the catalog details including products, images, "
        "and configuration for the connected catalog."
    ),
    tags={
        "catalog",
        "commerce",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Catalog Management"
    }
)
async def get_catalog() -> Dict[str, Any]:
    """
    Fetch the catalog.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Catalog details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_catalog()
            
            if response.get("success"):
                logger.info("Successfully retrieved catalog")
            else:
                logger.warning(
                    f"Failed to retrieve catalog: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching catalog: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }