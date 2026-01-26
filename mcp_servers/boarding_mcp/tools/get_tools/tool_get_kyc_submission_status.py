"""
MCP Tool: Get KYC Submission Status

Fetches the KYC submission status for a specific project.
This version FETCHES project_id from database based on user_id.
"""
from typing import Dict, Any

from .. import mcp
from ...models import KycSubmissionStatusResponse
from ...clients import get_aisensy_get_client
from app import logger
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import (
    ProjectCreationRepository
)


@mcp.tool(
    name="get_kyc_submission_status",
    description=(
        "Fetches the KYC (Know Your Customer) submission status for a specific project. "
        "Returns details about the KYC verification process including status, "
        "submission date, and any pending requirements. "
        "Requires user_id - the project_id is automatically retrieved from the database."
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
async def get_kyc_submission_status(user_id: str) -> KycSubmissionStatusResponse:
    """
    Fetch KYC submission status for a project.

    The project_id is automatically fetched from the database based on the user_id.

    Args:
        user_id: User ID - used to fetch the associated project_id from database.

    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): KYC status details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        logger.info("=" * 80)
        logger.info(f"Getting KYC submission status for user_id: {user_id}")
        logger.info("=" * 80)

        # Step 1: Fetch project_id from database based on user_id
        logger.info("Step 1: Fetching project_id from database...")

        with get_session() as session:
            project_repo = ProjectCreationRepository(session=session)
            result = project_repo.get_project_by_user_id(user_id)

            if not result:
                error_msg = f"No project found for user_id: {user_id}"
                logger.error(error_msg)
                logger.error("  Make sure a project has been created for this user first")
                return {
                    "success": False,
                    "error": error_msg
                }

            name, project_id, business_id = result
            logger.info(f"✓ Successfully retrieved project_id: {project_id}")
            logger.info(f"  - Project Name: {name}")
            logger.info(f"  - Business ID: {business_id}")

        # Step 2: Call API with project_id
        logger.info("=" * 80)
        logger.info(f"Step 2: Fetching KYC submission status from API...")
        logger.info(f"  - Project ID: {project_id}")
        logger.info("=" * 80)

        async with get_aisensy_get_client() as client:
            response = await client.get_kyc_submission_status(
                project_id=project_id
            )
            
            if response.get("success"):
                logger.info("=" * 80)
                logger.info(f"✓ Successfully retrieved KYC submission status")
                logger.info(f"  - Project: {project_id}")
                logger.info("=" * 80)
                return KycSubmissionStatusResponse(**response)

            else:
                error_msg = response.get("error", "Unknown error")
                status_code = response.get("status_code", "N/A")
                details = response.get("details", {})

                full_error = f"{error_msg} | Status: {status_code} | Details: {details}"

                logger.error("=" * 80)
                logger.error("API ERROR - Failed to get KYC submission status")
                logger.error("=" * 80)
                logger.error(f"Error: {error_msg}")
                logger.error(f"Status Code: {status_code}")
                logger.error(f"Details: {details}")
                logger.error("=" * 80)

                return {
                    "success": False,
                    "error": full_error
                }

    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

    except Exception as e:
        error_msg = f"Unexpected error fetching KYC submission status: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }