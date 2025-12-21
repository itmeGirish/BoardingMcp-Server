"""
MCP Tool: Connect Catalog

Connects a catalog via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import ConnectCatalogRequest
from app import logger


@mcp.tool(
    name="connect_catalog",
    description=(
        "Connects a catalog via the AiSensy Direct API. "
        "Links the specified catalog to the WhatsApp Business Account."
    ),
    tags={
        "catalog",
        "connect",
        "commerce",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Catalog Management"
    }
)
async def connect_catalog(catalog_id: str) -> Dict[str, Any]:
    """
    Connect a catalog.
    
    Args:
        catalog_id: The catalog ID to connect
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = ConnectCatalogRequest(catalog_id=catalog_id)
        
        async with get_direct_api_post_client() as client:
            response = await client.connect_catalog(
                catalog_id=request.catalog_id
            )
            
            if response.get("success"):
                logger.info(f"Successfully connected catalog: {request.catalog_id}")
            else:
                logger.warning(
                    f"Failed to connect catalog {request.catalog_id}: {response.get('error')}"
                )
            
            return response
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.warning(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error connecting catalog: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }