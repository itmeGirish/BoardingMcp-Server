import pytest
import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport

@pytest_asyncio.fixture
async def main_mcp_client():
    async with Client("http://localhost:9001/mcp") as mcp_client:
        yield mcp_client


@pytest.mark.parametrize(
    "user_id",
    [
        "user_886182",  # User ID - business_id and project_id are fetched from database
    ],
)
@pytest.mark.asyncio
async def test_get_kyc_submission(user_id: str, main_mcp_client: Client[FastMCPTransport]):
    """Test retrieving the KYC submission status.

    The tool automatically fetches business_id and project_id from the database
    based on the provided user_id.
    """

    # First, list available tools
    tools = await main_mcp_client.list_tools()
    print("\n=== Available Tools ===")
    for tool in tools:
        print(f"- {tool.name}")

    # Then call the tool with user_id - business_id and project_id are fetched from database
    result = await main_mcp_client.call_tool(
        "get_kyc_submission_status",
        arguments={"user_id": user_id}  # Only user_id needed
    )
    print(f"\n=== Result for user_id: {user_id} ===")
    print(result.data)

    # Add assertions
    assert result.data is not None
 