"""
MCP Tool: Create Business Profile

Creates a new business profile in the AiSensy API.
"""
import traceback
from typing import Dict, Any

from ..import mcp
from ...models import CreateBusinessProfileRequest, BusinessCreationResponse
from ...clients import get_aisensy_post_client
from app import logger
from app import BusinessCreationRepository, get_session


@mcp.tool(
    name="create_business_profile",
    description=(
        "Creates a new business profile in the AiSensy API. "
        "Requires display name, email, company details, timezone, currency, "
        "company size, and password. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "business",
        "profile",
        "create",
        "post",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Business Management"
    }
)
async def create_business_profile(
    display_name: str,
    email: str,
    company: str,
    contact: str,
    timezone: str,
    currency: str,
    company_size: str,
    password: str,
    user_id: str,
    onboarding_id: str,
) -> BusinessCreationResponse:
    """
    Create a new business profile.
    """
    try:
        request = CreateBusinessProfileRequest(
            display_name=display_name,
            email=email,
            company=company,
            contact=contact,
            timezone=timezone,
            currency=currency,
            company_size=company_size,
            password=password,
            user_id=user_id,
            onboarding_id=onboarding_id
        )
        
        async with get_aisensy_post_client() as client:
            response = await client.create_business_profile(
                display_name=request.display_name,
                email=request.email,
                company=request.company,
                contact=request.contact,
                timezone=request.timezone,
                currency=request.currency,
                company_size=request.company_size,
                password=request.password
            )
            
            if response.get("success"):
                logger.info("Successfully created business profile")

                # Save to database
                logger.info("=" * 80)
                logger.info("STARTING DATABASE SAVE OPERATION")
                logger.info("=" * 80)
                
                db_saved = False
                db_error_msg = None
                
                try:
                    logger.info(f"Attempting to save business profile to database")
                    logger.info(f"User ID: {request.user_id}")
                    logger.info(f"Onboarding ID: {request.onboarding_id}")
                    logger.info(f"Response data keys: {list(response['data'].keys())}")
                    
                    # Get database session
                    logger.info("Step 1: Getting database session...")
                    session = get_session()
                    logger.info(f"Step 1 Complete: Got session object: {type(session)}")
                    
                    # Use session context manager
                    logger.info("Step 2: Entering session context manager...")
                    with session as sess:
                        logger.info(f"Step 2 Complete: Inside session context, session active: {hasattr(sess, 'is_active')}")
                        
                        # Create repository
                        logger.info("Step 3: Creating BusinessCreationRepository...")
                        business_repo = BusinessCreationRepository(session=sess)
                        logger.info(f"Step 3 Complete: Repository created: {type(business_repo)}")
                        
                        # Prepare data
                        logger.info("Step 4: Preparing data for creation...")
                        business_data = {
                            "id": response["data"]["id"],
                            "user_id": request.user_id,
                            "onboarding_id": request.onboarding_id,
                            "display_name": response["data"]["display_name"],
                            "project_ids": response["data"]["project_ids"],
                            "user_name": response["data"]["user_name"],
                            "business_id": response["data"]["business_id"],
                            "email": response["data"]["email"],
                            "company": response["data"]["company"],
                            "contact": response["data"]["contact"],
                            "currency": response["data"]["currency"],
                            "timezone": response["data"]["timezone"]
                        }
                        logger.info(f"Step 4 Complete: Data prepared with keys: {list(business_data.keys())}")
                        
                        # Call create method
                        logger.info("Step 5: Calling repository.create()...")
                        business_repo.create(
                            id=response["data"]["id"],
                            user_id=request.user_id,
                            onboarding_id=request.onboarding_id,
                            display_name=response["data"]["display_name"],
                            project_ids=response["data"]["project_ids"],
                            user_name=response["data"]["user_name"],
                            business_id=response["data"]["business_id"],
                            email=response["data"]["email"],
                            company=response["data"]["company"],
                            contact=response["data"]["contact"],
                            currency=response["data"]["currency"],
                            timezone=response["data"]["timezone"]
                        )
                        logger.info("Step 5 Complete: repository.create() executed successfully")
                        
                        db_saved = True
                        logger.info("✓ Successfully saved business profile to database")
                        
                except Exception as db_error:
                    db_error_msg = str(db_error)
                    logger.error("=" * 80)
                    logger.error("DATABASE SAVE FAILED")
                    logger.error("=" * 80)
                    logger.error(f"Error Type: {type(db_error).__name__}")
                    logger.error(f"Error Message: {str(db_error)}")
                    logger.error(f"Error Args: {db_error.args}")
                    logger.error("Full Traceback:")
                    logger.error(traceback.format_exc())
                    logger.error("=" * 80)
                    
                    # Log the data that was being saved for debugging
                    logger.error("Data that failed to save:")
                    logger.error(f"  - User ID: {request.user_id}")
                    logger.error(f"  - Onboarding ID: {request.onboarding_id}")
                    logger.error(f"  - Business ID: {response['data'].get('business_id', 'N/A')}")
                    logger.error(f"  - Email: {response['data'].get('email', 'N/A')}")
                    
                    # Continue even if database save fails - API creation succeeded
                    logger.warning("Continuing despite database save failure - API creation was successful")
                
                finally:
                    logger.info("=" * 80)
                    logger.info(f"DATABASE SAVE OPERATION COMPLETE - Success: {db_saved}")
                    logger.info("=" * 80)

                logger.info(f"Returning success response to client (DB saved: {db_saved})")
                
                return BusinessCreationResponse(
                    success=True,
                    data=response["data"]
                )
            else:
                error_msg = response.get("error", "Unknown error")
                status_code = response.get("status_code", "N/A")
                details = response.get("details", {})
                
                full_error = f"{error_msg} | Status: {status_code} | Details: {details}"
                logger.warning(f"Failed to create business profile: {full_error}")
                
                return BusinessCreationResponse(
                    success=False,
                    error=full_error
                )

    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return BusinessCreationResponse(
            success=False,
            error=error_msg
        )
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(error_msg)
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        return BusinessCreationResponse(
            success=False,
            error=error_msg
        )