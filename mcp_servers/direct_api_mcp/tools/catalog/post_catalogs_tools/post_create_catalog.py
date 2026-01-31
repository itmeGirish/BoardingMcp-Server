"""
MCP Tool: Create Catalog

Creates a catalog via the AiSensy Direct API.
"""
from typing import Dict, Any, Optional, List

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import CreateCatalogRequest
from app import logger
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import MemoryRepository


@mcp.tool(
    name="create_catalog",
    description=(
        "Creates a catalog via the AiSensy Direct API. "
        "Supports creating catalogs with products, images, and display settings."
    ),
    tags={
        "catalog",
        "create",
        "commerce",
        "post",
        "direct-api",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Catalog Management"
    }
)
async def create_catalog(
    user_id:str,
    name: str,
    vertical: str = "commerce",
    product_count: int = 0,
    feed_count: int = 1,
    default_image_url: Optional[str] = None,
    fallback_image_url: Optional[List[str]] = None,
    is_catalog_segment: bool = False,
    da_display_settings: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a catalog.
    
    Args:
        name: Catalog name
        vertical: Catalog vertical (default: "commerce")
        product_count: Number of products (default: 0)
        feed_count: Number of feeds (default: 1)
        default_image_url: Default image URL (optional)
        fallback_image_url: List of fallback image URLs (optional)
        is_catalog_segment: Whether catalog is a segment (default: False)
        da_display_settings: Display settings for dynamic ads (optional)
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Created catalog details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = CreateCatalogRequest(
            name=name,
            vertical=vertical,
            product_count=product_count,
            feed_count=feed_count,
            default_image_url=default_image_url,
            fallback_image_url=fallback_image_url,
            is_catalog_segment=is_catalog_segment,
            da_display_settings=da_display_settings
        )

        logger.info(f"Fetching JWT token from TempMemory for user_id: {user_id}")
        with get_session() as session:
            memory_repo = MemoryRepository(session=session)
            memory_record = memory_repo.get_by_user_id(user_id)

        if not memory_record or not memory_record.get("jwt_token"):
            error_msg = f"No JWT token found in TempMemory for user_id: {user_id}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        jwt_token = memory_record["jwt_token"]
        logger.info(f"JWT token fetched successfully for user_id: {user_id}")

        
        async with get_direct_api_post_client() as client:
            response = await client.create_catalog(
                jwt_token=jwt_token,
                name=request.name,
                vertical=request.vertical,
                product_count=request.product_count,
                feed_count=request.feed_count,
                default_image_url=request.default_image_url,
                fallback_image_url=request.fallback_image_url,
                is_catalog_segment=request.is_catalog_segment,
                da_display_settings=request.da_display_settings,
               
            )
            
            if response.get("success"):
                logger.info(f"Successfully created catalog: {request.name}")
            else:
                logger.warning(
                    f"Failed to create catalog {request.name}: {response.get('error')}"
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
        error_msg = f"Unexpected error creating catalog: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }