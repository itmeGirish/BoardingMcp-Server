"""
MCP Tool: Request OTP for Verification

Requests OTP for verification during migration.
"""
from typing import Dict, Any

from .. import mcp
from ...models import RequestOtpRequest
from ...clients import get_aisensy_post_client
from app import logger


@mcp.tool(
    name="request_otp_for_verification",
    description=(
        "Requests OTP for verification during migration. "
        "Requires assistant_id and optionally the delivery mode (sms or voice). "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "otp",
        "verification",
        "migration",
        "request",
        "post",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Migration"
    }
)
async def request_otp_for_verification(
    assistant_id: str,
    mode: str = "sms"
) -> Dict[str, Any]:
    """
    Request OTP for verification.
    
    Args:
        assistant_id: The assistant ID.
        mode: OTP delivery mode - "sms" or "voice" (default: "sms").
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): OTP request response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = RequestOtpRequest(
            assistant_id=assistant_id,
            mode=mode
        )
        
        async with get_aisensy_post_client() as client:
            response = await client.request_otp_for_verification(
                assistant_id=request.assistant_id,
                mode=request.mode
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully requested OTP via {request.mode} "
                    f"for assistant: {request.assistant_id}"
                )
            else:
                logger.warning(
                    f"Failed to request OTP: {response.get('error')}"
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
        error_msg = f"Unexpected error requesting OTP: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }