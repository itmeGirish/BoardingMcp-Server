"""
MCP Tool: Post Send Message

Sends a WhatsApp message via the AiSensy Direct API.
"""
from typing import Dict, Any

from .. import mcp
from ...clients import get_direct_api_post_client
from ...models import SendMessageRequest
from app import logger


@mcp.tool(
    name="send_message",
    description=(
        "Sends a WhatsApp message via the AiSensy Direct API. "
        "Supports sending text messages to individual recipients."
    ),
    tags={
        "message",
        "send",
        "whatsapp",
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
async def send_message(
    to: str,
    text_body: str,
    message_type: str = "text",
    recipient_type: str = "individual"
) -> Dict[str, Any]:
    """
    Send a WhatsApp message.
    
    Args:
        to: Recipient phone number (e.g., "917089379345")
        text_body: The message body text
        message_type: Type of message (default: "text")
        recipient_type: Type of recipient (default: "individual")
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Message response if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = SendMessageRequest(
            to=to,
            text_body=text_body,
            message_type=message_type,
            recipient_type=recipient_type
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.send_message(
                to=request.to,
                message_type=request.message_type,
                text_body=request.text_body,
                recipient_type=request.recipient_type
            )
            
            if response.get("success"):
                logger.info(f"Successfully sent message to: {request.to}")
            else:
                logger.warning(
                    f"Failed to send message to {request.to}: {response.get('error')}"
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
        error_msg = f"Unexpected error sending message: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }