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
    "display_name,company,contact",
    [
        (
            "Agent@Tapes",
            "AgentTape",
            "918877665544",
        )
    ],
)
@pytest.mark.asyncio
async def test_update_business_details(
    display_name: str,
    company: str,
    contact: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test updating business details with all fields."""
    result = await main_mcp_client.call_tool(
        "update_business_details",
        arguments={
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


@pytest.mark.parametrize(
    "display_name,company,contact",
    [
        (
            "CallHippo Updated",
            None,
            None,
        ),
        (
            None,
            "TechStartup Solutions",
            None,
        ),
        (
            None,
            None,
            "918116856153",
        ),
    ],
)
@pytest.mark.asyncio
async def test_update_business_details_partial(
    display_name: str,
    company: str,
    contact: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test updating business details with partial fields."""
    result = await main_mcp_client.call_tool(
        "update_business_details",
        arguments={
            "display_name": display_name,
            "company": company,
            "contact": contact,
        },
    )
    print(f"\n=== Update Business Details: Partial Fields ===")
    if display_name:
        print(f"Display Name: {display_name}")
    if company:
        print(f"Company: {company}")
    if contact:
        print(f"Contact: {contact}")
    print(result.data)

    # Add assertions
    assert result.data is not None


@pytest.mark.parametrize(
    "display_name,company,contact",
    [
        (
            "Updated Display Name Only",
            None,
            None,
        ),
        (
            None,
            "Updated Company Name Only",
            None,
        ),
        (
            None,
            None,
            "919999999999",
        ),
    ],
)
@pytest.mark.asyncio
async def test_update_business_details_single_field(
    display_name: str,
    company: str,
    contact: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test updating business details with single field at a time."""
    result = await main_mcp_client.call_tool(
        "update_business_details",
        arguments={
            "display_name": display_name,
            "company": company,
            "contact": contact,
        },
    )
    print(f"\n=== Update Business Details: Single Field ===")
    if display_name:
        print(f"Updating Display Name: {display_name}")
    elif company:
        print(f"Updating Company: {company}")
    elif contact:
        print(f"Updating Contact: {contact}")
    print(result.data)

    # Add assertions
    assert result.data is not None


@pytest.mark.parametrize(
    "display_name,company,contact",
    [
        (
            "Enterprise Business Solutions",
            "Enterprise Corp",
            "14155552671",
        ),
        (
            "Startup Innovation Lab",
            "Startup Labs",
            "14155553000",
        ),
    ],
)
@pytest.mark.asyncio
async def test_update_business_details_various_regions(
    display_name: str,
    company: str,
    contact: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test updating business details with various regional data."""
    result = await main_mcp_client.call_tool(
        "update_business_details",
        arguments={
            "display_name": display_name,
            "company": company,
            "contact": contact,
        },
    )
    print(f"\n=== Update Business Details: Regional Data ===")
    print(f"Display Name: {display_name}")
    print(f"Company: {company}")
    print(f"Contact: {contact}")
    print(result.data)

    # Add assertions
    assert result.data is not None