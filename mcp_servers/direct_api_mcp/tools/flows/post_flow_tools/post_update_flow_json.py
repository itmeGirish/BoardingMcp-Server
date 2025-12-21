"""
MCP Tool: Update Flow JSON

Updates a flow's JSON via the AiSensy Direct API.
"""
from typing import Dict, Any

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import UpdateFlowJsonRequest
from app import logger


@mcp.tool(
    name="update_flow_json",
    description=(
        "Updates a flow's JSON via the AiSensy Direct API. "
        "Uploads new flow assets/configuration for the specified flow."
    ),
    tags={
        "flow",
        "update",
        "json",
        "assets",
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
async def update_flow_json(
    flow_id: str,
    file_path: str
) -> Dict[str, Any]:
    """
    Update a flow's JSON.
    
    Args:
        flow_id: The flow ID to update
        file_path: Path to the JSON file to upload
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = UpdateFlowJsonRequest(
            flow_id=flow_id,
            file_path=file_path
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.update_flow_json(
                flow_id=request.flow_id,
                file_path=request.file_path
            )
            
            if response.get("success"):
                logger.info(f"Successfully updated flow JSON: {request.flow_id}")
            else:
                logger.warning(
                    f"Failed to update flow JSON {request.flow_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error updating flow JSON: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }