"""
MCP Tool: Get KYC Submission Status
Fetches the KYC submission status for a specific project.
"""
from typing import Dict, Any
from .. import mcp
from ...models import ProjectIdRequest
from ...models import KycSubmissionStatusResponse
from ...clients import get_aisensy_get_client
from app import logger


@mcp.tool(
    name="get_kyc_submission_status",
    description=(
        "Fetches the KYC (Know Your Customer) submission status for a specific project. "
        "Returns details about the KYC verification process including status, "
        "submission date, and any pending requirements. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "kyc",
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
async def get_kyc_submission_status(project_id: str) -> KycSubmissionStatusResponse:
    """
    Fetch KYC submission status for a project.
    
    Args:
        project_id: The unique identifier of the project to check KYC status for.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): KYC status details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = ProjectIdRequest(project_id=project_id)
        validated_project_id = request.project_id
        
        async with get_aisensy_get_client() as client:
            response = await client.get_kyc_submission_status(
                project_id=validated_project_id
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully retrieved KYC status for project: {validated_project_id}"
                )
                return KycSubmissionStatusResponse(**response)

            else:
                logger.warning(
                    f"Failed to retrieve KYC status for project {validated_project_id}: "
                    f"{response.get('error')}"
                )
                error_msg = (
                    f"Failed to retrieve KYC status for project "
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
        error_msg = f"Unexpected error fetching KYC status: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }