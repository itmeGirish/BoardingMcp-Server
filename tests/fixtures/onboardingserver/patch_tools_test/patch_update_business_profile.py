"""Tests for update_business_details PATCH endpoint via MCP."""

import pytest
import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest_asyncio.fixture
async def main_mcp_client():
    """Initialize MCP client for onboarding server."""
    async with Client("mcp_servers/onboardserver.py") as mcp_client:
        yield mcp_client

# 918877665544

@pytest.mark.parametrize(
    "user_id,display_name,company,contact",
    [
        (   "user_45618",
            "Tech Analytics",
            "Tech Inc",
            "918861832566",
        )
    ],
)
@pytest.mark.asyncio
async def test_update_business_details(
    user_id:str,
    display_name: str,
    company: str,
    contact: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test updating business details with all fields."""
    result = await main_mcp_client.call_tool(
        "update_business_details",
        arguments={
            "user_id":user_id,
            "display_name": display_name,
            "company": company,
            "contact": contact,
       
        },
    )
    print(f"\n=== Update Business Details: All Fields ===")
    print(f"Display Name: {display_name}")
    print(f"Company: {company}")
    print(f"Contact: {contact}")
    print(result.data)

    # Add assertions
    assert result.data is not None