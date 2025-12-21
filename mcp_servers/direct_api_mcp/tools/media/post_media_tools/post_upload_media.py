"""
MCP Tool: Upload Media

Uploads media via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import UploadMediaRequest
from app import logger


@mcp.tool(
    name="upload_media",
    description=(
        "Uploads media via the AiSensy Direct API. "
        "Supports uploading images, videos, and documents."
    ),
    tags={
        "media",
        "upload",
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
async def upload_media(file_path: str) -> Dict[str, Any]:
    """
    Upload media.
    
    Args:
        file_path: Path to the file to upload
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Upload response if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = UploadMediaRequest(file_path=file_path)
        
        async with get_direct_api_post_client() as client:
            response = await client.upload_media(
                file_path=request.file_path
            )
            
            if response.get("success"):
                logger.info(f"Successfully uploaded media: {request.file_path}")
            else:
                logger.warning(
                    f"Failed to upload media {request.file_path}: {response.get('error')}"
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
        error_msg = f"Unexpected error uploading media: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }