"""
MCP Tool: Generate CTWA Ads Manager Dashboard URL

Generates CTWA (Click-to-WhatsApp) Ads Manager Dashboard URL.
"""
from typing import Dict, Any

from ..import mcp
from ...models import CtwaAdsDashboardRequest
from ...clients import get_aisensy_post_client
from app import logger


@mcp.tool(
    name="generate_ctwa_ads_dashboard_url",
    description=(
        "Generates CTWA (Click-to-WhatsApp) Ads Manager Dashboard URL. "
        "Requires business_id, assistant_id, and optionally expires_in. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "ctwa",
        "ads",
        "dashboard",
        "whatsapp",
        "url",
        "generate",
        "post",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Ads Management"
    }
)
async def generate_ctwa_ads_dashboard_url(
    business_id: str,
    assistant_id: str,
    expires_in: int = 150000
) -> Dict[str, Any]:
    """
    Generate CTWA Ads Manager Dashboard URL.
    
    Args:
        business_id: The business ID.
        assistant_id: The assistant ID.
        expires_in: URL expiration time in milliseconds (default: 150000).
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Generated dashboard URL details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = CtwaAdsDashboardRequest(
            business_id=business_id,
            assistant_id=assistant_id,
            expires_in=expires_in
        )
        
        async with get_aisensy_post_client() as client:
            response = await client.generate_ctwa_ads_manager_dashboard_url(
                business_id=request.business_id,
                assistant_id=request.assistant_id,
                expires_in=request.expires_in
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully generated CTWA Ads Dashboard URL for "
                    f"business: {request.business_id}"
                )
            else:
                logger.warning(
                    f"Failed to generate CTWA Ads Dashboard URL: {response.get('error')}"
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
        error_msg = f"Unexpected error generating CTWA Ads Dashboard URL: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }