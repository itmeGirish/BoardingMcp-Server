"""
MCP Tool: Update QR Code

Updates a QR code via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_patch_client
from ....models import UpdateQrCodeRequest
from app import logger


@mcp.tool(
    name="update_qr_code",
    description=(
        "Updates a QR code via the AiSensy Direct API. "
        "Changes the prefilled message for the specified QR code."
    ),
    tags={
        "qr",
        "code",
        "update",
        "patch",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "QR Code Management"
    }
)
async def update_qr_code(
    qr_code_id: str,
    prefilled_message: str
) -> Dict[str, Any]:
    """
    Update a QR code.
    
    Args:
        qr_code_id: The QR code ID to update
        prefilled_message: The new prefilled message
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = UpdateQrCodeRequest(
            qr_code_id=qr_code_id,
            prefilled_message=prefilled_message
        )
        
        async with get_direct_api_patch_client() as client:
            response = await client.update_qr_code(
                qr_code_id=request.qr_code_id,
                prefilled_message=request.prefilled_message
            )
            
            if response.get("success"):
                logger.info(f"Successfully updated QR code: {request.qr_code_id}")
            else:
                logger.warning(
                    f"Failed to update QR code {request.qr_code_id}: {response.get('error')}"
                )
            
            return response
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.warning(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error updating QR code: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }