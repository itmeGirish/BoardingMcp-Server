"""
MCP Tool: Get Payment Configuration by Name

Fetches a specific payment configuration by name from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from ....models import PaymentConfigurationNameRequest
from app import logger


@mcp.tool(
    name="get_payment_configuration_by_name",
    description=(
        "Fetches a specific payment configuration by name from the AiSensy Direct API. "
        "Returns the payment configuration details including provider, redirect URL, "
        "and settings for the given configuration name."
    ),
    tags={
        "payment",
        "configuration",
        "detail",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Payment Management"
    }
)
async def get_payment_configuration_by_name(configuration_name: str) -> Dict[str, Any]:
    """
    Fetch a specific payment configuration by name.
    
    Args:
        configuration_name: The payment configuration name
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Payment configuration details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = PaymentConfigurationNameRequest(configuration_name=configuration_name)
        
        async with get_direct_api_get_client() as client:
            response = await client.get_payment_configuration_by_name(
                configuration_name=request.configuration_name
            )
            
            if response.get("success"):
                logger.info(f"Successfully retrieved payment configuration: {request.configuration_name}")
            else:
                logger.warning(
                    f"Failed to retrieve payment configuration {request.configuration_name}: {response.get('error')}"
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
        error_msg = f"Unexpected error fetching payment configuration: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }