"""
MCP Tool: Get Business Verification Status

Fetches the business verification status for a specific project.
"""
from typing import Dict, Any

from .. import mcp
from ...models import ProjectIdRequest
from ...clients import get_aisensy_get_client
from ...models import BusinessVerificationStatusResponse
from app import logger


@mcp.tool(
    name="get_business_verification_status",
    description=(
        "Fetches the business verification status for a specific project. "
        "Returns details about the business verification process including "
        "verification state, completion percentage, and any required actions. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "business",
        "verification",
        "status",
        "compliance",
        "project",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "KYC & Compliance"
    }
)
async def get_business_verification_status(project_id: str) -> BusinessVerificationStatusResponse:
    """
    Fetch business verification status for a project.
    
    Args:
        project_id: The unique identifier of the project to check 
                   business verification status for.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Business verification status details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = ProjectIdRequest(project_id=project_id)
        validated_project_id = request.project_id
        
        async with get_aisensy_get_client() as client:
            response = await client.get_business_verification_status(
                project_id=validated_project_id
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully retrieved business verification status "
                    f"for project: {validated_project_id}"
                )
                return BusinessVerificationStatusResponse(**response)

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
        error_msg = f"Unexpected error fetching business verification status: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }