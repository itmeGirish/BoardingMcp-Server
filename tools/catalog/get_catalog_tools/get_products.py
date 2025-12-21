"""
MCP Tool: Get Products

Fetches all products from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_products",
    description=(
        "Fetches all products from the AiSensy Direct API. "
        "Returns a list of all products in the catalog including "
        "name, price, images, and availability."
    ),
    tags={
        "products",
        "catalog",
        "commerce",
        "list",
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
async def get_products() -> Dict[str, Any]:
    """
    Fetch all products.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (list): List of products if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_products()
            
            if response.get("success"):
                data = response.get("data", [])
                count = len(data) if isinstance(data, list) else "unknown"
                logger.info(f"Successfully retrieved {count} products")
            else:
                logger.warning(
                    f"Failed to retrieve products: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching products: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }