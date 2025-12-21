"""
MCP Tool: Get WhatsApp Commerce Settings

Fetches WhatsApp commerce settings from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_whatsapp_commerce_settings",
    description=(
        "Fetches WhatsApp commerce settings from the AiSensy Direct API. "
        "Returns the commerce configuration including catalog visibility, "
        "cart settings, and other commerce-related options."
    ),
    tags={
        "commerce",
        "settings",
        "whatsapp",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Commerce Management"
    }
)
async def get_commerce_settings() -> Dict[str, Any]:
    """
    Fetch WhatsApp commerce settings.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Commerce settings if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_whatsapp_commerce_settings()
            
            if response.get("success"):
                logger.info("Successfully retrieved WhatsApp commerce settings")
            else:
                logger.warning(
                    f"Failed to retrieve WhatsApp commerce settings: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching WhatsApp commerce settings: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }