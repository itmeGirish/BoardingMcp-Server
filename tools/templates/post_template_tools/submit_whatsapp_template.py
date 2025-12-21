"""
MCP Tool: Submit WhatsApp Template Message

Submits a WhatsApp Template Message via the AiSensy Direct API.
"""
from typing import Dict, Any, List

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import SubmitWhatsappTemplateMessageRequest
from app import logger


@mcp.tool(
    name="submit_whatsapp_template_message",
    description=(
        "Submits a WhatsApp Template Message via the AiSensy Direct API. "
        "Creates a new template with specified components for approval."
    ),
    tags={
        "template",
        "submit",
        "create",
        "whatsapp",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Template Management"
    }
)
async def submit_whatsapp_template_message(
    name: str,
    category: str,
    language: str,
    components: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Submit a WhatsApp Template Message.
    
    Args:
        name: Template name
        category: Template category (MARKETING, UTILITY, AUTHENTICATION)
        language: Template language (e.g., "en")
        components: List of template components (HEADER, BODY, FOOTER, BUTTONS)
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Created template details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = SubmitWhatsappTemplateMessageRequest(
            name=name,
            category=category,
            language=language,
            components=components
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.submit_whatsapp_template_message(
                name=request.name,
                category=request.category,
                language=request.language,
                components=request.components
            )
            
            if response.get("success"):
                logger.info(f"Successfully submitted WhatsApp template: {request.name}")
            else:
                logger.warning(
                    f"Failed to submit WhatsApp template {request.name}: {response.get('error')}"
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
        error_msg = f"Unexpected error submitting WhatsApp template: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }