"""Tests for submit_waba_app_id POST endpoint via MCP."""

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
    "assistant_id,waba_app_id",
    [
        (
            "66a73a246f969d0b5dbb6903",
            "100375269493439",
        ),
        (
            "66a73a246f969d0b5dbb6904",
            "100375269493440",
        ),
    ],
)
@pytest.mark.asyncio
async def test_submit_waba_app_id(
    assistant_id: str,
    waba_app_id: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test submitting WABA App ID (Facebook Access Token)."""
    result = await main_mcp_client.call_tool(
        "submit_waba_app_id",
        arguments={
            "assistant_id": assistant_id,
            "waba_app_id": waba_app_id,
        },
    )
    print(f"\n=== Submit WABA App ID: {waba_app_id} ===")
    print(result.data)

    # Add assertions
    assert result.data is not None