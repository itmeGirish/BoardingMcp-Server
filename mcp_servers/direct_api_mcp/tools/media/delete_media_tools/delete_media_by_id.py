"""
MCP Tool: Delete Media by ID

Deletes media by ID via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_delete_client
from ....models import DeleteMediaByIdRequest
from app import logger


@mcp.tool(
    name="delete_media_by_id",
    description=(
        "Deletes media by ID via the AiSensy Direct API. "
        "Permanently removes the media from the account. "
        "This action cannot be undone."
    ),
    tags={
        "media",
        "delete",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Media Management"
    }
)
async def delete_media_by_id(media_id: str) -> Dict[str, Any]:
    """
    Delete media by ID.
    
    Args:
        media_id: The media ID to delete
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = DeleteMediaByIdRequest(media_id=media_id)
        
        async with get_direct_api_delete_client() as client:
            response = await client.delete_media_by_id(
                media_id=request.media_id
            )
            
            if response.get("success"):
                logger.info(f"Successfully deleted media by ID: {request.media_id}")
            else:
                logger.warning(
                    f"Failed to delete media by ID {request.media_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error deleting media by ID: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }