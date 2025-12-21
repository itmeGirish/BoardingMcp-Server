"""
MCP Tool: Create Business Profile

Creates a new business profile in the AiSensy API.
"""
from typing import Dict, Any

from ..import mcp
from ...models import CreateBusinessProfileRequest, BusinessCreationResponse
from ...clients import get_aisensy_post_client
from app import logger


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
    password: str
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
            password=password
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
        return BusinessCreationResponse(
            success=False,
            error=error_msg
        )
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(error_msg)
        return BusinessCreationResponse(
            success=False,
            error=error_msg
        )