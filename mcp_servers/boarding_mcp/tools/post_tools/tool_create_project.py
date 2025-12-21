"""
MCP Tool: Create Project

Creates a new project in the AiSensy API.
"""
from typing import Dict, Any

from . .import mcp
from ...models import CreateProjectRequest
from ...clients import get_aisensy_post_client
from app import logger


@mcp.tool(
    name="create_project",
    description=(
        "Creates a new project in the AiSensy API. "
        "Requires a project name. "
        "Requires PARTNER_ID and BUSINESS_ID to be configured in settings."
    ),
    tags={
        "project",
        "create",
        "post",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Project Management"
    }
)
async def create_project(name: str) -> Dict[str, Any]:
    """
    Create a new project.
    
    Args:
        name: Name for the project.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Created project details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = CreateProjectRequest(name=name)
        
        async with get_aisensy_post_client() as client:
            response = await client.create_project(name=request.name)
            
            if response.get("success"):
                logger.info(f"Successfully created project: {request.name}")
            else:
                logger.warning(
                    f"Failed to create project: {response.get('error')}"
                )
            
            return response
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
        
    except Exception as e:
        error_msg = f"Unexpected error creating project: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }