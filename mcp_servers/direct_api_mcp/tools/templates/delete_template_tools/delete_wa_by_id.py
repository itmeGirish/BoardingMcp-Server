"""
MCP Tool: Delete WA Template by ID

Deletes a WhatsApp template by ID via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_delete_client
from ....models import DeleteWaTemplateByIdRequest
from app import logger
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import MemoryRepository



@mcp.tool(
    name="delete_wa_template_by_id",
    description=(
        "Deletes a WhatsApp template by ID via the AiSensy Direct API. "
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
async def delete_wa_template_by_id(user_id:str,template_id: str,template_name:str) -> Dict[str, Any]:
    """
    Delete a WhatsApp template by ID.
    
    Args:
        template_id: The template ID to delete
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = DeleteWaTemplateByIdRequest(template_id=template_id,template_name=template_name)
        
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

        
        async with get_direct_api_delete_client() as client:
            response = await client.delete_wa_template_by_id(
                template_id=request.template_id,
                template_name=template_name,
                jwt_token=jwt_token
            )
            
            if response.get("success"):
                logger.info(f"Successfully deleted template by ID: {request.template_id}")
            else:
                logger.warning(
                    f"Failed to delete template by ID {request.template_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error deleting template by ID: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }