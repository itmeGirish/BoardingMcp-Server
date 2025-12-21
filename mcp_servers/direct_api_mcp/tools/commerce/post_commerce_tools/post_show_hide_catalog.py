"""
MCP Tool: Show/Hide Catalog

Shows or hides the catalog via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import ShowHideCatalogRequest
from app import logger


@mcp.tool(
    name="show_hide_catalog",
    description=(
        "Shows or hides the catalog via the AiSensy Direct API. "
        "Updates WhatsApp commerce settings for catalog and cart visibility."
    ),
    tags={
        "catalog",
        "commerce",
        "settings",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Commerce Management"
    }
)
async def show_hide_catalog(
    enable_catalog: bool,
    enable_cart: bool
) -> Dict[str, Any]:
    """
    Show or hide the catalog.
    
    Args:
        enable_catalog: Whether to enable catalog visibility
        enable_cart: Whether to enable cart functionality
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Updated settings if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = ShowHideCatalogRequest(
            enable_catalog=enable_catalog,
            enable_cart=enable_cart
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.show_hide_catalog(
                enable_catalog=request.enable_catalog,
                enable_cart=request.enable_cart
            )
            
            if response.get("success"):
                logger.info("Successfully updated catalog visibility settings")
            else:
                logger.warning(
                    f"Failed to update catalog visibility settings: {response.get('error')}"
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
        error_msg = f"Unexpected error updating catalog visibility: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }