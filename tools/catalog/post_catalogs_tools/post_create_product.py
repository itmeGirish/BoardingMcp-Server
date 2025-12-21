"""
MCP Tool: Create Product

Creates a product via the AiSensy Direct API.
"""
from typing import Dict, Any, Optional

from ... import mcp
from ....clients import get_direct_api_post_client
from ....models import CreateProductRequest
from app import logger


@mcp.tool(
    name="create_product",
    description=(
        "Creates a product via the AiSensy Direct API. "
        "Adds a new product to the specified catalog with pricing and details."
    ),
    tags={
        "product",
        "create",
        "catalog",
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
async def create_product(
    catalog_id: str,
    name: str,
    category: str,
    currency: str,
    image_url: str,
    price: str,
    retailer_id: str,
    description: Optional[str] = None,
    url: Optional[str] = None,
    brand: Optional[str] = None,
    sale_price: Optional[str] = None,
    sale_price_start_date: Optional[str] = None,
    sale_price_end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a product.
    
    Args:
        catalog_id: The catalog ID to add product to
        name: Product name
        category: Product category
        currency: Currency code (e.g., "INR")
        image_url: Product image URL
        price: Product price
        retailer_id: Retailer ID
        description: Product description (optional)
        url: Product URL (optional)
        brand: Product brand (optional)
        sale_price: Sale price (optional)
        sale_price_start_date: Sale start date (optional)
        sale_price_end_date: Sale end date (optional)
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Created product details if successful
        - error (str): Error message if unsuccessful
    """
    try:
        request = CreateProductRequest(
            catalog_id=catalog_id,
            name=name,
            category=category,
            currency=currency,
            image_url=image_url,
            price=price,
            retailer_id=retailer_id,
            description=description,
            url=url,
            brand=brand,
            sale_price=sale_price,
            sale_price_start_date=sale_price_start_date,
            sale_price_end_date=sale_price_end_date
        )
        
        async with get_direct_api_post_client() as client:
            response = await client.create_product(
                catalog_id=request.catalog_id,
                name=request.name,
                category=request.category,
                currency=request.currency,
                image_url=request.image_url,
                price=request.price,
                retailer_id=request.retailer_id,
                description=request.description,
                url=request.url,
                brand=request.brand,
                sale_price=request.sale_price,
                sale_price_start_date=request.sale_price_start_date,
                sale_price_end_date=request.sale_price_end_date
            )
            
            if response.get("success"):
                logger.info(f"Successfully created product: {request.name}")
            else:
                logger.warning(
                    f"Failed to create product {request.name}: {response.get('error')}"
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
        error_msg = f"Unexpected error creating product: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }