"""Tests for generate_embedded_fb_catalog_url POST endpoint via MCP."""

import pytest
import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest_asyncio.fixture
async def main_mcp_client():
    """Initialize MCP client for onboarding server."""
    async with Client("mcp_servers/onboardserver.py") as mcp_client:
        yield mcp_client


@pytest.mark.parametrize(
    "business_id,assistant_id",
    [
        (
            "67482a210fa2703716c11a4e",
            "66a73a246f969d0b5dbb6903",
        ),
        (
            "67482a210fa2703716c11a4f",
            "66a73a246f969d0b5dbb6904",
        ),
    ],
)
@pytest.mark.asyncio
async def test_generate_embedded_fb_catalog_url(
    business_id: str,
    assistant_id: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test generating an embedded Facebook Catalog connect URL."""
    result = await main_mcp_client.call_tool(
        "generate_embedded_fb_catalog_url",
        arguments={
            "business_id": business_id,
            "assistant_id": assistant_id,
        },
    )
    print(f"\n=== Generate FB Catalog URL: {business_id} ===")
    print(result.data)

    # Add assertions
    assert result.data is not None