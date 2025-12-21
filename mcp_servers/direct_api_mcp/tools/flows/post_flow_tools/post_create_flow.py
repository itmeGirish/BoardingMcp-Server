"""
MCP Tool: Create Flow

Creates a flow via the AiSensy Direct API.
"""
from typing import Dict, Any, List

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import CreateFlowRequest
from app import logger


@mcp.tool(
    name="create_flow",
    description=(
        "Creates a flow via the AiSensy Direct API. "
        "Supports creating flows with specified name and categories."
    ),
    tags={
        "flow",
        "create",
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
async def create_flow(
    name: str,
    categories: List[str]
) -> Dict[str, Any]:
    """
    Create a flow.
    
    Args:
        name: Flow name
        categories: List of flow categories (e.g., ["APPOINTMENT_BOOKING"])
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Created flow details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = CreateFlowRequest(
            name=name,
            categories=categories
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.create_flow(
                name=request.name,
                categories=request.categories
            )
            
            if response.get("success"):
                logger.info(f"Successfully created flow: {request.name}")
            else:
                logger.warning(
                    f"Failed to create flow {request.name}: {response.get('error')}"
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
        error_msg = f"Unexpected error creating flow: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }