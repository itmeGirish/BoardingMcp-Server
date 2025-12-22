"""
MCP Tool: Create Project

Creates a new project in the AiSensy API.
"""
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
        "Requires a project name. "
        "Requires PARTNER_ID and BUSINESS_ID to be configured in settings."
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
    
    Args:
        name: Name for the project.
        user_id: User ID to retrieve the associated business_id.
    
    Returns:
        ProjectAPIResponse containing:
        - success (bool): Whether the operation was successful
        - data (ProjectResponse): Created project details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = CreateProjectRequest(name=name, user_id=user_id)

        # Get business_id from database
        with get_session() as session:
            business_repo = BusinessCreationRepository(session=session)
            ids = business_repo.get_ids_by_user_id(user_id)

            if not ids:
                error_msg = f"No business found for user_id: {user_id}"
                logger.warning(error_msg)
                return ProjectAPIResponse(
                    success=False,
                    error=error_msg
                )

            business_id = ids[0]["business_id"]
            
            if not business_id:
                error_msg = f"Business ID is empty for user_id: {user_id}"
                logger.warning(error_msg)
                return ProjectAPIResponse(
                    success=False,
                    error=error_msg
                )
            
            logger.info(f"Successfully retrieved the business_id for {user_id}")

            # Create project via API
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
                
                logger.info(f"Successfully created project via API: {request.name}")
                
                # Parse the API response data into ProjectResponse
                project_data = ProjectResponse(**response["data"])
                
                # Save project to database using same session
                project_repo = ProjectCreationRepository(session=session)
                
                # Convert Pydantic model to dict
                project_dict = project_data.model_dump()
                
                # Add user_id and business_id (not in API response)
                project_dict["user_id"] = user_id
                project_dict["business_id"] = business_id
                
                # Handle nested wa_business_profile model
                if project_dict.get("wa_business_profile"):
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
                project_dict = {k: v for k, v in project_dict.items() if k in allowed_keys}
                
                saved_project = project_repo.create(**project_dict)
                
                if saved_project:
                    logger.info(f"Successfully saved project to database: {saved_project.id}")
                else:
                    logger.warning(f"Failed to save project to database: {project_data.id}")
                
                return ProjectAPIResponse(
                    success=True,
                    data=project_data
                )
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        return ProjectAPIResponse(
            success=False,
            error=error_msg
        )
        
    except Exception as e:
        error_msg = f"Unexpected error creating project: {str(e)}"
        logger.exception(error_msg)
        return ProjectAPIResponse(
            success=False,
            error=error_msg
        )