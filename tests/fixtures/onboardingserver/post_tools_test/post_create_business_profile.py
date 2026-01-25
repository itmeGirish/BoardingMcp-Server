import pytest
import pytest_asyncio
from fastmcp.client import Client

@pytest_asyncio.fixture(scope="function")
async def main_mcp_client():
    """Initialize MCP client for onboarding server."""
    # Connect to the HTTP server at the URL
    async with Client("http://localhost:9001/mcp") as mcp_client:
        yield mcp_client


@pytest.mark.parametrize(
    "display_name,email,company,contact,timezone,currency,company_size,password,user_id,onboarding_id",
    [
        (
            "DataFlow Analyticsgg",
            "girishstarup@gmail.com",
            "DataFlow Inc3344",
            "9188666775544",
            "Asia/Calcutta GMT+05:30",
            "USD",
            "50 - 100",
            "Analytics@123",
            "user_8861",
            "onb_789619",
        ),
    ],
)
@pytest.mark.asyncio
async def test_create_business_profile(
    main_mcp_client,
    display_name,
    email,
    company,
    contact,
    timezone,
    currency,
    company_size,
    password,
    user_id,
    onboarding_id,
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
    print(f"Result: {result.data}")
    
    assert result.data is not None