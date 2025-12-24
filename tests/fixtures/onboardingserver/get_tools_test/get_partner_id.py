import pytest
import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport

@pytest_asyncio.fixture
async def main_mcp_client():
    async with Client("mcp_servers/onboardserver.py") as mcp_client:
        yield mcp_client


@pytest.mark.asyncio
async def test_get_all_business_profiles(main_mcp_client: Client[FastMCPTransport]):
    """Test retrieving the partner_details"""
    
    # First, list available tools
    tools = await main_mcp_client.list_tools()
    print("\n=== Available Tools ===")
    for tool in tools:
        print(f"- {tool.name}")
    
    # Then call the tool
    result = await main_mcp_client.call_tool("get_partner_details", arguments={})
    print("\n=== Result ===")
    print(result.data)
   
    