"""
MCP Tool: Deprecate Flow

Deprecates a flow via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import PostFlowIdRequest
from app import logger


@mcp.tool(
    name="deprecate_flow",
    description=(
        "Deprecates a flow via the AiSensy Direct API. "
        "Marks the flow as deprecated and prevents further use."
    ),
    tags={
        "flow",
        "deprecate",
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
async def deprecate_flow(flow_id: str) -> Dict[str, Any]:
    """
    Deprecate a flow.
    
    Args:
        flow_id: The flow ID to deprecate
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = PostFlowIdRequest(flow_id=flow_id)
        
        async with get_direct_api_post_client() as client:
            response = await client.deprecate_flow(
                flow_id=request.flow_id
            )
            
            if response.get("success"):
                logger.info(f"Successfully deprecated flow: {request.flow_id}")
            else:
                logger.warning(
                    f"Failed to deprecate flow {request.flow_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error deprecating flow: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }