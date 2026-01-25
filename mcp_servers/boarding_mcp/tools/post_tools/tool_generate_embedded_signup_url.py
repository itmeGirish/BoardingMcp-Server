"""
MCP Tool: Generate Embedded Signup URL

Generates an embedded signup URL for WhatsApp Business API (WABA).
"""
from typing import Dict, Any, Optional
from .. import mcp
from ...models import EmbeddedSignupUrlRequest
from ...clients import get_aisensy_post_client
from app import logger
from app import get_session
from app import ProjectCreationRepository



@mcp.tool(
    name="generate_embedded_signup_url",
    description=(
        "Generates an embedded signup URL for WhatsApp Business API (WABA). "
        "Requires business details including name, email, phone, address, "
        "timezone, display name, and category. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "waba",
        "signup",
        "whatsapp",
        "embedded",
        "url",
        "post",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "WABA Integration"
    }
)
async def generate_embedded_signup_url(
    user_id: str,
    business_name: str,
    business_email: str,
    phone_code: int,
    phone_number: str,
    website: str,
    street_address: str,
    city: str,
    state: str,
    zip_postal: str,
    country: str,
    timezone: str,
    display_name: str,
    category: str,
    description: Optional[str] = ""
) -> Dict[str, Any]:
    """
    Generate an embedded signup URL for WABA.
    
    Args:
        user_id: The user ID to lookup project details.
        business_name: Name of the business.
        business_email: Email of the business.
        phone_code: Phone country code (e.g., 1 for US, 91 for India).
        phone_number: Phone number.
        website: Business website URL.
        street_address: Street address.
        city: City name.
        state: State/Province code.
        zip_postal: ZIP/Postal code.
        country: Country code (e.g., "US", "IN").
        timezone: Timezone (e.g., "UTC-08:00").
        display_name: Display name for the phone.
        category: Business category (e.g., "ENTERTAIN").
        description: Optional description.
    
    Returns:
        Dict containing:
        - embeddedSignupURL (str): The generated signup URL
        - error (str): Error message if unsuccessful
    """
    try:
        logger.info("=" * 80)
        logger.info(f"Generating embedded signup URL for user_id: {user_id}")
        logger.info(f"  - Business: {business_name}")
        logger.info(f"  - Email: {business_email}")
        logger.info("=" * 80)

        # Step 1: Fetch project details from database
        logger.info("Step 1: Fetching project details from database...")
        with get_session() as session:
            project_repo = ProjectCreationRepository(session=session)
            result = project_repo.get_project_by_user_id(user_id)

            if not result:
                error_msg = f"No project found for user_id: {user_id}"
                logger.error(error_msg)
                logger.error("  Make sure a project has been created for this user first")
                return {"error": error_msg}

            name, project_id, business_id = result
            logger.info(f"✓ Successfully retrieved project details")
            logger.info(f"  - Project Name: {name}")
            logger.info(f"  - Project ID: {project_id}")
            logger.info(f"  - Business ID: {business_id}")

        # Step 2: Validate input
        logger.info("=" * 80)
        logger.info("Step 2: Validating input parameters...")
        logger.info("=" * 80)
        request = EmbeddedSignupUrlRequest(
            business_id=business_id,
            assistant_id=project_id,
            business_name=business_name,
            business_email=business_email,
            phone_code=phone_code,
            phone_number=phone_number,
            website=website,
            street_address=street_address,
            city=city,
            state=state,
            zip_postal=zip_postal,
            country=country,
            timezone=timezone,
            display_name=display_name,
            category=category,
            description=description
        )
        logger.info("✓ Input validation passed")

        # Step 3: Generate signup URL via API
        logger.info("=" * 80)
        logger.info("Step 3: Calling AiSensy API to generate embedded signup URL...")
        logger.info("=" * 80)
        async with get_aisensy_post_client() as client:
            response = await client.generate_embedded_signup_url(
                business_id=business_id,
                assistant_id=project_id,
                business_name=request.business_name,
                business_email=request.business_email,
                phone_code=request.phone_code,
                phone_number=request.phone_number,
                website=request.website,
                street_address=request.street_address,
                city=request.city,
                state=request.state,
                zip_postal=request.zip_postal,
                country=request.country,
                timezone=request.timezone,
                display_name=request.display_name,
                category=request.category,
                description=request.description
            )

            if response.get("success"):
                signup_url = response["data"]["embeddedSignupURL"]
                logger.info("=" * 80)
                logger.info("✓ Successfully generated embedded signup URL")
                logger.info(f"  - URL: {signup_url[:80]}..." if len(signup_url) > 80 else f"  - URL: {signup_url}")
                logger.info("=" * 80)
                return {"embeddedSignupURL": signup_url}
            else:
                error_msg = response.get("error", "Unknown error")
                status_code = response.get("status_code", "N/A")
                details = response.get("details", {})

                logger.error("=" * 80)
                logger.error("API ERROR - Failed to generate embedded signup URL")
                logger.error("=" * 80)
                logger.error(f"Error: {error_msg}")
                logger.error(f"Status Code: {status_code}")
                logger.error(f"Details: {details}")
                logger.error("=" * 80)

                full_error = f"{error_msg} | Status: {status_code} | Details: {details}"
                return {"error": full_error}
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
        
    except Exception as e:
        error_msg = f"Unexpected error generating embedded signup URL: {str(e)}"
        logger.exception(error_msg)
        return {"error": error_msg}