"""
MCP Tool: Get WhatsApp Business Encryption

Fetches WhatsApp Business encryption settings from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_whatsapp_business_encryption",
    description=(
        "Fetches WhatsApp Business encryption settings from the AiSensy Direct API. "
        "Returns the current encryption configuration including public key status, "
        "encryption enabled state, and other security-related settings for the "
        "WhatsApp Business Account."
    ),
    tags={
        "encryption",
        "security",
        "public-key",
        "whatsapp",
        "business",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Security Management"
    }
)
async def get_whatsapp_business_encryption() -> Dict[str, Any]:
    """
    Fetch WhatsApp Business encryption settings.
    
    This tool retrieves the current encryption configuration for the
    WhatsApp Business Account, including:
    - Whether encryption is enabled
    - Public key status and details
    - Encryption configuration settings
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Encryption settings if successful, including:
            - encryption_enabled (bool): Whether encryption is active
            - public_key_status (str): Status of the configured public key
            - key_details (dict): Details about the encryption key
        - error (str): Error message if unsuccessful
    
    Example:
        >>> result = await get_whatsapp_business_encryption()
        >>> if result["success"]:
        ...     data = result["data"]
        ...     print(f"Encryption enabled: {data.get('encryption_enabled')}")
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_whatsapp_business_encryption()
            
            if response.get("success"):
                logger.info("Successfully retrieved WhatsApp Business encryption settings")
            else:
                logger.warning(
                    f"Failed to retrieve WhatsApp Business encryption settings: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching WhatsApp Business encryption settings: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }