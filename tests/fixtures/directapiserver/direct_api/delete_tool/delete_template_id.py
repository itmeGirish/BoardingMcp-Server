"""Tests for delete_wa_template_by_id DELETE endpoint via MCP."""

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
async def test_inspect_delete_template_schema(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Inspect the schema of delete_wa_template_by_id tool."""
    tools = await direct_api_mcp_client.list_tools()

    target_tool = next(
        (t for t in tools if t.name == "delete_wa_template_by_id"), None
    )

    assert target_tool is not None, "Tool not found"

    print("\n" + "=" * 80)
    print("TOOL SCHEMA FOR: delete_wa_template_by_id")
    print("=" * 80)
    print(f"Name: {target_tool.name}")
    print(f"\nDescription: {target_tool.description}")
    print(f"\nInput Schema:")
    print(json.dumps(target_tool.inputSchema, indent=2))
    print("=" * 80)


@pytest.mark.parametrize(
    "template_id, template_name, expected_success, test_description",
    [
        # Valid test case - actual template to delete
        (
            "858447980512648",
            "computer_lectures",
            True,
            "Delete actual template: computer_lectures"
        ),
        # Invalid test case - example from model (likely doesn't exist)

    ],
)
@pytest.mark.asyncio
async def test_delete_template_by_id(
    template_id: str,
    template_name: str,
    expected_success: bool,
    test_description: str,
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Test deleting a WhatsApp template by ID and name.

    The tool fetches the JWT token from TempMemory,
    then calls the Direct API to delete the specified template.

    Args:
        template_id: Template ID to delete
        template_name: Template name to delete
        expected_success: Whether this test case should succeed
        test_description: Description of what this test validates
    """
    print(f"\n{'=' * 80}")
    print(f"Testing delete_wa_template_by_id")
    print(f"Test: {test_description}")
    print(f"  - template_id: {template_id}")
    print(f"  - template_name: {template_name}")
    print(f"  - expected_success: {expected_success}")
    print(f"{'=' * 80}")

    # Call the tool
    result = await direct_api_mcp_client.call_tool(
        "delete_wa_template_by_id",
        arguments={
            "template_id": template_id,
            "template_name": template_name
        },
    )

    print(f"\n=== Result ===")
    print(json.dumps(result.data, indent=2))

    # Assertions
    assert result.data is not None, "Result should not be None"
    assert isinstance(result.data, dict), "Result should be a dictionary"
    assert "success" in result.data, "Result should contain 'success' field"

    if expected_success:
        assert result.data["success"] is True, \
            f"Expected success but got failure: {result.data.get('error', 'Unknown error')}"
        
        # Verify deletion confirmation
        response_data = result.data.get("data", result.data)
        
        # Check for deletion confirmation message
        if "message" in response_data:
            print(f"\n✓ Deletion message: {response_data['message']}")
        
        if "deleted" in response_data or "success" in response_data:
            print(f"✓ Template {template_id} ({template_name}) successfully deleted")
        
        print(f"✓ Test passed: {test_description}")
        
    else:
        assert result.data["success"] is False, \
            f"Expected failure but got success: {result.data}"
        
        assert "error" in result.data, \
            "Failed response should contain 'error' field"
        
        error_message = result.data.get("error", "Unknown error")
        details = result.data.get("details", "")
        
        print(f"\n✓ Test correctly failed with error: {error_message}")
        
