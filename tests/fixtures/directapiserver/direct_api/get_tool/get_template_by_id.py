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
async def test_get_template_by_id(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Inspect the template by id."""
    tools = await direct_api_mcp_client.list_tools()

    target_tool = next(
        (t for t in tools if t.name == "get_template_by_id"), None
    )

    assert target_tool is not None, "Tool not found"

    print("\n" + "=" * 80)
    print("TOOL SCHEMA FOR: get_template_by_id")
    print("=" * 80)
    print(f"Name: {target_tool.name}")
    print(f"\nDescription: {target_tool.description}")
    print(f"\nInput Schema:")
    print(json.dumps(target_tool.inputSchema, indent=2))
    print("=" * 80)


import pytest
import json

@pytest.mark.parametrize(
    "user_id,template_id,expected_success",
    [
        # PDF file
        ("user1", "1459452276191331", True),  # utility: pending (pdf)

        # # Video file
        # ("user1", "2502204860182652", True),  # UTILITY: video

        # # Carousel file
        # ("user1", "2285632275274849", True),  # MARKETING: carousel

        # # Flow template
        # ("user1", "25847459641586526", True),  # MARKETING: flow

        # # Multi-Button Template
        # ("user1", "1398730445602939", True),  # MARKETING: multi-button

        # # Limited-time offer
        # ("user1", "1424476949274088", True),  # MARKETING: offer

        # # Authentication template
        # ("user1", "1260203929348523", True),  # AUTHENTICATION
    ],
)
@pytest.mark.asyncio
async def test_get_template_by_id(
    user_id: str,
    template_id: str,
    expected_success: bool,
    direct_api_mcp_client,
):
    """Test fetching template by template_id."""

    print(f"\n{'=' * 80}")
    print("Testing get_template_by_id")
    print(f"  - user_id: {user_id}")
    print(f"  - template_id: {template_id}")
    print(f"  - expected_success: {expected_success}")
    print(f"{'=' * 80}")

    result = await direct_api_mcp_client.call_tool(
        "get_template_by_id",
        arguments={
            "user_id": user_id,
            "template_id": template_id,
        },
    )

    print("\n=== Result ===")
    print(json.dumps(result.data, indent=2))

    assert result.data is not None, "Result should not be None"
    assert isinstance(result.data, dict), "Result should be a dictionary"
    assert "success" in result.data, "Result should contain 'success' field"

    if expected_success:
        assert result.data["success"] is True, (
            f"Expected success but got error: {result.data.get('error')}"
        )
    else:
        assert result.data["success"] is False, "Expected failure but got success"
        assert "error" in result.data, "Failed response should contain 'error' field"




