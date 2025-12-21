"""
MCP Tool: Update Business Details

Updates business details in the AiSensy API.
"""
from typing import Dict, Any, Optional

from .. import mcp
from ...models import UpdateBusinessDetailsRequest
from ...clients import get_aisensy_patch_client
from app import logger


@mcp.tool(
    name="update_business_details",
    description=(
        "Updates business details in the AiSensy API. "
        "At least one field (display_name, company, or contact) must be provided. "
        "Only provided fields will be updated. "
        "Requires PARTNER_ID and BUSINESS_ID to be configured in settings."
    ),
    tags={
        "business",
        "update",
        "patch",
        "details",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Business Management"
    }
)
async def update_business_details(
    display_name: Optional[str] = None,
    company: Optional[str] = None,
    contact: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update business details.
    
    Args:
        display_name: Optional new display name for the business.
        company: Optional new company name.
        contact: Optional new contact number.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Updated business details if successful
        - error (str): Error message if unsuccessful
    
    Note:
        At least one field must be provided for update.
    """
    try:
        # Validate input using Pydantic model
        request = UpdateBusinessDetailsRequest(
            display_name=display_name,
            company=company,
            contact=contact
        )
        
        # Check if at least one field is provided
        if not request.has_updates():
            error_msg = "At least one field (display_name, company, or contact) must be provided"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
        async with get_aisensy_patch_client() as client:
            response = await client.update_business_details(
                display_name=request.display_name,
                company=request.company,
                contact=request.contact
            )
            
            if response.get("success"):
                updated_fields = [
                    f for f in ["display_name", "company", "contact"]
                    if getattr(request, f) is not None
                ]
                logger.info(
                    f"Successfully updated business details. "
                    f"Updated fields: {', '.join(updated_fields)}"
                )
            else:
                logger.warning(
                    f"Failed to update business details: {response.get('error')}"
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
        error_msg = f"Unexpected error updating business details: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }