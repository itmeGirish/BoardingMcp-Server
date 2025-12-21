"""Tests for verify_otp POST endpoint via MCP."""

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
    "assistant_id,otp",
    [
        (
            "66a73a246f969d0b5dbb6903",
            "123456",
        ),
        (
            "66a73a246f969d0b5dbb6904",
            "654321",
        ),
    ],
)
@pytest.mark.asyncio
async def test_verify_otp(
    assistant_id: str,
    otp: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test verifying OTP for migration to partner."""
    result = await main_mcp_client.call_tool(
        "verify_otp",
        arguments={
            "assistant_id": assistant_id,
            "otp": otp,
        },
    )
    print(f"\n=== Verify OTP: {otp} ===")
    print(result.data)

    # Add assertions
    assert result.data is not None