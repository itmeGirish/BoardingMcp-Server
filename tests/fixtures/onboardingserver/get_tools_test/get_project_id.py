import pytest
import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport

@pytest_asyncio.fixture
async def main_mcp_client():
    async with Client("mcp_servers/onboardserver.py") as mcp_client:
        yield mcp_client

@pytest.mark.parametrize(
    "project_id",
    [
        "6798e0ab6c6d490c0e356d1d",  # Full project ID from your earlier output
    ],
)
@pytest.mark.asyncio
async def test_get_project_by_id(project_id: str, main_mcp_client: Client[FastMCPTransport]):
    """Test retrieving the project by id"""
    
    # First, list available tools
    tools = await main_mcp_client.list_tools()
    print("\n=== Available Tools ===")
    for tool in tools:
        print(f"- {tool.name}")
    
    # Then call the tool with proper argument format
    result = await main_mcp_client.call_tool(
        "get_project_by_id", 
        arguments={"project_id": project_id}  # Pass as dictionary
    )
    print(f"\n=== Result for project_id: {project_id} ===")
    print(result.data)
    

   