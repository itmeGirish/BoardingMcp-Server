"""
main.py - Auto-generated
Implement your logic here
"""

from fastmcp import Client
import asyncio

async def main():
    # The client will automatically handle Google OAuth
    async with Client("http://localhost:8000/mcp", auth="oauth") as client:
        # First-time connection will open Google login in your browser
        print("✓ Authenticated with Google!")
        
        # Test the protected tool
        result = await client.call_tool("get_user_info")
        
        # Access the content from the CallToolResult object
        user_info = result.content[0].text if result.content else None
        
        # If the result is JSON string, parse it
        if user_info:
            import json
            data = json.loads(user_info)
            print(f"Google user: {data['email']}")
            print(f"Name: {data['name']}")
        else:
            print(f"Raw result: {result}")

if __name__ == "__main__":
    asyncio.run(main())