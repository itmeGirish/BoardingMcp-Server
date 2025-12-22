"""Tests for create_project POST endpoint via MCP."""

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
    "project_name, user_id",
    [
        ("my_test_project", "user_45618"),
    ],
)
@pytest.mark.asyncio
async def test_create_project(
    project_name: str,
    user_id: str,
    main_mcp_client: Client[FastMCPTransport],
):
    """Test creating a new project."""
    result = await main_mcp_client.call_tool(
        "create_project",
        arguments={"name": project_name, "user_id": user_id},
    )
    print(f"\n=== Create Project: {project_name} ===")
    print(result.data)

    # Add assertions
    assert result.data is not None