"""
MCP Tool: Regenerate JWT Bearer Token

Regenerates JWT Bearer Token to Access Direct-APIs.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import RegenerateJwtBearerTokenRequest
from app import logger


@mcp.tool(
    name="regenerate_jwt_bearer_token",
    description=(
        "Regenerates JWT Bearer Token to Access Direct-APIs. "
        "Returns a new authentication token for API access."
    ),
    tags={
        "auth",
        "token",
        "jwt",
        "regenerate",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Authentication"
    }
)
async def regenerate_jwt_bearer_token(direct_api: bool = True) -> Dict[str, Any]:
    """
    Regenerate JWT Bearer Token.
    
    Args:
        direct_api: Whether to use direct API (default: True)
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): New token details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = RegenerateJwtBearerTokenRequest(direct_api=direct_api)
        
        async with get_direct_api_post_client() as client:
            response = await client.regenerate_jwt_bearer_token(
                direct_api=request.direct_api
            )
            
            if response.get("success"):
                logger.info("Successfully regenerated JWT bearer token")
            else:
                logger.warning(
                    f"Failed to regenerate JWT bearer token: {response.get('error')}"
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
        error_msg = f"Unexpected error regenerating JWT bearer token: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }