"""
MCP Tool: Get Partner Details

Fetches the partner account details from AiSensy.
"""
from typing import Dict, Any

from ..import mcp
from ...clients import get_aisensy_get_client
from app import logger
from ...models import PartnerDetails


@mcp.tool(
    name="get_partner_details",
    description=(
        "Fetches the partner account details from AiSensy. "
        "Returns comprehensive information about the partner including "
        "account status, configuration, and associated metadata. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "partner",
        "account",
        "details",
        "get",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Partner Management"
    }
)
async def get_partner_details() -> PartnerDetails:
    """
    Fetch partner account details.
    
    Returns:
        PartnerDetails object containing partner details if successful
        or error information if unsuccessful.
        - success (bool): Whether the operation was successful
        - data (dict): Partner details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_aisensy_get_client() as client:
            response = await client.get_partner_details()
            
            if response.get("success"):
                logger.info("Successfully retrieved partner details")
                return PartnerDetails(**response["data"])
            else:
                logger.warning(
                    f"Failed to retrieve partner details: {response.get('error')}"
                )
                error_msg = f"Failed to retrieve partner details: {response.get('error')}"
                logger.warning(error_msg)
                raise ValueError(error_msg)       
            
       
        
    except Exception as e:
        error_msg = f"Unexpected error fetching partner details: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }