"""
MCP Tool: Get Business Profile by ID

Fetches the business profile details for the configured business ID.
"""
from .. import mcp
from ...clients import get_aisensy_get_client
from ...models import BusinessProfile
from app import logger


@mcp.tool(
    name="get_business_profile_by_id",
    description=(
        "Fetches the business profile details for the configured business ID. "
        "Returns business information including name, status, and configuration. "
        "Requires PARTNER_ID and BUSINESS_ID to be configured in settings."
    ),
    tags={
        "business",
        "profile",
        "get",
        "business-profile",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Business Management"
    }
)
async def get_business_profile_by_id() -> BusinessProfile:
    """
    Fetch the business profile by configured business ID.
    
    Returns:
        BusinessProfile: The business profile details.
        
    Raises:
        ValueError: If the API returns an error response.
        Exception: For unexpected errors.
    """
    try:
        async with get_aisensy_get_client() as client:
            response = await client.get_business_profile_by_id()
            
            if response.get("success"):
                logger.info("Successfully retrieved business profile by ID")
                return BusinessProfile(**response["data"])
            else:
                error_msg = f"Failed to retrieve business profile: {response.get('error')}"
                logger.warning(error_msg)
                raise ValueError(error_msg)

    except ValueError:
        raise  # Re-raise ValueError as-is
    except Exception as e:
        error_msg = f"Unexpected error fetching business profile: {str(e)}"
        logger.exception(error_msg)
        raise RuntimeError(error_msg)