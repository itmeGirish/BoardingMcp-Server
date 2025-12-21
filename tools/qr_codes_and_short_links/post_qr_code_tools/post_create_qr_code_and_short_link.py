"""
MCP Tool: Create QR Code and Short Link

Creates a QR code and short link via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import CreateQrCodeAndShortLinkRequest
from app import logger


@mcp.tool(
    name="create_qr_code_and_short_link",
    description=(
        "Creates a QR code and short link via the AiSensy Direct API. "
        "Returns a QR code image and short link with the specified prefilled message."
    ),
    tags={
        "qr",
        "code",
        "short",
        "link",
        "create",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "QR Code Management"
    }
)
async def create_qr_code_and_short_link(
    prefilled_message: str,
    generate_qr_image: str = "SVG"
) -> Dict[str, Any]:
    """
    Create a QR code and short link.
    
    Args:
        prefilled_message: The prefilled message for the QR code
        generate_qr_image: QR image format (default: "SVG")
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): QR code and short link details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = CreateQrCodeAndShortLinkRequest(
            prefilled_message=prefilled_message,
            generate_qr_image=generate_qr_image
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.create_qr_code_and_short_link(
                prefilled_message=request.prefilled_message,
                generate_qr_image=request.generate_qr_image
            )
            
            if response.get("success"):
                logger.info("Successfully created QR code and short link")
            else:
                logger.warning(
                    f"Failed to create QR code and short link: {response.get('error')}"
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
        error_msg = f"Unexpected error creating QR code and short link: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }