"""
MCP Tool: Update Flow Metadata

Updates flow metadata via the AiSensy Direct API.
"""
from typing import Dict, Any, Optional, List

from ... import mcp
from ....clients import get_direct_api_patch_client
from ....models import UpdateFlowMetadataRequest
from app import logger


@mcp.tool(
    name="update_flow_metadata",
    description=(
        "Updates flow metadata via the AiSensy Direct API. "
        "Supports updating flow name and categories."
    ),
    tags={
        "flow",
        "metadata",
        "update",
        "patch",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Flow Management"
    }
)
async def update_flow_metadata(
    flow_id: str,
    name: Optional[str] = None,
    categories: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Update flow metadata.
    
    Args:
        flow_id: The flow ID to update
        name: New flow name (optional)
        categories: New list of flow categories (optional)
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = UpdateFlowMetadataRequest(
            flow_id=flow_id,
            name=name,
            categories=categories
        )
        
        async with get_direct_api_patch_client() as client:
            response = await client.update_flow_metadata(
                flow_id=request.flow_id,
                name=request.name,
                categories=request.categories
            )
            
            if response.get("success"):
                logger.info(f"Successfully updated flow metadata: {request.flow_id}")
            else:
                logger.warning(
                    f"Failed to update flow metadata {request.flow_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error updating flow metadata: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }