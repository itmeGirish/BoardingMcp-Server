"""
MCP Tool: Disconnect Catalog

Disconnects the catalog via the AiSensy Direct API.
"""
from typing import Dict, Any

from ...import mcp
from ....clients import get_direct_api_delete_client
from app import logger


@mcp.tool(
    name="disconnect_catalog",
    description=(
        "Disconnects the catalog via the AiSensy Direct API. "
        "Removes the catalog connection from the WhatsApp Business Account. "
        "This action cannot be undone."
    ),
    tags={
        "catalog",
        "disconnect",
        "delete",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Catalog Management"
    }
)
async def disconnect_catalog() -> Dict[str, Any]:
    """
    Disconnect the catalog.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_delete_client() as client:
            response = await client.disconnect_catalog()
            
            if response.get("success"):
                logger.info("Successfully disconnected catalog")
            else:
                logger.warning(
                    f"Failed to disconnect catalog: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error disconnecting catalog: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }