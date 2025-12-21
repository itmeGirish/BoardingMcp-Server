"""
MCP Tool: Generate Embedded FB Catalog URL

Generates an embedded Facebook Catalog connect URL.
"""
from typing import Dict, Any

from ..import mcp
from ...models import BusinessAssistantRequest
from ...clients import get_aisensy_post_client
from app import logger


@mcp.tool(
    name="generate_embedded_fb_catalog_url",
    description=(
        "Generates an embedded Facebook Catalog connect URL. "
        "Requires business_id and assistant_id. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "facebook",
        "catalog",
        "embedded",
        "url",
        "generate",
        "post",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Facebook Integration"
    }
)
async def generate_embedded_fb_catalog_url(
    business_id: str,
    assistant_id: str
) -> Dict[str, Any]:
    """
    Generate an embedded Facebook Catalog connect URL.
    
    Args:
        business_id: The business ID.
        assistant_id: The assistant ID.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Generated catalog connect URL details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = BusinessAssistantRequest(
            business_id=business_id,
            assistant_id=assistant_id
        )
        
        async with get_aisensy_post_client() as client:
            response = await client.generate_embedded_fb_catalog_url(
                business_id=request.business_id,
                assistant_id=request.assistant_id
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully generated FB catalog URL for "
                    f"business: {request.business_id}"
                )
            else:
                logger.warning(
                    f"Failed to generate FB catalog URL: {response.get('error')}"
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
        error_msg = f"Unexpected error generating FB catalog URL: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }