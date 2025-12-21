"""
MCP Tool: Update Business Profile Details

Updates the business profile details via the AiSensy Direct API.
"""
from typing import Dict, Any, Optional, List

from ... import mcp
from ....clients import get_direct_api_patch_client
from ....models import UpdateBusinessProfileDetailsRequest
from app import logger


@mcp.tool(
    name="update_business_profile_details",
    description=(
        "Updates the business profile details via the AiSensy Direct API. "
        "Supports updating about text, address, description, vertical, "
        "email, websites, and profile image."
    ),
    tags={
        "profile",
        "details",
        "update",
        "patch",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Profile Management"
    }
)
async def update_business_profile_details(
    whatsapp_about: Optional[str] = None,
    address: Optional[str] = None,
    description: Optional[str] = None,
    vertical: Optional[str] = None,
    email: Optional[str] = None,
    websites: Optional[List[str]] = None,
    whatsapp_display_image: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update the business profile details.
    
    Args:
        whatsapp_about: WhatsApp about/status text (optional)
        address: Business address (optional)
        description: Business description (optional)
        vertical: Business vertical (optional)
        email: Business email (optional)
        websites: List of business website URLs (optional)
        whatsapp_display_image: URL of the profile picture (optional)
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = UpdateBusinessProfileDetailsRequest(
            whatsapp_about=whatsapp_about,
            address=address,
            description=description,
            vertical=vertical,
            email=email,
            websites=websites,
            whatsapp_display_image=whatsapp_display_image
        )
        
        async with get_direct_api_patch_client() as client:
            response = await client.update_business_profile_details(
                whatsapp_about=request.whatsapp_about,
                address=request.address,
                description=request.description,
                vertical=request.vertical,
                email=request.email,
                websites=request.websites,
                whatsapp_display_image=request.whatsapp_display_image
            )
            
            if response.get("success"):
                logger.info("Successfully updated business profile details")
            else:
                logger.warning(
                    f"Failed to update business profile details: {response.get('error')}"
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
        error_msg = f"Unexpected error updating business profile details: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }