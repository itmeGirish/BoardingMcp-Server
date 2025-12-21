"""
MCP Tool: Verify OTP

Verifies OTP for migration to partner.
"""
from typing import Dict, Any

from ..import mcp
from ...models import VerifyOtpRequest
from ...clients import get_aisensy_post_client
from app import logger


@mcp.tool(
    name="verify_otp",
    description=(
        "Verifies OTP for migration to partner. "
        "Requires assistant_id and the OTP code. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "otp",
        "verification",
        "migration",
        "verify",
        "post",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Migration"
    }
)
async def verify_otp(
    assistant_id: str,
    otp: str
) -> Dict[str, Any]:
    """
    Verify OTP for migration.
    
    Args:
        assistant_id: The assistant ID.
        otp: The OTP code to verify.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): OTP verification response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = VerifyOtpRequest(
            assistant_id=assistant_id,
            otp=otp
        )
        
        async with get_aisensy_post_client() as client:
            response = await client.verify_otp(
                assistant_id=request.assistant_id,
                otp=request.otp
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully verified OTP for assistant: {request.assistant_id}"
                )
            else:
                logger.warning(
                    f"Failed to verify OTP: {response.get('error')}"
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
        error_msg = f"Unexpected error verifying OTP: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }