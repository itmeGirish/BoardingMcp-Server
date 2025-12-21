"""
MCP Tool: Compare Template

Compares templates via the AiSensy Direct API.
"""
from typing import Dict, Any, List

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import CompareTemplateRequest
from app import logger


@mcp.tool(
    name="compare_template",
    description=(
        "Compares templates via the AiSensy Direct API. "
        "Returns comparison analytics for the specified templates "
        "over the given time period."
    ),
    tags={
        "template",
        "compare",
        "analytics",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Template Management"
    }
)
async def compare_template(
    template_id: str,
    template_ids: List[int],
    start: int,
    end: int
) -> Dict[str, Any]:
    """
    Compare templates.
    
    Args:
        template_id: The primary template ID for comparison
        template_ids: List of template IDs to compare
        start: Start timestamp (Unix epoch)
        end: End timestamp (Unix epoch)
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Comparison results if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = CompareTemplateRequest(
            template_id=template_id,
            template_ids=template_ids,
            start=start,
            end=end
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.compare_template(
                template_id=request.template_id,
                template_ids=request.template_ids,
                start=request.start,
                end=request.end
            )
            
            if response.get("success"):
                logger.info(f"Successfully compared template: {request.template_id}")
            else:
                logger.warning(
                    f"Failed to compare template {request.template_id}: {response.get('error')}"
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
        error_msg = f"Unexpected error comparing template: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }