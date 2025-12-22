"""Tests for create_business_profile POST endpoint via MCP."""

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
    "display_name,email,company,contact,timezone,currency,company_size,password,user_id,onboarding_id",
    [
        (
            "DataFlow Analytics",
            "info_791d6e166dhhmkkj@dataflow.com",
            "DataFlow Inc",
            "918877665544",
            "Asia/Calcutta GMT+05:30",
            "USD",
            "50 - 100",
            "Analytics@123",
            "user_45618",
            "onb_789618",
        ),
    ],
)
@pytest.mark.asyncio
async def test_create_business_profile(
    main_mcp_client: Client[FastMCPTransport],
    display_name: str,
    email: str,
    company: str,
    contact: str,
    timezone: str,
    currency: str,
    company_size: str,
    password: str,
    user_id: str,
    onboarding_id: str,
):
    """Test creating a new business profile."""
    result = await main_mcp_client.call_tool(
        "create_business_profile",
        arguments={
            "display_name": display_name,
            "email": email,
            "company": company,
            "contact": contact,
            "timezone": timezone,
            "currency": currency,
            "company_size": company_size,
            "password": password,
            "user_id": user_id,
            "onboarding_id": onboarding_id,
        },
    )
    print(f"\n=== Create Business Profile: {display_name} ===")
    print(f"Email used: {email}")
    print(result.data)
    
    assert result.data is not None