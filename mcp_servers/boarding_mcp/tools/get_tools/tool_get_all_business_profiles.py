"""
MCP Tool: Get All Business Profiles

Fetches all business profiles associated with the partner.
"""
from typing import Dict, Any

from .. import mcp
from ...clients import get_aisensy_get_client
from ...models import AllBusinessProfilesResponse
from app import logger


@mcp.tool(
    name="get_all_business_profiles",
    description=(
        "Fetches all business profiles for the configured partner. "
        "Returns a list of all businesses associated with the partner account. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "business",
        "profiles",
        "list",
        "get",
        "partner",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Business Management"
    }
)
async def get_all_business_profiles() -> AllBusinessProfilesResponse:
    """
    Fetch all business profiles for the partner.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (list): List of business profiles if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_aisensy_get_client() as client:
            response = await client.get_all_business_profiles()
            
            if response.get("success"):
                data = response.get("data", [])
                count = len(data) if isinstance(data, list) else "unknown"
                logger.info(f"Successfully retrieved {count} business profiles")
                return AllBusinessProfilesResponse(profiles=response["data"])
            else:
                error_msg = response.get("error", "Unknown error")
                status_code = response.get("status_code", "N/A")
                details = response.get("details", {})
                
                full_error = f"{error_msg} | Status: {status_code} | Details: {details}"
                logger.warning(full_error)
                return full_error

    except Exception as e:
        error_msg = f"Unexpected error fetching business profiles: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }