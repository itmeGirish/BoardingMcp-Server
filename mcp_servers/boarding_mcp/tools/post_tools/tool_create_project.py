"""
MCP Tool: Create Project

Creates a new project in the AiSensy API.
This version FETCHES business_id from database based on user_id.
"""
import traceback
from typing import Dict, Any

from . .import mcp
from ...models import CreateProjectRequest, ProjectAPIResponse, ProjectResponse
from ...clients import get_aisensy_post_client

from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import (
    BusinessCreationRepository,
    ProjectCreationRepository
)
from app import logger


@mcp.tool(
    name="create_project",
    description=(
        "Creates a new project in the AiSensy API. "
        "Requires a project name and user_id. "
        "The business_id is automatically retrieved from the database based on user_id."
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
async def create_project(name: str, user_id: str) -> ProjectAPIResponse:
    """
    Create a new project.
    
    The business_id is automatically fetched from the database based on the user_id.

    Args:
        name: Name for the project.
        user_id: User ID - used to fetch the associated business_id.

    Returns:
        ProjectAPIResponse containing:
        - success (bool): Whether the operation was successful
        - data (ProjectResponse): Created project details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = CreateProjectRequest(name=name, user_id=user_id)

        logger.info("=" * 80)
        logger.info(f"Creating project '{name}' for user_id: {user_id}")
        logger.info("=" * 80)

        # Get business_id from database based on user_id
        logger.info("Step 1: Fetching business_id from database...")
        
        with get_session() as session:
            business_repo = BusinessCreationRepository(session=session)
            ids = business_repo.get_ids_by_user_id(user_id)
        
            if not ids:
                error_msg = f"No business found for user_id: {user_id}"
                logger.error(error_msg)
                logger.error("  Make sure a business profile has been created for this user first")
                return ProjectAPIResponse(
                    success=False,
                    error=error_msg
                )
        
            business_id = ids[0]["business_id"]
        
            if not business_id:
                error_msg = f"Business ID is empty for user_id: {user_id}"
                logger.error(error_msg)
                return ProjectAPIResponse(
                    success=False,
                    error=error_msg
                )
        
            logger.info(f"✓ Successfully retrieved business_id: {business_id}")
            logger.info(f"  - User ID: {user_id}")
            logger.info(f"  - Business ID: {business_id}")

        # Create project via API
        logger.info("=" * 80)
        logger.info("Step 2: Creating project via AiSensy API...")
        logger.info("=" * 80)
        
        async with get_aisensy_post_client() as client:
            response = await client.create_project(name=request.name, business_id=business_id)

            if not response.get("success"):
                error_msg = response.get("error", "Unknown error")
                status_code = response.get("status_code", "N/A")
                details = response.get("details", {})

                full_error = f"{error_msg} | Status: {status_code} | Details: {details}"
                logger.warning(f"Failed to create project: {full_error}")
                return ProjectAPIResponse(
                    success=False,
                    error=full_error
                )

            logger.info(f"✓ Successfully created project via API: {request.name}")
            logger.info(f"  - Project ID: {response['data'].get('id', 'N/A')}")

            # Parse the API response data into ProjectResponse
            project_data = ProjectResponse(**response["data"])

            # Save project to database
            logger.info("=" * 80)
            logger.info("Step 3: Saving project to database...")
            logger.info("=" * 80)
            
            db_saved = False
            db_error_msg = None
            
            try:
                with get_session() as db_session:
                    project_repo = ProjectCreationRepository(session=db_session)

                    # Convert Pydantic model to dict
                    project_dict = project_data.model_dump()

                    # Add user_id and business_id (not in API response)
                    project_dict["user_id"] = user_id
                    project_dict["business_id"] = business_id

                    logger.info(f"Project data keys: {list(project_dict.keys())}")

                    # Handle nested wa_business_profile model
                    if project_dict.get("wa_business_profile"):
                        logger.info("Converting wa_business_profile to dict...")
                        project_dict["wa_business_profile"] = dict(project_dict["wa_business_profile"])

                    # Remove any keys that don't match repository create params
                    allowed_keys = {
                        "id", "user_id", "business_id", "name", "partner_id", "type",
                        "status", "sandbox", "active_plan", "plan_activated_on",
                        "plan_renewal_on", "scheduled_subscription_changes",
                        "subscription_started_on", "subscription_status", "mau_quota",
                        "mau_usage", "credit", "billing_currency", "timezone",
                        "wa_number", "wa_messaging_tier", "wa_display_name",
                        "wa_display_name_status", "wa_quality_rating", "wa_about",
                        "wa_display_image", "wa_business_profile", "waba_app_status",
                        "fb_business_manager_status", "is_whatsapp_verified",
                        "applied_for_waba", "created_at", "updated_at"
                    }
                    
                    # Filter to only allowed keys
                    filtered_dict = {k: v for k, v in project_dict.items() if k in allowed_keys}
                    logger.info(f"Filtered project data keys: {list(filtered_dict.keys())}")

                    # Create project in database
                    logger.info("Calling project_repo.create()...")
                    saved_project = project_repo.create(**filtered_dict)

                    if saved_project:
                        db_saved = True
                        logger.info(f"✓ Successfully saved project to database")
                        logger.info(f"  - Project ID: {saved_project.id}")
                        logger.info(f"  - Project Name: {saved_project.name if hasattr(saved_project, 'name') else 'N/A'}")
                    else:
                        logger.warning("project_repo.create() returned None/False")
                        
            except Exception as db_error:
                db_error_msg = str(db_error)
                logger.error("=" * 80)
                logger.error("DATABASE SAVE FAILED (NON-FATAL)")
                logger.error("=" * 80)
                logger.error(f"Error Type: {type(db_error).__name__}")
                logger.error(f"Error Message: {str(db_error)}")
                logger.error("Full Traceback:")
                logger.error(traceback.format_exc())
                logger.error("=" * 80)
                
                # Log the data that was being saved
                logger.error("Data that failed to save:")
                logger.error(f"  - Project Name: {request.name}")
                logger.error(f"  - User ID: {user_id}")
                logger.error(f"  - Business ID: {business_id}")
                logger.error(f"  - Project ID: {project_data.id if hasattr(project_data, 'id') else 'N/A'}")
                
                # Continue even if database save fails - API creation succeeded
                logger.warning("Continuing despite database save failure - API creation was successful")
            
            finally:
                logger.info("=" * 80)
                logger.info(f"DATABASE SAVE OPERATION COMPLETE - Success: {db_saved}")
                logger.info("=" * 80)

            logger.info(f"Returning success response to client (DB saved: {db_saved})")
            return ProjectAPIResponse(
                success=True,
                data=project_data
            )
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return ProjectAPIResponse(
            success=False,
            error=error_msg
        )
        
    except Exception as e:
        error_msg = f"Unexpected error creating project: {str(e)}"
        logger.exception(error_msg)
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        return ProjectAPIResponse(
            success=False,
            error=error_msg
        )