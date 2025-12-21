"""
MCP Tool: Set Business Public Key

Sets the business public key for WhatsApp Business encryption via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import SetBusinessPublicKeyRequest
from app import logger


@mcp.tool(
    name="set_business_public_key",
    description=(
        "Sets the business public key for WhatsApp Business encryption via the AiSensy Direct API. "
        "Configures end-to-end encryption settings for secure message handling. "
        "The public key must be in PEM format starting with '-----BEGIN PUBLIC KEY-----' "
        "and ending with '-----END PUBLIC KEY-----'."
    ),
    tags={
        "encryption",
        "security",
        "public-key",
        "whatsapp",
        "business",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Security Management"
    }
)
async def set_business_public_key(business_public_key: str) -> Dict[str, Any]:
    """
    Set the business public key for WhatsApp Business encryption.
    
    This tool configures the public key used for end-to-end encryption
    in WhatsApp Business communications. The key enables secure message
    handling between your business and WhatsApp.
    
    Args:
        business_public_key: The business public key in PEM format.
            Must start with '-----BEGIN PUBLIC KEY-----' and end with
            '-----END PUBLIC KEY-----'. The key content should be
            base64 encoded and may contain newline characters.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful, including:
            - status: Confirmation of key update
            - encryption_enabled: Whether encryption is now enabled
        - error (str): Error message if unsuccessful
    
    Example:
        >>> key = '''-----BEGIN PUBLIC KEY-----
        ... MIIBIkANBglqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
        ... -----END PUBLIC KEY-----'''
        >>> result = await set_business_public_key(key)
        >>> if result["success"]:
        ...     print("Encryption key set successfully")
    """
    try:
        # Validate input
        request = SetBusinessPublicKeyRequest(business_public_key=business_public_key)
        
        async with get_direct_api_post_client() as client:
            response = await client.set_business_public_key(
                business_public_key=request.business_public_key
            )
            
            if response.get("success"):
                logger.info("Successfully set business public key for encryption")
            else:
                logger.warning(
                    f"Failed to set business public key: {response.get('error')}"
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
        error_msg = f"Unexpected error setting business public key: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }