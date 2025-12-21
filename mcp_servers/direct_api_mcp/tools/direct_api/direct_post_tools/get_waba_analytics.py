"""
MCP Tool: Post WABA Analytics

Fetches WABA Analytics from the AiSensy Direct API.
"""
from typing import Dict, Any, Optional, List

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import WabaAnalyticsRequest
from app import logger


@mcp.tool(
    name="get_waba_analytics",
    description=(
        "Fetches WABA Analytics from the AiSensy Direct API. "
        "Returns analytics data for the specified time period including "
        "message counts, delivery rates, and engagement metrics."
    ),
    tags={
        "waba",
        "analytics",
        "metrics",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Analytics"
    }
)
async def get_waba_analytics(
    fields: str,
    start: int,
    end: int,
    granularity: str,
    country_codes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Fetch WABA Analytics.
    
    Args:
        fields: Analytics fields to fetch (e.g., "analytics")
        start: Start timestamp (Unix epoch)
        end: End timestamp (Unix epoch)
        granularity: Data granularity (DAY, MONTH, HOUR)
        country_codes: List of country codes to filter (optional)
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Analytics data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = WabaAnalyticsRequest(
            fields=fields,
            start=start,
            end=end,
            granularity=granularity,
            country_codes=country_codes
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.get_waba_analytics(
                fields=request.fields,
                start=request.start,
                end=request.end,
                granularity=request.granularity,
                country_codes=request.country_codes
            )
            
            if response.get("success"):
                logger.info("Successfully retrieved WABA analytics")
            else:
                logger.warning(
                    f"Failed to retrieve WABA analytics: {response.get('error')}"
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
        error_msg = f"Unexpected error fetching WABA analytics: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }