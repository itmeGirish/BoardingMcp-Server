"""
MCP Tool: Get Flow by ID

Fetches a specific flow by ID from the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_get_client
from ....models import GetFlowIdRequest
from app import logger


@mcp.tool(
    name="get_flow_by_id",
    description=(
        "Fetches a specific flow by ID from the AiSensy Direct API. "
        "Returns the flow details including name, categories, status, "
        "and configuration for the given flow ID."
    ),
    tags={
        "flow",
        "detail",
        "get",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Flow Management"
    }
)
async def get_flow_by_id(flow_id: str) -> Dict[str, Any]:
    """
    Fetch a specific flow by ID.
    
    Args:
        flow_id: The unique flow identifier
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Flow details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = GetFlowIdRequest(flow_id=flow_id)
        
        async with get_direct_api_get_client() as client:
            response = await client.get_flow_by_id(
                flow_id=request.flow_id
            )
            
            if response.get("success"):
                logger.info(f"Successfully retrieved flow: {request.flow_id}")
            else:
                logger.warning(
                    f"Failed to retrieve flow {request.flow_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error fetching flow: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }