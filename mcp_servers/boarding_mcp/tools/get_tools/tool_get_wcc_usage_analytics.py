"""
MCP Tool: Get WCC Usage Analytics

Fetches WhatsApp Cloud Credits (WCC) usage analytics for a project.
"""
from typing import Dict, Any

from ..import mcp
from ...models import ProjectIdRequest
from ...clients import get_aisensy_get_client
# from ...models import WccUsageAnalyticsResponse
from app import logger


@mcp.tool(
    name="get_wcc_usage_analytics",
    description=(
        "Fetches WhatsApp Cloud Credits (WCC) usage analytics for a specific project. "
        "Returns detailed analytics including credit consumption, message counts, "
        "usage trends, and billing period information. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "wcc",
        "whatsapp",
        "credits",
        "analytics",
        "usage",
        "billing",
        "project",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Analytics & Billing"
    }
)
async def get_wcc_usage_analytics(project_id: str) -> Dict[str, Any]:
    """
    Fetch WCC usage analytics for a project.
    
    Args:
        project_id: The unique identifier of the project to get WCC analytics for.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): WCC usage analytics data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = ProjectIdRequest(project_id=project_id)
        validated_project_id = request.project_id
        
        async with get_aisensy_get_client() as client:
            response = await client.get_wcc_usage_analytics(
                project_id=validated_project_id
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully retrieved WCC analytics for project: {validated_project_id}"
                )
                return response
            else:
                logger.warning(
                    f"Failed to retrieve WCC analytics for project {validated_project_id}: "
                    f"{response.get('error')}"
                )
                error_msg = (
                    f"Failed to retrieve WCC analytics for project "
                    f"{validated_project_id}: {response.get('error')}"
                )
                logger.warning(error_msg)
                raise ValueError(error_msg)       
            
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
        
    except Exception as e:
        error_msg = f"Unexpected error fetching WCC analytics: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }