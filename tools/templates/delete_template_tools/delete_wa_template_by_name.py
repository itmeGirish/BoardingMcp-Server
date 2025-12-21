"""
MCP Tool: Delete WA Template by Name

Deletes a WhatsApp template by name via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_delete_client
from ....models import DeleteWaTemplateByNameRequest
from app import logger


@mcp.tool(
    name="delete_wa_template_by_name",
    description=(
        "Deletes a WhatsApp template by name via the AiSensy Direct API. "
        "Permanently removes the template from the account. "
        "This action cannot be undone."
    ),
    tags={
        "template",
        "delete",
        "whatsapp",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Template Management"
    }
)
async def delete_wa_template_by_name(template_name: str) -> Dict[str, Any]:
    """
    Delete a WhatsApp template by name.
    
    Args:
        template_name: The template name to delete
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = DeleteWaTemplateByNameRequest(template_name=template_name)
        
        async with get_direct_api_delete_client() as client:
            response = await client.delete_wa_template_by_name(
                template_name=request.template_name
            )
            
            if response.get("success"):
                logger.info(f"Successfully deleted template by name: {request.template_name}")
            else:
                logger.warning(
                    f"Failed to delete template by name {request.template_name}: {response.get('error')}"
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
        error_msg = f"Unexpected error deleting template by name: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }