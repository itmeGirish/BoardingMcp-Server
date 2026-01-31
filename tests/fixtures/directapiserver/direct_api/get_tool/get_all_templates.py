"""Tests for fb_verification_status GET endpoint via MCP."""

import pytest
import pytest_asyncio
import json
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport


@pytest_asyncio.fixture
async def direct_api_mcp_client():
    """Initialize MCP client for direct API server."""
    async with Client("http://127.0.0.1:9002/mcp") as mcp_client:
        yield mcp_client


@pytest.mark.asyncio
async def test_inspect_get_all_templates(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Inspect the schema of get_templates tool."""
    tools = await direct_api_mcp_client.list_tools()

    target_tool = next(
        (t for t in tools if t.name == "get_templates"), None
    )

    assert target_tool is not None, "Tool not found"

    print("\n" + "=" * 80)
    print("TOOL SCHEMA FOR: get_templates")
    print("=" * 80)
    print(f"Name: {target_tool.name}")
    print(f"\nDescription: {target_tool.description}")
    print(f"\nInput Schema:")
    print(json.dumps(target_tool.inputSchema, indent=2))
    print("=" * 80)


@pytest.mark.parametrize(
    "user_id, expected_success",
    [
        ("user1", True),  # Valid user with JWT token in TempMemory
    ],
)
@pytest.mark.asyncio
async def test_get_templates(
    user_id: str,
    expected_success: bool,
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Test fetching fb verification status.

    The tool fetches the JWT token from TempMemory using user_id,
    then calls the Direct API to get FB verification status.

    Args:
        user_id: User ID to fetch JWT token for
        expected_success: Whether this test case should succeed
    """
    print(f"\n{'=' * 80}")
    print(f"Testing get_templates")
    print(f"  - user_id: {user_id}")
    print(f"  - expected_success: {expected_success}")
    print(f"{'=' * 80}")

    result = await direct_api_mcp_client.call_tool(
        "get_templates",
        arguments={"user_id": user_id},
    )

    print(f"\n=== Result ===")
    print(json.dumps(result.data, indent=2))

    assert result.data is not None, "Result should not be None"
    assert isinstance(result.data, dict), "Result should be a dictionary"
    assert "success" in result.data, "Result should contain 'success' field"

    if expected_success:
        assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"
    else:
        assert result.data["success"] is False, "Expected failure but got success"
        assert "error" in result.data, "Failed response should contain 'error' field"

