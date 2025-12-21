"""
MCP Tool: Update Business Profile Picture

Updates the business profile picture via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_patch_client
from ....models import UpdateBusinessProfilePictureRequest
from app import logger


@mcp.tool(
    name="update_business_profile_picture",
    description=(
        "Updates the business profile picture via the AiSensy Direct API. "
        "Sets a new profile image from the provided URL."
    ),
    tags={
        "profile",
        "picture",
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
async def update_business_profile_picture(whatsapp_display_image: str) -> Dict[str, Any]:
    """
    Update the business profile picture.
    
    Args:
        whatsapp_display_image: URL of the new profile picture
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = UpdateBusinessProfilePictureRequest(
            whatsapp_display_image=whatsapp_display_image
        )
        
        async with get_direct_api_patch_client() as client:
            response = await client.update_business_profile_picture(
                whatsapp_display_image=request.whatsapp_display_image
            )
            
            if response.get("success"):
                logger.info("Successfully updated business profile picture")
            else:
                logger.warning(
                    f"Failed to update business profile picture: {response.get('error')}"
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
        error_msg = f"Unexpected error updating business profile picture: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }