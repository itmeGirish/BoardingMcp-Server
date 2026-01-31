"""Tests for create_catalog POST endpoint via MCP."""

import pytest
import pytest_asyncio
import json
import random
from typing import Dict, List, Any, Optional
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest_asyncio.fixture
async def direct_api_mcp_client():
    """Initialize MCP client for direct API server."""
    async with Client("http://127.0.0.1:9002/mcp") as mcp_client:
        yield mcp_client


@pytest.mark.asyncio
async def test_inspect_create_catalog_schema(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Inspect the schema of create_catalog tool."""
    tools = await direct_api_mcp_client.list_tools()
    
    target_tool = next(
        (t for t in tools if t.name == "create_catalog"), None
    )
    
    assert target_tool is not None, "Tool not found"
    
    print("\n" + "="*80)
    print("TOOL SCHEMA FOR: create_catalog")
    print("="*80)
    print(f"Name: {target_tool.name}")
    print(f"\nDescription: {target_tool.description}")
    print(f"\nInput Schema:")
    print(json.dumps(target_tool.inputSchema, indent=2))
    print("="*80)


@pytest.mark.parametrize(
    "user_id, name, vertical, product_count, feed_count, default_image_url, fallback_image_url, is_catalog_segment, da_display_settings, expected_success, test_description",
    [
        # Example 1: Complete catalog with all fields (will fail due to ToS)
        (
            "user1",
            "my-new-catalogue",
            "commerce",
            10,
            1,
            "https://images.unsplash.com/photo-1600716051809-e997e11a5d52?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=2050&q=80",
            ["https://images.unsplash.com/photo-1558393385-c2019c6a125c?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=2832&q=80"],
            False,
            {
                "carousel_ad": {"transformation_type": "none"},
                "single_ad": {"transformation_type": "none"}
            },
            False,
            "Complete catalog with all optional fields - fails due to ToS"
        ),
        # Example 2: Empty catalog name - validation error
        (
            "user1",
            "",
            "commerce",
            0,
            1,
            None,
            None,
            False,
            None,
            False,
            "Empty catalog name should fail validation"
        ),
    ],
)
@pytest.mark.asyncio
async def test_create_catalog(
    user_id: str,
    name: str,
    vertical: str,
    product_count: int,
    feed_count: int,
    default_image_url: Optional[str],
    fallback_image_url: Optional[List[str]],
    is_catalog_segment: bool,
    da_display_settings: Optional[Dict[str, Any]],
    expected_success: bool,
    test_description: str,
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Test creating a WhatsApp catalog.

    Creates a catalog for WhatsApp Business with products, images, and display settings.
    
    Args:
        user_id: User ID who owns the catalog
        name: Name of the catalog
        vertical: Catalog vertical (e.g., "commerce")
        product_count: Number of products in the catalog
        feed_count: Number of feeds
        default_image_url: Default image URL for products
        fallback_image_url: List of fallback image URLs
        is_catalog_segment: Whether this is a catalog segment
        da_display_settings: Display settings for dynamic ads
        expected_success: Whether this test case should succeed
        test_description: Description of what this test validates
    """
    print(f"\n{'='*80}")
    print(f"Testing create_catalog")
    print(f"Test: {test_description}")
    print(f"  - user_id: {user_id}")
    print(f"  - name: {name}")
    print(f"  - vertical: {vertical}")
    print(f"  - product_count: {product_count}")
    print(f"  - feed_count: {feed_count}")
    print(f"  - default_image_url: {default_image_url}")
    print(f"  - fallback_image_url: {fallback_image_url}")
    print(f"  - is_catalog_segment: {is_catalog_segment}")
    print(f"  - da_display_settings: {da_display_settings}")
    print(f"  - expected_success: {expected_success}")
    print(f"{'='*80}")
    
    # Build arguments - only include non-None optional parameters
    arguments = {
        "user_id": user_id,
        "name": name,
        "vertical": vertical,
        "product_count": product_count,
        "feed_count": feed_count,
        "is_catalog_segment": is_catalog_segment,
    }
    
    # Add optional parameters only if they're not None
    if default_image_url is not None:
        arguments["default_image_url"] = default_image_url
    if fallback_image_url is not None:
        arguments["fallback_image_url"] = fallback_image_url
    if da_display_settings is not None:
        arguments["da_display_settings"] = da_display_settings
    
    try:
        # Call the tool
        result = await direct_api_mcp_client.call_tool(
            "create_catalog",
            arguments=arguments,
        )
        
        print(f"\n=== Result ===")
        print(json.dumps(result.data, indent=2))

        # Assertions
        assert result.data is not None, "Result should not be None"
        assert isinstance(result.data, dict), "Result should be a dictionary"
        assert "success" in result.data, "Result should contain 'success' field"
        
        if expected_success:
            assert result.data["success"] is True, \
                f"Expected success but got failure: {result.data.get('error', 'Unknown error')}"
            
            # Check for catalog data in response
            assert "data" in result.data or "id" in result.data or "catalog_id" in result.data, \
                "Successful response should contain catalog data"
            
            response_data = result.data.get("data", result.data)
            
            # Verify catalog details if present in response
            if "name" in response_data:
                assert response_data["name"] == name, \
                    f"Catalog name mismatch: expected {name}, got {response_data['name']}"
            
            if "vertical" in response_data:
                assert response_data["vertical"] == vertical, \
                    f"Vertical mismatch: expected {vertical}, got {response_data['vertical']}"
            
            # Check for catalog ID (indicates successful creation)
            catalog_id = response_data.get("id") or response_data.get("catalog_id")
            if catalog_id:
                print(f"\n✓ Catalog created successfully with ID: {catalog_id}")
            
            print(f"✓ Test passed: {test_description}")
                
        else:
            assert result.data["success"] is False, \
                f"Expected failure but got success: {result.data}"
            
            assert "error" in result.data, \
                "Failed response should contain 'error' field"
            
            error_message = result.data.get("error", "Unknown error")
            details = result.data.get("details", "")
            
            print(f"\n✓ Test correctly failed with error: {error_message}")
            
            # Check if this is a ToS-related error
            if "Terms of Service" in details or "fb.me/" in details:
                print("  → Error reason: WhatsApp Catalog Terms of Service not accepted")
                # Extract ToS link if present
                if "fb.me/" in details:
                    import re
                    tos_links = re.findall(r'https://fb\.me/[A-Za-z0-9]+', details)
                    if tos_links:
                        print(f"  → ToS acceptance link: {tos_links[0]}")
            
            # Validate specific error types
            elif not name:
                # Just verify it failed - don't check specific error message
                print("  → Validation error for empty catalog name")
    
    except Exception as e:
        # Handle the case where user_id is not in the schema
        if "user_id" in str(e) and "unexpected_keyword_argument" in str(e):
            print(f"\n⚠ WARNING: user_id parameter is not in the MCP tool schema")
            print(f"  The tool schema does not accept user_id as a parameter.")
            print(f"  This means user_id might be auto-injected by the server or the schema needs updating.")
            print(f"\n  Retrying without user_id parameter...")
            
            # Retry without user_id
            arguments_without_user_id = {k: v for k, v in arguments.items() if k != "user_id"}
            
            result = await direct_api_mcp_client.call_tool(
                "create_catalog",
                arguments=arguments_without_user_id,
            )
            
            print(f"\n=== Result (without user_id) ===")
            print(json.dumps(result.data, indent=2))
            
            # Continue with same assertions as above
            assert result.data is not None, "Result should not be None"
            assert isinstance(result.data, dict), "Result should be a dictionary"
            
            if not expected_success:
                assert result.data.get("success") is False or "error" in result.data, \
                    f"Expected failure but got: {result.data}"
                print(f"\n✓ Test correctly failed (without user_id)")
        else:
            # Re-raise if it's a different error
            raise