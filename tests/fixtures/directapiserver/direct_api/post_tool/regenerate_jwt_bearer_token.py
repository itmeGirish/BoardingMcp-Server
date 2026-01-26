"""Tests for regenerate_jwt_bearer_token POST endpoint via MCP."""

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
async def test_inspect_regenerate_jwt_bearer_token_schema(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Inspect the schema of regenerate_jwt_bearer_token tool."""
    tools = await direct_api_mcp_client.list_tools()
    
    target_tool = next(
        (t for t in tools if t.name == "regenerate_jwt_bearer_token"), None
    )
    
    assert target_tool is not None, "Tool not found"
    
    print("\n" + "="*80)
    print("TOOL SCHEMA FOR: regenerate_jwt_bearer_token")
    print("="*80)
    print(f"Name: {target_tool.name}")
    print(f"\nDescription: {target_tool.description}")
    print(f"\nInput Schema:")
    print(json.dumps(target_tool.inputSchema, indent=2))
    print("="*80)


@pytest.mark.parametrize(
    "user_id, direct_api, expected_success",
    [
        ("user1", True, True),    # Valid user with direct_api=True# Invalid user should fail
    ],
)
@pytest.mark.asyncio
async def test_regenerate_jwt_bearer_token(
    user_id: str,
    direct_api: bool,
    expected_success: bool,
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Test regenerating JWT bearer token.

    The tool automatically fetches email, password, and project_id from the database
    based on the provided user_id, creates a base64 token, and calls the API.
    
    Args:
        user_id: User ID to fetch credentials for
        direct_api: Boolean flag for direct API usage
        expected_success: Whether this test case should succeed
    """
    print(f"\n{'='*80}")
    print(f"Testing regenerate_jwt_bearer_token")
    print(f"  - user_id: {user_id}")
    print(f"  - direct_api: {direct_api}")
    print(f"  - expected_success: {expected_success}")
    print(f"{'='*80}")
    
    # Call the tool
    result = await direct_api_mcp_client.call_tool(
        "regenerate_jwt_bearer_token",
        arguments={"user_id": user_id, "direct_api": direct_api},
    )
    
    print(f"\n=== Result ===")
    print(json.dumps(result.data, indent=2))

    # Assertions
    assert result.data is not None, "Result should not be None"
    assert isinstance(result.data, dict), "Result should be a dictionary"
    assert "success" in result.data, "Result should contain 'success' field"
    
    if expected_success:
        assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"
        assert "data" in result.data, "Successful response should contain 'data' field"
        # You can add more specific assertions about the token structure
    else:
        assert result.data["success"] is False, "Expected failure but got success"
        assert "error" in result.data, "Failed response should contain 'error' field"


@pytest.mark.asyncio
async def test_regenerate_jwt_bearer_token_missing_user_id(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Test that tool fails when user_id is not provided."""
    with pytest.raises(Exception) as exc_info:
        await direct_api_mcp_client.call_tool(
            "regenerate_jwt_bearer_token",
            arguments={"direct_api": True},  # Missing user_id
        )
    
    assert "user_id" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_regenerate_jwt_bearer_token_default_params(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Test with default direct_api parameter."""
    result = await direct_api_mcp_client.call_tool(
        "regenerate_jwt_bearer_token",
        arguments={"user_id": "user1"},  # direct_api will use default (True)
    )
    
    print(f"\n=== Result with default direct_api ===")
    print(json.dumps(result.data, indent=2))

    assert result.data is not None
    assert result.data.get("success") in [True, False]  # Should get a valid response