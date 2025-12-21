"""Tests for request_otp_for_verification POST endpoint via MCP."""

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
    "assistant_id,mode",
    [
        (
            "66a73a246f969d0b5dbb6903",
            "sms",
        ),
        (
            "66a73a246f969d0b5dbb6904",
            "voice",
        ),
    ],
)
@pytest.mark.asyncio
async def test_request_otp_for_verification(
    assistant_id: str,
    mode: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test requesting OTP for verification during migration."""
    result = await main_mcp_client.call_tool(
        "request_otp_for_verification",
        arguments={
            "assistant_id": assistant_id,
            "mode": mode,
        },
    )
    print(f"\n=== Request OTP: {mode} mode ===")
    print(result.data)

    # Add assertions
    assert result.data is not None