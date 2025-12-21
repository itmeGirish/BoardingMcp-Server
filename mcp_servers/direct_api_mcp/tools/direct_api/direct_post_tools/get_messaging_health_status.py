"""
MCP Tool: Post Messaging Health Status

Fetches Messaging Health Status from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import MessagingHealthStatusRequest
from app import logger


@mcp.tool(
    name="get_messaging_health_status",
    description=(
        "Fetches Messaging Health Status from the AiSensy Direct API. "
        "Returns the health status of messaging services for the specified node."
    ),
    tags={
        "messaging",
        "health",
        "status",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Health Monitoring"
    }
)
async def get_messaging_health_status(node_id: str) -> Dict[str, Any]:
    """
    Fetch Messaging Health Status.
    
    Args:
        node_id: The node ID to check health status for
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Health status if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = MessagingHealthStatusRequest(node_id=node_id)
        
        async with get_direct_api_post_client() as client:
            response = await client.get_messaging_health_status(
                node_id=request.node_id
            )
            
            if response.get("success"):
                logger.info(f"Successfully retrieved messaging health status for node: {request.node_id}")
            else:
                logger.warning(
                    f"Failed to retrieve messaging health status: {response.get('error')}"
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
        error_msg = f"Unexpected error fetching messaging health status: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }