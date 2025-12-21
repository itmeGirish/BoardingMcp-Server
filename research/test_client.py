import asyncio
from fastmcp import Client

# Point to the server file
client = Client("mcp_servers/direct_api_server.py")


async def main():
    async with client:
        # Ping server
        await client.ping()
        print("✅ Server is alive")

        # List tools
        tools = await client.list_tools()
        print("🛠 Tools:", tools)

        # List resources
        resources = await client.list_resources()
        print("📦 Resources:", resources)

        # List prompts
        prompts = await client.list_prompts()
        print("💬 Prompts:", prompts)

        
asyncio.run(main())
