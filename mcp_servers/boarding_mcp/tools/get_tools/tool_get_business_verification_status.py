"""
MCP Tool: Get Business Verification Status

Fetches the business verification status for a specific project.
This version FETCHES business_id and project_id from database based on user_id.
"""
from typing import Dict, Any

from .. import mcp
from ...clients import get_aisensy_get_client
from ...models import BusinessVerificationStatusResponse
from app import logger
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import (
    BusinessCreationRepository,
    ProjectCreationRepository
)


@mcp.tool(
    name="get_business_verification_status",
    description=(
        "Fetches the business verification status for a specific project. "
        "Returns details about the business verification process including "
        "verification state, completion percentage, and any required actions. "
        "Requires user_id - the business_id and project_id are automatically retrieved from the database."
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
async def get_business_verification_status(user_id: str) -> BusinessVerificationStatusResponse:
    """
    Fetch business verification status for a project.

    The business_id and project_id are automatically fetched from the database based on the user_id.

    Args:
        user_id: User ID - used to fetch the associated business_id and project_id from database.

    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Business verification status details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        logger.info("=" * 80)
        logger.info(f"Getting business verification status for user_id: {user_id}")
        logger.info("=" * 80)

        # Step 1: Fetch business_id from database based on user_id
        logger.info("Step 1: Fetching business_id from database...")

        with get_session() as session:
            business_repo = BusinessCreationRepository(session=session)
            ids = business_repo.get_ids_by_user_id(user_id)

            if not ids:
                error_msg = f"No business found for user_id: {user_id}"
                logger.error(error_msg)
                logger.error("  Make sure a business profile has been created for this user first")
                return {
                    "success": False,
                    "error": error_msg
                }

            business_id = ids[0]["business_id"]

            if not business_id:
                error_msg = f"Business ID is empty for user_id: {user_id}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

            logger.info(f"✓ Successfully retrieved business_id: {business_id}")

        # Step 2: Fetch project_id from database based on user_id
        logger.info("Step 2: Fetching project_id from database...")

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

            name, project_id, fetched_business_id = result
            logger.info(f"✓ Successfully retrieved project_id: {project_id}")
            logger.info(f"  - Project Name: {name}")
            logger.info(f"  - Business ID: {fetched_business_id}")

        # Step 3: Call API with project_id
        logger.info("=" * 80)
        logger.info(f"Step 3: Fetching business verification status from API...")
        logger.info(f"  - Project ID: {project_id}")
        logger.info("=" * 80)

        async with get_aisensy_get_client() as client:
            response = await client.get_business_verification_status(
                project_id=project_id
            )

            if response.get("success"):
                logger.info("=" * 80)
                logger.info(f"✓ Successfully retrieved business verification status")
                logger.info(f"  - Project: {project_id}")
                logger.info("=" * 80)
                return BusinessVerificationStatusResponse(**response)

            else:
                error_msg = response.get("error", "Unknown error")
                status_code = response.get("status_code", "N/A")
                details = response.get("details", {})

                full_error = f"{error_msg} | Status: {status_code} | Details: {details}"

                logger.error("=" * 80)
                logger.error("API ERROR - Failed to get business verification status")
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
        error_msg = f"Unexpected error fetching business verification status: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
