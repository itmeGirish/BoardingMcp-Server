"""
MCP Tool: Create Payment Configuration

Creates a payment configuration via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import CreatePaymentConfigurationRequest
from app import logger


@mcp.tool(
    name="create_payment_configuration",
    description=(
        "Creates a payment configuration via the AiSensy Direct API. "
        "Sets up payment provider integration with redirect URL."
    ),
    tags={
        "payment",
        "configuration",
        "create",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Payment Management"
    }
)
async def create_payment_configuration(
    configuration_name: str,
    purpose_code: str,
    merchant_category_code: str,
    provider_name: str,
    redirect_url: str
) -> Dict[str, Any]:
    """
    Create a payment configuration.
    
    Args:
        configuration_name: Name of the payment configuration
        purpose_code: Purpose code (e.g., "00")
        merchant_category_code: Merchant category code (e.g., "0000")
        provider_name: Payment provider name (e.g., "razorpay")
        redirect_url: Redirect URL after payment
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Created configuration details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = CreatePaymentConfigurationRequest(
            configuration_name=configuration_name,
            purpose_code=purpose_code,
            merchant_category_code=merchant_category_code,
            provider_name=provider_name,
            redirect_url=redirect_url
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.create_payment_configuration(
                configuration_name=request.configuration_name,
                purpose_code=request.purpose_code,
                merchant_category_code=request.merchant_category_code,
                provider_name=request.provider_name,
                redirect_url=request.redirect_url
            )
            
            if response.get("success"):
                logger.info(f"Successfully created payment configuration: {request.configuration_name}")
            else:
                logger.warning(
                    f"Failed to create payment configuration {request.configuration_name}: {response.get('error')}"
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
        error_msg = f"Unexpected error creating payment configuration: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }