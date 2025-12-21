"""
MCP Tool: Submit WABA App ID

Submits WABA App ID (Facebook Access Token) to the AiSensy API.
"""
from typing import Dict, Any

from .. import mcp
from ...models import SubmitWabaAppIdRequest
from ...clients import get_aisensy_post_client
from app import logger


@mcp.tool(
    name="submit_waba_app_id",
    description=(
        "Submits WABA App ID (Facebook Access Token) to the AiSensy API. "
        "Requires assistant_id and waba_app_id. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "waba",
        "facebook",
        "access-token",
        "submit",
        "post",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "WABA Integration"
    }
)
async def submit_waba_app_id(
    assistant_id: str,
    waba_app_id: str
) -> Dict[str, Any]:
    """
    Submit WABA App ID (Facebook Access Token).
    
    Args:
        assistant_id: The assistant ID.
        waba_app_id: The WABA App ID.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = SubmitWabaAppIdRequest(
            assistant_id=assistant_id,
            waba_app_id=waba_app_id
        )
        
        async with get_aisensy_post_client() as client:
            response = await client.submit_waba_app_id(
                assistant_id=request.assistant_id,
                waba_app_id=request.waba_app_id
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully submitted WABA App ID for assistant: {request.assistant_id}"
                )
            else:
                logger.warning(
                    f"Failed to submit WABA App ID: {response.get('error')}"
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
        error_msg = f"Unexpected error submitting WABA App ID: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }