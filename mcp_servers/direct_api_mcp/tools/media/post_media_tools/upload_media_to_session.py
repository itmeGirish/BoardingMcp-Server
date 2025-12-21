"""
MCP Tool: Upload Media to Session

Uploads media to an existing session via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import UploadMediaToSessionRequest
from app import logger


@mcp.tool(
    name="upload_media_to_session",
    description=(
        "Uploads media to an existing session via the AiSensy Direct API. "
        "Supports resumable uploads with byte offset."
    ),
    tags={
        "media",
        "upload",
        "session",
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
async def upload_media_to_session(
    upload_session_id: str,
    file_path: str,
    file_offset: int = 0
) -> Dict[str, Any]:
    """
    Upload media to an existing session.
    
    Args:
        upload_session_id: The upload session ID
        file_path: Path to the file to upload
        file_offset: Byte offset for resumable uploads (default: 0)
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Upload response if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = UploadMediaToSessionRequest(
            upload_session_id=upload_session_id,
            file_path=file_path,
            file_offset=file_offset
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.upload_media_to_session(
                upload_session_id=request.upload_session_id,
                file_path=request.file_path,
                file_offset=request.file_offset
            )
            
            if response.get("success"):
                logger.info(f"Successfully uploaded media to session: {request.upload_session_id}")
            else:
                logger.warning(
                    f"Failed to upload media to session {request.upload_session_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error uploading media to session: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }