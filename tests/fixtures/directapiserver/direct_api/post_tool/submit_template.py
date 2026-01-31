import pytest
import pytest_asyncio
import json
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from typing_extensions import List


@pytest_asyncio.fixture
async def direct_api_mcp_client():
    """Initialize MCP client for direct API server."""
    async with Client("http://127.0.0.1:9002/mcp") as mcp_client:
        yield mcp_client


# @pytest.mark.asyncio
# async def test_submit_message_template(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Inspect the schema of submit_whatsapp_template_message tool."""
#     tools = await direct_api_mcp_client.list_tools()

#     print(tools)
    
#     target_tool = next(
#         (t for t in tools if t.name == "submit_whatsapp_template_message"), None
#     )
    
#     assert target_tool is not None, "Tool not found"
    
#     print("\n" + "="*80)
#     print("TOOL SCHEMA FOR: submit_whatsapp_template_message")
#     print("="*80)
#     print(f"Name: {target_tool.name}")
#     print(f"\nDescription: {target_tool.description}")
#     print(f"\nInput Schema:")
#     print(json.dumps(target_tool.inputSchema, indent=2))
#     print("="*80)


# @pytest.mark.parametrize(
#     "user_id,name,category,language,components,expected_success",
#     [
#         (
#             "user1",
#             "order_confirmation_v1",
#             "UTILITY",
#             "en",
#             [
#                 {
#                     "type": "BODY",
#                     "text": "Hi {{1}}, your order {{2}} has been confirmed! It will be delivered by {{3}}. Total amount is {{4}}. Thank you for shopping with us.",
#                     "example": {
#                         "body_text": [
#                             ["Rahul", "ORD12345", "Feb 5, 2026", "Rs 2,499"]
#                         ]
#                     }
#                 },
#                 {
#                     "type": "BUTTONS",
#                     "buttons": [
#                         {
#                             "type": "URL",
#                             "text": "Track Order",
#                             "url": "https://yourstore.com/track/{{1}}",
#                             "example": ["https://yourstore.com/track/ORD12345"]
#                         },
#                         {
#                             "type": "PHONE_NUMBER",
#                             "text": "Contact Support",
#                             "phone_number": "918861832522"
#                         }
#                     ]
#                 },
#                 {
#                     "type": "FOOTER",
#                     "text": "We appreciate your business"
#                 }
#             ],
#             True
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_submit_order_confirmation_template(
#     user_id: str,
#     name: str,
#     category: str,
#     language: str,
#     components: list[dict],
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test submitting a simple order confirmation WhatsApp template."""
    
#     print(f"\n{'='*80}")
#     print(f"Testing Template: {name}")
#     print(f"User ID: {user_id}")
#     print(f"Category: {category}")
#     print(f"Language: {language}")
#     print(f"{'='*80}")
    
#     # Call the tool with user_id included
#     result = await direct_api_mcp_client.call_tool(
#         "submit_whatsapp_template_message",
#         arguments={
#             "user_id": user_id,
#             "name": name,
#             "category": category,
#             "language": language,
#             "components": components
#         },
#     )
    
#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     # Assertions
#     assert result.data is not None, "Result should not be None"
#     assert isinstance(result.data, dict), "Result should be a dictionary"
#     assert "success" in result.data, "Result should contain 'success' field"
#     assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"
#     assert "data" in result.data, "Successful response should contain 'data' field"
    
#     print(f"\n✅ Template submitted successfully!")


# @pytest.mark.parametrize(
#     "user_id,name,category,language,components,expected_success",
#     [
#         (
#             "user1",
#             "order_confirmation",
#             "UTILITY",
#             "en",
#             [
#                 {
#                     "type": "HEADER",
#                     "format": "TEXT",
#                     "text": "Order Confirmed"
#                 },
#                 {
#                     "type": "BODY",
#                     "text": "Hello {{1}},\n\nThank you for your order! Your order number {{2}} has been successfully confirmed and is being processed.\n\nWe will notify you once your package is shipped. Expected delivery date is {{3}}.\n\nIf you have any questions, please feel free to contact our support team.",
#                     "example": {
#                         "body_text": [
#                             ["John Doe", "ORD-12345", "February 5, 2026"]
#                         ]
#                     }
#                 },
#                 {
#                     "type": "BUTTONS",
#                     "buttons": [
#                         {
#                             "type": "URL",
#                             "text": "Track Order",
#                             "url": "https://aisensy.com/track/{{1}}",
#                             "example": ["ORD-12345"]
#                         },
#                         {
#                             "type": "PHONE_NUMBER",
#                             "text": "Call Support",
#                             "phone_number": "919177604610"
#                         }
#                     ]
#                 },
#                 {
#                     "type": "FOOTER",
#                     "text": "Thank you for shopping with us"
#                 }
#             ],
#             True
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_submit_utility_template(
#     user_id: str,
#     name: str,
#     category: str,
#     language: str,
#     components: list[dict],
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test submitting a WhatsApp UTILITY template for order confirmation."""
    
#     print(f"\n{'='*80}")
#     print(f"Testing UTILITY Template: {name}")
#     print(f"User ID: {user_id}")
#     print(f"Category: {category}")
#     print(f"Language: {language}")
#     print(f"{'='*80}")
    
#     # Call the tool with user_id included
#     result = await direct_api_mcp_client.call_tool(
#         "submit_whatsapp_template_message",
#         arguments={
#             "user_id": user_id,
#             "name": name,
#             "category": category,
#             "language": language,
#             "components": components
#         },
#     )
    
#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     # Assertions
#     assert result.data is not None, "Result should not be None"
#     assert isinstance(result.data, dict), "Result should be a dictionary"
#     assert "success" in result.data, "Result should contain 'success' field"
#     assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"
#     assert "data" in result.data, "Successful response should contain 'data' field"
    
#     print(f"\n✅ UTILITY template submitted successfully!")




# @pytest.mark.parametrize(
#     "user_id,name,category,language,components,expected_success",
#     [
#         (
#             "user1",
#             "survey_invitation",
#             "UTILITY",
#             "en",
#             [
#                 {
#                     "type": "BODY",
#                     "text": "Hello {{1}}, thank you for participating in our research study. Your survey is now ready and will take approximately {{2}} minutes to complete. Your responses are confidential and will help us improve our services. Please complete the survey by {{3}} to ensure your feedback is included.",
#                     "example": {
#                         "body_text": [
#                             ["Dr. Michael Chen", "15", "February 15, 2026"]
#                         ]
#                     }
#                 },
#                 {
#                     "type": "BUTTONS",
#                     "buttons": [
#                         {
#                             "type": "URL",
#                             "text": "Start Survey",
#                             "url": "https://aisensy.com/survey/{{1}}",
#                             "example": ["SRV-2026-001"]
#                         }
#                     ]
#                 },
#                 {
#                     "type": "FOOTER",
#                     "text": "Your privacy is important to us"
#                 }
#             ],
#             True
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_submit_utility_template(
#     user_id: str,
#     name: str,
#     category: str,
#     language: str,
#     components: list[dict],
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test submitting a WhatsApp UTILITY template for research survey invitation."""
    
#     print(f"\n{'='*80}")
#     print(f"Testing UTILITY Template: {name}")
#     print(f"User ID: {user_id}")
#     print(f"Category: {category}")
#     print(f"Language: {language}")
#     print(f"{'='*80}")
    
#     # Call the tool with user_id included
#     result = await direct_api_mcp_client.call_tool(
#         "submit_whatsapp_template_message",
#         arguments={
#             "user_id": user_id,
#             "name": name,
#             "category": category,
#             "language": language,
#             "components": components
#         },
#     )
    
#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     # Assertions
#     assert result.data is not None, "Result should not be None"
#     assert isinstance(result.data, dict), "Result should be a dictionary"
#     assert "success" in result.data, "Result should contain 'success' field"
#     assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"
#     assert "data" in result.data, "Successful response should contain 'data' field"
    
#     print(f"\n✅ UTILITY template submitted successfully!")




#file 
# @pytest.mark.parametrize(
#     "user_id,name,category,language,components,expected_success",
#     [
#         (
#             "user1",
#             "books_list",
#             "UTILITY",
#             "en",
#             [
#                 {
#                     "type": "HEADER",
#                     "format": "DOCUMENT",
#                     "example": {
#                         "header_handle": [
#                             "https://www.mha.gov.in/sites/default/files/250883_english_01042024.pdf"
#                         ]
#                     }
#                 },
#                 {
#                     "type": "BODY",
#                     "text": "Hello dear Mr. {{1}}, please download the available book list from below:",
#                     "example": {
#                         "body_text": [
#                             ["Virat"]
#                         ]
#                     }
#                 },
#                 {
#                     "type": "BUTTONS",
#                     "buttons": [
#                         {
#                             "type": "PHONE_NUMBER",
#                             "text": "Contact Us",
#                             "phone_number": "917089379345"
#                         },
#                         {
#                             "type": "URL",
#                             "text": "Visit Us",
#                             "url": "https://yoursite.com"
#                         }
#                     ]
#                 },
#                 {
#                     "type": "FOOTER",
#                     "text": "Reach out to us at 12/1 ABC"
#                 }
#             ],
#             True
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_submit_utility_template(
#     user_id: str,
#     name: str,
#     category: str,
#     language: str,
#     components: list[dict],
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test submitting a WhatsApp UTILITY template with document header."""
    
#     print(f"\n{'='*80}")
#     print(f"Testing UTILITY Template: {name}")
#     print(f"User ID: {user_id}")
#     print(f"Category: {category}")
#     print(f"Language: {language}")
#     print(f"{'='*80}")
    
#     # Call the tool with user_id included
#     result = await direct_api_mcp_client.call_tool(
#         "submit_whatsapp_template_message",
#         arguments={
#             "user_id": user_id,
#             "name": name,
#             "category": category,
#             "language": language,
#             "components": components
#         },
#     )
    
#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     # Assertions
#     assert result.data is not None, "Result should not be None"
#     assert isinstance(result.data, dict), "Result should be a dictionary"
#     assert "success" in result.data, "Result should contain 'success' field"
#     assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"
#     assert "data" in result.data, "Successful response should contain 'data' field"
    
#     print(f"\n✅ UTILITY template submitted successfully!")



# @pytest.mark.parametrize(
#     "user_id,name,category,language,components,expected_success",
#     [
#         (
#             "user1",
#             "computer_lectures",
#             "UTILITY",
#             "en",
#             [
#                 {
#                     "type": "HEADER",
#                     "format": "VIDEO",
#                     "example": {
#                         "header_handle": [
#                             "https://aisensy-project-media-library-stg.s3.ap-south-1.amazonaws.com/VIDEO/6245d025fcb7966c46294618/6334744_6467606fileexampleMP448015MG.mp4"
#                         ]
#                     }
#                 },
#                 {
#                     "type": "BODY",
#                     "text": "Hello dear Mr. {{1}}, please find the lectures for this semester below:",
#                     "example": {
#                         "body_text": [
#                             ["Rohit"]
#                         ]
#                     }
#                 },
#                 {
#                     "type": "BUTTONS",
#                     "buttons": [
#                         {
#                             "type": "PHONE_NUMBER",
#                             "text": "Contact Us",
#                             "phone_number": "917089379345"
#                         },
#                         {
#                             "type": "URL",
#                             "text": "Visit Us",
#                             "url": "https://yoursite.com"
#                         }
#                     ]
#                 },
#                 {
#                     "type": "FOOTER",
#                     "text": "Content is subject to change."
#                 }
#             ],
#             True
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_submit_utility_template(
#     user_id: str,
#     name: str,
#     category: str,
#     language: str,
#     components: list[dict],
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test submitting a WhatsApp UTILITY template with video header."""
    
#     print(f"\n{'='*80}")
#     print(f"Testing UTILITY Template: {name}")
#     print(f"User ID: {user_id}")
#     print(f"Category: {category}")
#     print(f"Language: {language}")
#     print(f"{'='*80}")
    
#     # Call the tool with user_id included
#     result = await direct_api_mcp_client.call_tool(
#         "submit_whatsapp_template_message",
#         arguments={
#             "user_id": user_id,
#             "name": name,
#             "category": category,
#             "language": language,
#             "components": components
#         },
#     )
    
#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     # Assertions
#     assert result.data is not None, "Result should not be None"
#     assert isinstance(result.data, dict), "Result should be a dictionary"
#     assert "success" in result.data, "Result should contain 'success' field"
#     assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"
#     assert "data" in result.data, "Successful response should contain 'data' field"
    
#     print(f"\n✅ UTILITY template submitted successfully!")



# @pytest.mark.parametrize(
#     "user_id,name,category,language,components,expected_success",
#     [
#         (
#             "user1",
#             "summer_carousel_promo_2023_7",
#             "MARKETING",
#             "en",
#             [
#                 {
#                     "type": "BODY",
#                     "text": "Summer is here, and we have the freshest produce around! Use code {{1}} to get {{2}} off your next order.",
#                     "example": {
#                         "body_text": [
#                             [
#                                 "15OFF",
#                                 "15%"
#                             ]
#                         ]
#                     }
#                 },
#                 {
#                     "type": "CAROUSEL",
#                     "cards": [
#                         {
#                             "components": [
#                                 {
#                                     "type": "HEADER",
#                                     "format": "IMAGE",
#                                     "example": {
#                                         "header_handle": [
#                                             "https://images.unsplash.com/photo-1596181525841-8e8bae173eb0?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=3087&q=80"
#                                         ]
#                                     }
#                                 },
#                                 {
#                                     "type": "BODY",
#                                     "text": "Rare lemons for unique cocktails. Use code {{1}} to get {{2}} off all produce.",
#                                     "example": {
#                                         "body_text": [
#                                             [
#                                                 "15OFF",
#                                                 "15%"
#                                             ]
#                                         ]
#                                     }
#                                 },
#                                 {
#                                     "type": "BUTTONS",
#                                     "buttons": [
#                                         {
#                                             "type": "QUICK_REPLY",
#                                             "text": "Get Lemons"
#                                         },
#                                         {
#                                             "type": "URL",
#                                             "text": "Buy now",
#                                             "url": "https://www.luckyshrub.com/shop?promo={{1}}",
#                                             "example": [
#                                                 "https://www.luckyshrub.com/shop?promo=exotic_produce_2023"
#                                             ]
#                                         }
#                                     ]
#                                 }
#                             ]
#                         },
#                         {
#                             "components": [
#                                 {
#                                     "type": "HEADER",
#                                     "format": "IMAGE",
#                                     "example": {
#                                         "header_handle": [
#                                             "https://images.unsplash.com/photo-1596404643764-2a2461483a3b?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2864&q=80"
#                                         ]
#                                     }
#                                 },
#                                 {
#                                     "type": "BODY",
#                                     "text": "Exotic fruit for unique cocktails! Use code {{1}} to get {{2}} off all exotic produce.",
#                                     "example": {
#                                         "body_text": [
#                                             [
#                                                 "20OFFEXOTIC",
#                                                 "20%"
#                                             ]
#                                         ]
#                                     }
#                                 },
#                                 {
#                                     "type": "BUTTONS",
#                                     "buttons": [
#                                         {
#                                             "type": "QUICK_REPLY",
#                                             "text": "Get Lemons"
#                                         },
#                                         {
#                                             "type": "URL",
#                                             "text": "Buy now",
#                                             "url": "https://www.luckyshrub.com/shop?promo={{1}}",
#                                             "example": [
#                                                 "https://www.luckyshrub.com/shop?promo=exotic_produce_2023"
#                                             ]
#                                         }
#                                     ]
#                                 }
#                             ]
#                         }
#                     ]
#                 }
#             ],
#             True
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_submit_marketing_carousel_template(
#     user_id: str,
#     name: str,
#     category: str,
#     language: str,
#     components: list[dict],
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test submitting a WhatsApp MARKETING carousel template with multiple cards."""
    
#     print(f"\n{'='*80}")
#     print(f"Testing MARKETING Carousel Template: {name}")
#     print(f"User ID: {user_id}")
#     print(f"Category: {category}")
#     print(f"Language: {language}")
#     print(f"{'='*80}")
    
#     # Call the tool with user_id included
#     result = await direct_api_mcp_client.call_tool(
#         "submit_whatsapp_template_message",
#         arguments={
#             "user_id": user_id,
#             "name": name,
#             "category": category,
#             "language": language,
#             "components": components
#         },
#     )
    
#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     # Assertions
#     assert result.data is not None, "Result should not be None"
#     assert isinstance(result.data, dict), "Result should be a dictionary"
#     assert "success" in result.data, "Result should contain 'success' field"
#     assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"
#     assert "data" in result.data, "Successful response should contain 'data' field"
    
#     print(f"\n✅ MARKETING carousel template submitted successfully!")





#flow template
# @pytest.mark.parametrize(
#     "user_id,name,category,language,components,expected_success",
#     [
#         (
#             "user1",
#             "flow_template",
#             "MARKETING",
#             "en",
#             [
#                 {
#                     "type": "BODY",
#                     "text": "My first flow template!"
#                 },
#                 {
#                     "type": "BUTTONS",
#                     "buttons": [
#                         {
#                             "type": "FLOW",
#                             "text": "Open flow!",
#                             "flow_id": "1354795268451905",
#                             "navigate_screen": "DEMO_SCREEN",
#                             "flow_action": "navigate"
#                         }
#                     ]
#                 }
#             ],
#             True,
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_submit_marketing_flow_template(
#     user_id: str,
#     name: str,
#     category: str,
#     language: str,
#     components: list[dict],
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test submitting a WhatsApp MARKETING Flow template."""

#     print(f"\n{'='*80}")
#     print(f"Testing MARKETING Flow Template: {name}")
#     print(f"User ID: {user_id}")
#     print(f"Category: {category}")
#     print(f"Language: {language}")
#     print(f"{'='*80}")

#     # Call MCP tool
#     result = await direct_api_mcp_client.call_tool(
#         "submit_whatsapp_template_message",
#         arguments={
#             "user_id": user_id,
#             "name": name,
#             "category": category,
#             "language": language,
#             "components": components,
#         },
#     )

#     print("\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     # Assertions
#     assert result.data is not None, "Result should not be None"
#     assert isinstance(result.data, dict), "Result should be a dictionary"
#     assert "success" in result.data, "Result should contain 'success'"
#     assert result.data["success"] is expected_success, (
#         f"Expected success={expected_success} but got error: "
#         f"{result.data.get('error')}"
#     )

#     if expected_success:
#         assert "data" in result.data, "Successful response should contain 'data'"

#     print("\n✅ MARKETING flow template submitted successfully!")


#multi Button template




# @pytest.mark.parametrize(
#     "user_id,name,category,language,components,expected_success",
#     [
#         (
#             "user1",
#             "multi_button_template",
#             "MARKETING",
#             "en",
#             [
#                 {
#                     "type": "BODY",
#                     "text": "Hello dear Mr. {{1}},to resolve your issue please connect with us",
#                     "example": {
#                         "body_text": [
#                             [
#                                 "Saurabh"
#                             ]
#                         ]
#                     }
#                 },
#                 {
#                     "type": "BUTTONS",
#                     "buttons": [
#                         {
#                             "type": "PHONE_NUMBER",
#                             "text": "Call Us",
#                             "phone_number": "917889379345"
#                         },
#                         {
#                             "type": "URL",
#                             "text": "Connect on web",
#                             "url": "https://yoursite.com/{{1}}",
#                             "example": [
#                                 "https://www.yoursite.com/dynamic-url-example"
#                             ]
#                         },
#                         {
#                             "type": "QUICK_REPLY",
#                             "text": "Renew Membership"
#                         },
#                         {
#                             "type": "QUICK_REPLY",
#                             "text": "Cancel Membership"
#                         }
#                     ]
#                 }
#             ],
#             True,
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_submit_marketing_multi_button_template(
#     user_id: str,
#     name: str,
#     category: str,
#     language: str,
#     components: list[dict],
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test submitting a WhatsApp MARKETING template with multiple button types."""

#     print(f"\n{'='*80}")
#     print(f"Testing MARKETING Multi-Button Template: {name}")
#     print(f"User ID: {user_id}")
#     print(f"Category: {category}")
#     print(f"Language: {language}")
#     print(f"{'='*80}")

#     # Call MCP tool
#     result = await direct_api_mcp_client.call_tool(
#         "submit_whatsapp_template_message",
#         arguments={
#             "user_id": user_id,
#             "name": name,
#             "category": category,
#             "language": language,
#             "components": components,
#         },
#     )

#     print("\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     # Assertions
#     assert result.data is not None, "Result should not be None"
#     assert isinstance(result.data, dict), "Result should be a dictionary"
#     assert "success" in result.data, "Result should contain 'success' field"
#     assert result.data["success"] is expected_success, (
#         f"Expected success={expected_success} but got error: "
#         f"{result.data.get('error')}"
#     )

#     if expected_success:
#         assert "data" in result.data, "Successful response should contain 'data'"

#     print("\n✅ MARKETING multi-button template submitted successfully!")


#Limited offer
# @pytest.mark.parametrize(
#     "user_id,name,category,language,components,expected_success",
#     [
#         (
#             "user1",
#             "limited_time_offer_tem_2",
#             "MARKETING",
#             "en",
#             [
#                 {
#                     "type": "HEADER",
#                     "format": "IMAGE",
#                     "example": {
#                         "header_handle": [
#                             "https://images.unsplash.com/photo-1596181525841-8e8bae173eb0"
#                         ]
#                     }
#                 },
#                 {
#                     "type": "LIMITED_TIME_OFFER",
#                     "limited_time_offer": {
#                         "text": "Expiring {{1}}!",
#                         "has_expiration": False
#                     }
#                 },
#                 {
#                     "type": "BODY",
#                     "text": "Good news, {{1}}! Use code {{2}} to get 25% off on all plans!",
#                     "example": {
#                         "body_text": [
#                             [
#                                 "Preeti",
#                                 "PR25"
#                             ]
#                         ]
#                     }
#                 },
#                 {
#                     "type": "BUTTONS",
#                     "buttons": [
#                         {
#                             "type": "COPY_CODE",
#                             "example": "CARIBE25"
#                         },
#                         {
#                             "type": "URL",
#                             "text": "Book now!",
#                             "url": "https://aisensy.com/offers?code={{1}}",
#                             "example": [
#                                 "https://aisensy.com/offers?code=n3mtql"
#                             ]
#                         }
#                     ]
#                 }
#             ],
#             True,
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_submit_marketing_limited_time_offer_template(
#     user_id: str,
#     name: str,
#     category: str,
#     language: str,
#     components: List[dict],
#     expected_success: bool,
#     direct_api_mcp_client,
# ):
#     """Test submitting a WhatsApp MARKETING limited time offer template."""

#     print(f"\n{'='*80}")
#     print(f"Testing MARKETING Limited Time Offer Template: {name}")
#     print(f"User ID: {user_id}")
#     print(f"Category: {category}")
#     print(f"Language: {language}")
#     print(f"{'='*80}")

#     result = await direct_api_mcp_client.call_tool(
#         "submit_whatsapp_template_message",
#         arguments={
#             "user_id": user_id,
#             "name": name,
#             "category": category,
#             "language": language,
#             "components": components,
#         },
#     )

#     print("\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     # Assertions
#     assert result.data is not None
#     assert isinstance(result.data, dict)
#     assert "success" in result.data
#     assert result.data["success"] is expected_success, (
#         f"Expected success={expected_success} but got error: "
#         f"{result.data.get('error')}"
#     )

#     if expected_success:
#         assert "data" in result.data

#     print("\n✅ MARKETING limited time offer template submitted successfully!")






#authentication

@pytest.mark.parametrize(
    "user_id,name,category,language,components,expected_success",
    [
        (
            "user1",
            "my_auth_template",
            "AUTHENTICATION",
            "en",
            [
                {
                    "type": "BODY"
                },
                {
                    "type": "BUTTONS",
                    "buttons": [
                        {
                            "type": "OTP",
                            "otp_type": "COPY_CODE",
                            "text": "COPY CODE"
                        }
                    ]
                }
            ],
            True,
        ),
    ],
)
@pytest.mark.asyncio
async def test_submit_authentication_otp_template(
    user_id: str,
    name: str,
    category: str,
    language: str,
    components: List[dict],
    expected_success: bool,
    direct_api_mcp_client,
):
    """Test submitting a WhatsApp AUTHENTICATION template with OTP copy code button."""

    print(f"\n{'='*80}")
    print(f"Testing AUTHENTICATION OTP Template: {name}")
    print(f"User ID: {user_id}")
    print(f"Category: {category}")
    print(f"Language: {language}")
    print(f"{'='*80}")

    result = await direct_api_mcp_client.call_tool(
        "submit_whatsapp_template_message",
        arguments={
            "user_id": user_id,
            "name": name,
            "category": category,
            "language": language,
            "components": components,
        },
    )

    print("\n=== Result ===")
    print(json.dumps(result.data, indent=2))

    # Assertions
    assert result.data is not None
    assert isinstance(result.data, dict)
    assert "success" in result.data
    assert result.data["success"] is expected_success, (
        f"Expected success={expected_success} but got error: "
        f"{result.data.get('error')}"
    )

    if expected_success:
        assert "data" in result.data

    print("\n✅ AUTHENTICATION OTP template submitted successfully!")
