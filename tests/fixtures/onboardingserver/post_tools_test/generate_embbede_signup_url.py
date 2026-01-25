"""Tests for generate_embedded_signup_url POST endpoint via MCP."""

import pytest
import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest_asyncio.fixture
async def main_mcp_client():
    """Initialize MCP client for onboarding server."""
    async with Client("http://localhost:9001/mcp") as mcp_client:
        yield mcp_client


@pytest.mark.parametrize(
    "user_id,business_name,business_email,phone_code,phone_number,website,street_address,city,state,zip_postal,country,timezone,display_name,category,description",
    [
        (
            "user_8861",
            "Acme Inc.",
            "johndoe888@acme.com",
            1,
            "6505551234",
            "https://www.acme.com",
            "1 Acme Way",
            "Acme Town",
            "CA",
            "94000",
            "US",
            "UTC-08:00",
            "Acme Inc.",
            "ENTERTAIN",
            "this is best ",
        )
    ],
)
@pytest.mark.asyncio
async def test_generate_embedded_signup_url(
    user_id: str,  # Added this
    business_name: str,
    business_email: str,
    phone_code: int,
    phone_number: str,
    website: str,
    street_address: str,
    city: str,
    state: str,
    zip_postal: str,
    country: str,
    timezone: str,
    display_name: str,
    category: str,
    description: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test generating an embedded signup URL for WABA."""
    result = await main_mcp_client.call_tool(
        "generate_embedded_signup_url",
        arguments={
            "user_id": user_id,  # Added this
            "business_name": business_name,
            "business_email": business_email,
            "phone_code": phone_code,
            "phone_number": phone_number,
            "website": website,
            "street_address": street_address,
            "city": city,
            "state": state,
            "zip_postal": zip_postal,
            "country": country,
            "timezone": timezone,
            "display_name": display_name,
            "category": category,
            "description": description,
        },
    )
    print(f"\n=== Generate Embedded Signup URL: {business_name} ===")
    print(result)