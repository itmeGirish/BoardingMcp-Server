"""
MCP Tool: Publish Flow

Publishes a flow via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import PostFlowIdRequest
from app import logger


@mcp.tool(
    name="publish_flow",
    description=(
        "Publishes a flow via the AiSensy Direct API. "
        "Makes the flow live and available for use."
    ),
    tags={
        "flow",
        "publish",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Flow Management"
    }
)
async def publish_flow(flow_id: str) -> Dict[str, Any]:
    """
    Publish a flow.
    
    Args:
        flow_id: The flow ID to publish
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = PostFlowIdRequest(flow_id=flow_id)
        
        async with get_direct_api_post_client() as client:
            response = await client.publish_flow(
                flow_id=request.flow_id
            )
            
            if response.get("success"):
                logger.info(f"Successfully published flow: {request.flow_id}")
            else:
                logger.warning(
                    f"Failed to publish flow {request.flow_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error publishing flow: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }