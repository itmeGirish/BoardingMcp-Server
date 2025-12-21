"""
MCP Tool: Delete Flow

Deletes a flow via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_delete_client
from ....models import DeleteFlowRequest
from app import logger


@mcp.tool(
    name="delete_flow",
    description=(
        "Deletes a flow via the AiSensy Direct API. "
        "Permanently removes the flow from the account. "
        "This action cannot be undone."
    ),
    tags={
        "flow",
        "delete",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Flow Management"
    }
)
async def delete_flow(flow_id: str) -> Dict[str, Any]:
    """
    Delete a flow.
    
    Args:
        flow_id: The flow ID to delete
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = DeleteFlowRequest(flow_id=flow_id)
        
        async with get_direct_api_delete_client() as client:
            response = await client.delete_flow(
                flow_id=request.flow_id
            )
            
            if response.get("success"):
                logger.info(f"Successfully deleted flow: {request.flow_id}")
            else:
                logger.warning(
                    f"Failed to delete flow {request.flow_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error deleting flow: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }