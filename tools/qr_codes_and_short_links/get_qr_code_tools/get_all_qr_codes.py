"""
MCP Tool: Get QR Codes

Fetches all QR codes from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from app import logger


@mcp.tool(
    name="get_qr_codes",
    description=(
        "Fetches all QR codes from the AiSensy Direct API. "
        "Returns a list of all QR codes including their prefilled messages, "
        "short links, and image data."
    ),
    tags={
        "qr",
        "codes",
        "list",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "QR Code Management"
    }
)
async def get_qr_codes() -> Dict[str, Any]:
    """
    Fetch all QR codes.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (list): List of QR codes if successful
        - error (str): Error message if unsuccessful
    """
    try:
        async with get_direct_api_get_client() as client:
            response = await client.get_qr_codes()
            
            if response.get("success"):
                data = response.get("data", [])
                count = len(data) if isinstance(data, list) else "unknown"
                logger.info(f"Successfully retrieved {count} QR codes")
            else:
                logger.warning(
                    f"Failed to retrieve QR codes: {response.get('error')}"
                )
            
            return response
        
    except Exception as e:
        error_msg = f"Unexpected error fetching QR codes: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }