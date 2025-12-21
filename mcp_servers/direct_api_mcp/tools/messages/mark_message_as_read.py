"""
MCP Tool: POST Mark Message as Read

Marks a message as read via the AiSensy Direct API.
"""
from typing import Dict, Any

from .. import mcp
from ...clients import get_direct_api_post_client
from ...models import MarkMessageAsReadRequest
from app import logger


@mcp.tool(
    name="mark_message_as_read",
    description=(
        "Marks a message as read via the AiSensy Direct API. "
        "Updates the read status of the specified message."
    ),
    tags={
        "message",
        "read",
        "status",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Messaging"
    }
)
async def mark_message_as_read(message_id: str) -> Dict[str, Any]:
    """
    Mark a message as read.
    
    Args:
        message_id: The message ID to mark as read
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = MarkMessageAsReadRequest(message_id=message_id)
        
        async with get_direct_api_post_client() as client:
            response = await client.mark_message_as_read(
                message_id=request.message_id
            )
            
            if response.get("success"):
                logger.info(f"Successfully marked message as read: {request.message_id}")
            else:
                logger.warning(
                    f"Failed to mark message as read {request.message_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error marking message as read: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }