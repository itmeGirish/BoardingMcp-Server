"""Tests for generate_ctwa_ads_manager_dashboard_url POST endpoint via MCP."""

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
    "business_id,assistant_id,expires_in",
    [
        (
            "6880aa4c61c4b97902d4c1ce",
            "6880aa4c61c4b97902d4c1d5",
            150000,
        ),
        (
            "6880aa4c61c4b97902d4c1cf",
            "6880aa4c61c4b97902d4c1d6",
            200000,
        ),
    ],
)
@pytest.mark.asyncio
async def test_generate_ctwa_ads_manager_dashboard_url(
    business_id: str,
    assistant_id: str,
    expires_in: int,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test generating CTWA (Click-to-WhatsApp) Ads Manager Dashboard URL."""
    result = await main_mcp_client.call_tool(
        "generate_ctwa_ads_manager_dashboard_url",
        arguments={
            "business_id": business_id,
            "assistant_id": assistant_id,
            "expires_in": expires_in,
        },
    )
    print(f"\n=== Generate CTWA Ads Manager Dashboard URL: {business_id} ===")
    print(result.data)

    # Add assertions
    assert result.data is not None