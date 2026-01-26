"""
MCP Tool: Regenerate JWT Bearer Token

Regenerates JWT Bearer Token to Access Direct-APIs.
This version FETCHES email, password, and project_id from database based on user_id.
"""
import base64
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import RegenerateJwtBearerTokenRequest
from app import logger
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import (
    BusinessCreationRepository,
    ProjectCreationRepository
)


@mcp.tool(
    name="regenerate_jwt_bearer_token",
    description=(
        "Regenerates JWT Bearer Token to Access Direct-APIs. "
        "Returns a new authentication token for API access. "
        "Requires user_id - email, password, and project_id are automatically retrieved from the database."
    ),
    tags={
        "auth",
        "token",
        "jwt",
        "regenerate",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Authentication"
    },
)
async def regenerate_jwt_bearer_token(user_id: str, direct_api: bool = True) -> Dict[str, Any]:
    """
    Regenerate JWT Bearer Token.

    The email, password, and project_id are automatically fetched from the database
    based on the user_id, then converted to a base64 token.

    Args:
        user_id: User ID - used to fetch email, password, and project_id from database
        direct_api: Whether to use direct API (default: True)

    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): New token details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        logger.info("=" * 80)
        logger.info(f"Regenerating JWT bearer token for user_id: {user_id}")
        logger.info("=" * 80)

        # Step 1: Fetch email and password from BusinessCreation table
        logger.info("Step 1: Fetching email and password from database...")

        with get_session() as session:
            business_repo = BusinessCreationRepository(session=session)
            credentials = business_repo.get_credentials_by_user_id(user_id)

            if not credentials:
                error_msg = f"No business credentials found for user_id: {user_id}"
                logger.error(error_msg)
                logger.error("  Make sure a business profile has been created for this user first")
                return {
                    "success": False,
                    "error": error_msg
                }

            email = credentials.get("email")
            password = credentials.get("password")

            if not email:
                error_msg = f"Email is empty for user_id: {user_id}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

            if not password:
                error_msg = f"Password is empty for user_id: {user_id}. Password must be saved during business profile creation."
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

            logger.info(f"✓ Successfully retrieved credentials for email: {email}")

        # Step 2: Fetch project_id from ProjectCreation table
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

            name, project_id, business_id = result
            logger.info(f"✓ Successfully retrieved project_id: {project_id}")
            logger.info(f"  - Project Name: {name}")
            logger.info(f"  - Business ID: {business_id}")

        # Step 3: Create base64 token from <email>:<password>:<projectId>
        logger.info("Step 3: Creating base64 token...")
        token_string = f"{email}:{password}:{project_id}"
        token = base64.b64encode(token_string.encode()).decode()
        logger.info("✓ Successfully created base64 token")
        logger.info("  - Token format: <email>:<password>:<projectId>")

        # Step 4: Call API with token
        logger.info("=" * 80)
        logger.info("Step 4: Regenerating JWT bearer token via API...")
        logger.info("=" * 80)

        request = RegenerateJwtBearerTokenRequest(direct_api=direct_api)

        async with get_direct_api_post_client() as client:
            response = await client.regenerate_jwt_bearer_token(
                token=token,
                direct_api=request.direct_api
            )

            if response.get("success"):
                logger.info("=" * 80)
                logger.info("✓ Successfully regenerated JWT bearer token")
                logger.info(f"  - User: {email}")
                logger.info(f"  - Project: {project_id}")
                logger.info("=" * 80)
            else:
                error_msg = response.get("error", "Unknown error")
                status_code = response.get("status_code", "N/A")
                details = response.get("details", {})

                logger.error("=" * 80)
                logger.error("API ERROR - Failed to regenerate JWT bearer token")
                logger.error("=" * 80)
                logger.error(f"Error: {error_msg}")
                logger.error(f"Status Code: {status_code}")
                logger.error(f"Details: {details}")
                logger.error("=" * 80)

            return response

    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

    except Exception as e:
        error_msg = f"Unexpected error regenerating JWT bearer token: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
