"""
MCP Tool: Get All Business Projects

Fetches all projects associated with a business.
"""
from typing import Dict, Any, Optional

from ..import mcp
from ...models import BusinessProjectsRequest
from ...clients import get_aisensy_get_client
from ...models import ProjectResponse
from app import logger


@mcp.tool(
    name="get_all_business_projects",
    description=(
        "Fetches all projects associated with the configured business. "
        "Returns a list of projects with optional field filtering. "
        "Use 'fields' parameter to specify which fields to include in response. "
        "Use 'additional_fields' parameter to include extra metadata. "
        "Requires PARTNER_ID and BUSINESS_ID to be configured in settings."
    ),
    tags={
        "business",
        "projects",
        "list",
        "get",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Project Management"
    }
)
async def get_all_business_projects(
    fields: Optional[str] = None,
    additional_fields: Optional[str] = None
) -> ProjectResponse:
    """
    Fetch all projects for the configured business.
    
    Args:
        fields: Optional comma-separated list of fields to include in response.
               Example: "name,status,createdAt"
        additional_fields: Optional comma-separated list of additional fields 
                          to include. Example: "metadata,settings"
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (list): List of project details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = BusinessProjectsRequest(
            fields=fields,
            additional_fields=additional_fields
        )
        
        async with get_aisensy_get_client() as client:
            response = await client.get_all_business_projects(
                fields=request.fields,
                additional_fields=request.additional_fields
            )
            
            if response.get("success"):
                data = response.get("data", [])
                count = len(data) if isinstance(data, list) else "unknown"
                logger.info(f"Successfully retrieved {count} business projects")
                return ProjectResponse(projects=response["data"])
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
        error_msg = f"Unexpected error fetching business projects: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }