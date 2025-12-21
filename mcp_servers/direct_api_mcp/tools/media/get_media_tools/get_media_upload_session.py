"""
MCP Tool: Get Media Upload Session

Fetches media upload session status from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from ....models import UploadSessionIdRequest
from app import logger


@mcp.tool(
    name="get_media_upload_session",
    description=(
        "Fetches media upload session status from the AiSensy Direct API. "
        "Returns the upload session details including status, progress, "
        "and file information for the given session ID."
    ),
    tags={
        "media",
        "upload",
        "session",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Media Management"
    }
)
async def get_media_upload_session(upload_session_id: str) -> Dict[str, Any]:
    """
    Fetch media upload session status.
    
    Args:
        upload_session_id: The unique upload session identifier
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Upload session details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = UploadSessionIdRequest(upload_session_id=upload_session_id)
        
        async with get_direct_api_get_client() as client:
            response = await client.get_media_upload_session(
                upload_session_id=request.upload_session_id
            )
            
            if response.get("success"):
                logger.info(f"Successfully retrieved upload session: {request.upload_session_id}")
            else:
                logger.warning(
                    f"Failed to retrieve upload session {request.upload_session_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error fetching upload session: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }