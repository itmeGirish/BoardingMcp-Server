"""
MCP Tool: Retrieve Media by ID

Retrieves media by ID via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import RetrieveMediaByIdRequest
from app import logger


@mcp.tool(
    name="retrieve_media_by_id",
    description=(
        "Retrieves media by ID via the AiSensy Direct API. "
        "Returns the media details and download URL for the specified media ID."
    ),
    tags={
        "media",
        "retrieve",
        "get",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Media Management"
    }
)
async def retrieve_media_by_id(media_id: str) -> Dict[str, Any]:
    """
    Retrieve media by ID.
    
    Args:
        media_id: The media ID to retrieve
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Media details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = RetrieveMediaByIdRequest(media_id=media_id)
        
        async with get_direct_api_post_client() as client:
            response = await client.retrieve_media_by_id(
                media_id=request.media_id
            )
            
            if response.get("success"):
                logger.info(f"Successfully retrieved media: {request.media_id}")
            else:
                logger.warning(
                    f"Failed to retrieve media {request.media_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error retrieving media: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }