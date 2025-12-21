"""
MCP Tool: Generate Embedded Signup URL

Generates an embedded signup URL for WhatsApp Business API (WABA).
"""
from typing import Dict, Any, Optional

from .. import mcp
from ...models import EmbeddedSignupUrlRequest
from ...clients import get_aisensy_post_client
from app import logger


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
    business_id: str,
    assistant_id: str,
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
        business_id: The business ID.
        assistant_id: The assistant ID.
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
        - success (bool): Whether the operation was successful
        - data (dict): Generated signup URL details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = EmbeddedSignupUrlRequest(
            business_id=business_id,
            assistant_id=assistant_id,
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
        
        async with get_aisensy_post_client() as client:
            response = await client.generate_embedded_signup_url(
                business_id=request.business_id,
                assistant_id=request.assistant_id,
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
                logger.info("Successfully generated embedded signup URL")
            else:
                logger.warning(
                    f"Failed to generate embedded signup URL: {response.get('error')}"
                )
            
            return response
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
        
    except Exception as e:
        error_msg = f"Unexpected error generating embedded signup URL: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }