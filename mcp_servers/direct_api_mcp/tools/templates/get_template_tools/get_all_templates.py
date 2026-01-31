"""
MCP Tool: Get Templates

Fetches all templates from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import MemoryRepository


@mcp.tool(
    name="get_templates",
    description=(
        "Fetches all WhatsApp templates from the AiSensy Direct API. "
        "Returns a list of all templates associated with the account "
        "including their name, category, language, and approval status."
    ),
    tags={
        "templates",
        "list",
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
async def get_templates(user_id:str) -> Dict[str, Any]:
    """
    Fetch all templates.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (list): List of templates if successful
        - error (str): Error message if unsuccessful
    """
    try:
        
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
            response = await client.get_templates(jwt_token=jwt_token)
            
            if response.get("success"):
                data = response.get("data", [])
                count = len(data) if isinstance(data, list) else "unknown"
                logger.info(f"Successfully retrieved {count} templates")
            else:
                logger.warning(
                    f"Failed to retrieve templates: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching templates: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }