"""
MCP Tool: Get Billing Records

Fetches billing records for a specific project.
"""
from typing import Dict, Any

from ..import mcp
from ...models import ProjectIdRequest
from ...clients import get_aisensy_get_client
from ...models import BillingRecordsResponse
from app import logger


@mcp.tool(
    name="get_billing_records",
    description=(
        "Fetches billing records for a specific project. "
        "Returns detailed billing information including invoices, "
        "payment history, outstanding balances, and billing cycle details. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "billing",
        "records",
        "invoices",
        "payments",
        "finance",
        "project",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Analytics & Billing"
    }
)
async def get_billing_records(project_id: str) -> BillingRecordsResponse:
    """
    Fetch billing records for a project.
    
    Args:
        project_id: The unique identifier of the project to get billing records for.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Billing records data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = ProjectIdRequest(project_id=project_id)
        validated_project_id = request.project_id
        
        async with get_aisensy_get_client() as client:
            response = await client.get_billing_records(
                project_id=validated_project_id
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully retrieved billing records for project: {validated_project_id}"
                )
                return BillingRecordsResponse(**response)
            else:
                logger.warning(
                    f"Failed to retrieve billing records for project {validated_project_id}: "
                    f"{response.get('error')}"
                )
                error_msg = (
                    f"Failed to retrieve billing records for project "
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
        error_msg = f"Unexpected error fetching billing records: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }