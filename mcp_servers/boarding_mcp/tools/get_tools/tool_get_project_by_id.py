"""
MCP Tool: Get Project by ID

Fetches project details by project ID.
"""
from typing import Dict, Any

from ..import mcp
from ...models import ProjectIdRequest
from ...clients import get_aisensy_get_client
from ...models import ProjectIDResponse
from app import logger


@mcp.tool(
    name="get_project_by_id",
    description=(
        "Fetches detailed information about a specific project by its ID. "
        "Returns comprehensive project details including configuration, "
        "status, associated phone numbers, and metadata. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "project",
        "details",
        "get",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Project Management"
    }
)
async def get_project_by_id(project_id: str) -> ProjectIDResponse:
    """
    Fetch project details by project ID.
    
    Args:
        project_id: The unique identifier of the project to fetch.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Project details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = ProjectIdRequest(project_id=project_id)
        validated_project_id = request.project_id
        
        async with get_aisensy_get_client() as client:
            response = await client.get_project_by_id(
                project_id=validated_project_id
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully retrieved project details for: {validated_project_id}"
                )
                return ProjectIDResponse(**response)
            else:
                error_msg = response.get("error", "Unknown error")
                status_code = response.get("status_code", "N/A")
                details = response.get("details", {})
                
                full_error = f"{error_msg} | Status: {status_code} | Details: {details}"
                logger.warning(full_error)
                raise full_error
      
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
        
    except Exception as e:
        error_msg = f"Unexpected error fetching project by ID: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }