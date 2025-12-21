"""
MCP Tool: Generate Payment Configuration OAuth Link

Generates a payment configuration OAuth link via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import GeneratePaymentConfigurationOAuthLinkRequest
from app import logger


@mcp.tool(
    name="generate_payment_configuration_oauth_link",
    description=(
        "Generates a payment configuration OAuth link via the AiSensy Direct API. "
        "Returns an OAuth authorization URL for payment provider integration."
    ),
    tags={
        "payment",
        "oauth",
        "link",
        "generate",
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
async def generate_payment_configuration_oauth_link(
    configuration_name: str,
    redirect_url: str
) -> Dict[str, Any]:
    """
    Generate a payment configuration OAuth link.
    
    Args:
        configuration_name: Name of the payment configuration
        redirect_url: Redirect URL after OAuth
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): OAuth link details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = GeneratePaymentConfigurationOAuthLinkRequest(
            configuration_name=configuration_name,
            redirect_url=redirect_url
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.generate_payment_configuration_oauth_link(
                configuration_name=request.configuration_name,
                redirect_url=request.redirect_url
            )
            
            if response.get("success"):
                logger.info(f"Successfully generated OAuth link for: {request.configuration_name}")
            else:
                logger.warning(
                    f"Failed to generate OAuth link for {request.configuration_name}: {response.get('error')}"
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
        error_msg = f"Unexpected error generating OAuth link: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }