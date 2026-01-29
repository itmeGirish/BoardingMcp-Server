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
async def test_submit_message_template(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Inspect the schema of submit_whatsapp_template_message tool."""
    tools = await direct_api_mcp_client.list_tools()

    print(tools)
    
    target_tool = next(
        (t for t in tools if t.name == "submit_whatsapp_template_message"), None
    )
    
    assert target_tool is not None, "Tool not found"
    
    print("\n" + "="*80)
    print("TOOL SCHEMA FOR: submit_whatsapp_template_message")
    print("="*80)
    print(f"Name: {target_tool.name}")
    print(f"\nDescription: {target_tool.description}")
    print(f"\nInput Schema:")
    print(json.dumps(target_tool.inputSchema, indent=2))
    print("="*80)


@pytest.mark.parametrize(
    "user_id,name,category,language,components,expected_success",
    [
        (
            "user1",
            "order_confirmation_v1",
            "UTILITY",
            "en",
            [
                {
                    "type": "BODY",
                    "text": "Hi {{1}}, your order {{2}} has been confirmed! It will be delivered by {{3}}. Total amount is {{4}}. Thank you for shopping with us.",
                    "example": {
                        "body_text": [
                            ["Rahul", "ORD12345", "Feb 5, 2026", "Rs 2,499"]
                        ]
                    }
                },
                {
                    "type": "BUTTONS",
                    "buttons": [
                        {
                            "type": "URL",
                            "text": "Track Order",
                            "url": "https://yourstore.com/track/{{1}}",
                            "example": ["https://yourstore.com/track/ORD12345"]
                        },
                        {
                            "type": "PHONE_NUMBER",
                            "text": "Contact Support",
                            "phone_number": "918861832522"
                        }
                    ]
                },
                {
                    "type": "FOOTER",
                    "text": "We appreciate your business"
                }
            ],
            True
        ),
    ],
)
@pytest.mark.asyncio
async def test_submit_order_confirmation_template(
    user_id: str,
    name: str,
    category: str,
    language: str,
    components: list[dict],
    expected_success: bool,
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Test submitting a simple order confirmation WhatsApp template."""
    
    print(f"\n{'='*80}")
    print(f"Testing Template: {name}")
    print(f"User ID: {user_id}")
    print(f"Category: {category}")
    print(f"Language: {language}")
    print(f"{'='*80}")
    
    # Call the tool with user_id included
    result = await direct_api_mcp_client.call_tool(
        "submit_whatsapp_template_message",
        arguments={
            "user_id": user_id,
            "name": name,
            "category": category,
            "language": language,
            "components": components
        },
    )
    
    print(f"\n=== Result ===")
    print(json.dumps(result.data, indent=2))

    # Assertions
    assert result.data is not None, "Result should not be None"
    assert isinstance(result.data, dict), "Result should be a dictionary"
    assert "success" in result.data, "Result should contain 'success' field"
    assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"
    assert "data" in result.data, "Successful response should contain 'data' field"
    
    print(f"\n✅ Template submitted successfully!")