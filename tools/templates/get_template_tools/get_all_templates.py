"""
MCP Tool: Get Templates

Fetches all templates from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


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
async def get_templates() -> Dict[str, Any]:
    """
    Fetch all templates.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (list): List of templates if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_templates()
            
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