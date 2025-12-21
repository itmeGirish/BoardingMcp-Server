"""
MCP Tool: Edit Template

Edits a WhatsApp template via the AiSensy Direct API.
"""
from typing import Dict, Any, List

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import EditTemplateRequest
from app import logger


@mcp.tool(
    name="edit_template",
    description=(
        "Edits a WhatsApp template via the AiSensy Direct API. "
        "Updates the template components for the specified template ID."
    ),
    tags={
        "template",
        "edit",
        "update",
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
async def edit_template(
    template_id: str,
    category: str,
    components: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Edit a WhatsApp template.
    
    Args:
        template_id: The template ID to edit
        category: Template category (MARKETING, UTILITY, AUTHENTICATION)
        components: List of template components (HEADER, BODY, FOOTER, BUTTONS)
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Updated template details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = EditTemplateRequest(
            template_id=template_id,
            category=category,
            components=components
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.edit_template(
                template_id=request.template_id,
                category=request.category,
                components=request.components
            )
            
            if response.get("success"):
                logger.info(f"Successfully edited template: {request.template_id}")
            else:
                logger.warning(
                    f"Failed to edit template {request.template_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error editing template: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }