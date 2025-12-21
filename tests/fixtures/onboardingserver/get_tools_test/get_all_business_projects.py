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
        "6798e0ab6c6d490c0e356d1d"
    ],
)
@pytest.mark.asyncio
async def test_get_project_by_id(project_id: str, main_mcp_client: Client[FastMCPTransport]):
    """Test retrieving a specific project by ID."""
    
    result = await main_mcp_client.call_tool(
        "get_project_by_id",
        arguments={"project_id": project_id}
    )
    print(f"\n=== Project {project_id} ===")
    print(result.data)
    
    # Add assertions
