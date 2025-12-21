"""
MCP Tool: Create Upload Session

Creates an upload session via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import CreateUploadSessionRequest
from app import logger


@mcp.tool(
    name="create_upload_session",
    description=(
        "Creates an upload session via the AiSensy Direct API. "
        "Returns a session ID for resumable media uploads."
    ),
    tags={
        "media",
        "upload",
        "session",
        "create",
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
async def create_upload_session(
    file_name: str,
    file_length: str,
    file_type: str
) -> Dict[str, Any]:
    """
    Create an upload session.
    
    Args:
        file_name: Name of the file to upload
        file_length: Size of the file in bytes
        file_type: MIME type of the file (e.g., "image/jpg")
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Session details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = CreateUploadSessionRequest(
            file_name=file_name,
            file_length=file_length,
            file_type=file_type
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.create_upload_session(
                file_name=request.file_name,
                file_length=request.file_length,
                file_type=request.file_type
            )
            
            if response.get("success"):
                logger.info(f"Successfully created upload session for: {request.file_name}")
            else:
                logger.warning(
                    f"Failed to create upload session for {request.file_name}: {response.get('error')}"
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
        error_msg = f"Unexpected error creating upload session: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }