"""
MCP Tool: Get Template by ID

Fetches a specific template by ID from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from ....models import TemplateIdRequest
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import MemoryRepository
from app import logger


@mcp.tool(
    name="get_template_by_id",
    description=(
        "Fetches a specific WhatsApp template by ID from the AiSensy Direct API. "
        "Returns the template details including name, category, language, components, "
        "and approval status for the given template ID."
    ),
    tags={
        "template",
        "detail",
        "whatsapp",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Template Management"
    }
)
async def get_template_by_id(user_id:str,template_id: str) -> Dict[str, Any]:
    """
    Fetch a specific template by ID.
    
    Args:
        template_id: The unique template identifier
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Template details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = TemplateIdRequest(template_id=template_id)

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


        
        async with get_direct_api_get_client() as client:
            response = await client.get_template_by_id(
                template_id=request.template_id,
                token=jwt_token
            )
            
            if response.get("success"):
                logger.info(f"Successfully retrieved template: {request.template_id}")
            else:
                logger.warning(
                    f"Failed to retrieve template {request.template_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error fetching template: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }