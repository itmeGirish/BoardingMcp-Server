"""Tests for start_migration POST endpoint via MCP."""

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
    "assistant_id,target_id,country_code,phone_number",
    [
        (
            "66a73a246f969d0b5dbb6903",
            "107945432259014",
            "91",
            "8645614148",
        ),
        (
            "66a73a246f969d0b5dbb6904",
            "107945432259015",
            "1",
            "2125551234",
        ),
    ],
)
@pytest.mark.asyncio
async def test_start_migration(
    assistant_id: str,
    target_id: str,
    country_code: str,
    phone_number: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test starting migration process."""
    result = await main_mcp_client.call_tool(
        "start_migration",
        arguments={
            "assistant_id": assistant_id,
            "target_id": target_id,
            "country_code": country_code,
            "phone_number": phone_number,
        },
    )
    print(f"\n=== Start Migration: {phone_number} ===")
    print(result.data)

    # Add assertions
    assert result.data is not None