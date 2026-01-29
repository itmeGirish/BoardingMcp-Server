"""
MCP Tool: Post Send Message

Sends a WhatsApp message via the AiSensy Direct API.
"""
from typing import Any, Dict, Optional

from .. import mcp
from ...clients import get_direct_api_post_client
from ...models import SendMessageRequest
from app import logger
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import MemoryRepository


@mcp.tool(
    name="send_message",
    description=(
        "Sends a WhatsApp message via the AiSensy Direct API. "
        "Supports sending text, image, video, audio, and document messages to individual recipients."
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
    user_id: str,
    to: str,
    message_type: str = "text",
    text_body: Optional[str] = None,
    media_link: Optional[str] = None,
    media_caption: Optional[str] = None,
    media_filename: Optional[str] = None,
    template_name: Optional[str] = None,
    template_language_code: Optional[str] = None,
    template_language_policy: Optional[str] = "deterministic",
    template_components: Optional[list] = None,
    interactive: Optional[dict] = None,
    recipient_type: str = "individual"
) -> Dict[str, Any]:
    """
    Send a WhatsApp message.

    Args:
        user_id: User ID to fetch JWT token from TempMemory
        to: Recipient phone number (e.g., "917089379345")
        message_type: Type of message: "text", "image", "video", "audio", "document", "template" (default: "text")
        text_body: The message body text (required for type "text")
        media_link: URL of the media (required for image, video, audio, document)
        media_caption: Caption for the media (optional)
        media_filename: Filename for document type (optional)
        template_name: Template name (required for type "template")
        template_language_code: Template language code (required for type "template")
        template_language_policy: Template language policy (default: "deterministic")
        template_components: Template components list (optional for type "template")
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
            message_type=message_type,
            text_body=text_body,
            media_link=media_link,
            media_caption=media_caption,
            media_filename=media_filename,
            template_name=template_name,
            template_language_code=template_language_code,
            template_language_policy=template_language_policy,
            template_components=template_components,
            interactive=interactive,
            recipient_type=recipient_type
        )
        logger.info(f"Fetching JWT token from TempMemory for user_id: {user_id}")
        with get_session() as session:
            memory_repo = MemoryRepository(session=session)
            memory_record = memory_repo.get_by_user_id(user_id)

        if not memory_record or not memory_record.get("jwt_token"):
            error_msg = f"No JWT token found in TempMemory for user_id: {user_id}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        jwt_token = memory_record["jwt_token"]
        logger.info(f"JWT token fetched successfully for user_id: {user_id}")

        async with get_direct_api_post_client() as client:
            response = await client.send_message(
                to=request.to,
                message_type=request.message_type,
                jwt_token=jwt_token,
                text_body=request.text_body,
                media_link=request.media_link,
                media_caption=request.media_caption,
                media_filename=request.media_filename,
                template_name=request.template_name,
                template_language_code=request.template_language_code,
                template_language_policy=request.template_language_policy,
                template_components=request.template_components,
                interactive=request.interactive,
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