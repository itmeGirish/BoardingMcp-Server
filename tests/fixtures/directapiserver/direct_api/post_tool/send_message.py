"""Tests for send_message POST endpoint via MCP."""

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
async def test_inspect_send_message_schema(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Inspect the schema of send_message tool."""
    tools = await direct_api_mcp_client.list_tools()

    target_tool = next(
        (t for t in tools if t.name == "send_message"), None
    )

    assert target_tool is not None, "Tool not found"

    print("\n" + "=" * 80)
    print("TOOL SCHEMA FOR: send_message")
    print("=" * 80)
    print(f"Name: {target_tool.name}")
    print(f"\nDescription: {target_tool.description}")
    print(f"\nInput Schema:")
    print(json.dumps(target_tool.inputSchema, indent=2))
    print("=" * 80)


# ==================== TEXT MESSAGE TESTS ====================


# @pytest.mark.parametrize(
#     "user_id, to, message_type, text_body, expected_success",
#     [
#         ("user1", "918861832522", "text", "who are you?", True),
#     ],
# )
# @pytest.mark.asyncio
# async def test_send_text_message(
#     user_id: str,
#     to: str,
#     message_type: str,
#     text_body: str,
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending a text message.

#     Args:
#         user_id: User ID to fetch JWT token for
#         to: Recipient phone number
#         message_type: Type of message
#         text_body: The message body text
#         expected_success: Whether this test case should succeed
#     """
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (text)")
#     print(f"  - user_id: {user_id}")
#     print(f"  - to: {to}")
#     print(f"  - message_type: {message_type}")
#     print(f"  - text_body: {text_body}")
#     print(f"  - expected_success: {expected_success}")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": user_id,
#             "to": to,
#             "message_type": message_type,
#             "text_body": text_body,
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None, "Result should not be None"
#     assert isinstance(result.data, dict), "Result should be a dictionary"
#     assert "success" in result.data, "Result should contain 'success' field"

#     if expected_success:
#         assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"
#         assert "data" in result.data, "Successful response should contain 'data' field"
#     else:
#         assert result.data["success"] is False, "Expected failure but got success"
#         assert "error" in result.data, "Failed response should contain 'error' field"


# # ==================== IMAGE MESSAGE TESTS ====================


# @pytest.mark.parametrize(
#     "user_id, to, message_type, media_link, media_caption, expected_success",
#     [
#         (
#             "user1",
#             "918861832522",
#             "image",
#             "https://aisensy-project-media-library-stg.s3.ap-south-1.amazonaws.com/IMAGE/6245d025fcb7966c46294618/2699676_babyyoda1.png",
#             "Your image caption here",
#             True,
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_send_image_message(
#     user_id: str,
#     to: str,
#     message_type: str,
#     media_link: str,
#     media_caption: str,
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending an image message."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (image)")
#     print(f"  - to: {to}, media_link: {media_link}")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": user_id,
#             "to": to,
#             "message_type": message_type,
#             "media_link": media_link,
#             "media_caption": media_caption,
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data

#     if expected_success:
#         assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"


# # ==================== VIDEO MESSAGE TESTS ====================


# @pytest.mark.parametrize(
#     "user_id, to, message_type, media_link, media_caption, expected_success",
#     [
#         (
#             "user1",
#             "918861832522",
#             "video",
#             "https://aisensy-project-media-library-stg.s3.ap-south-1.amazonaws.com/VIDEO/6245d025fcb7966c46294618/9346765_6467606fileexampleMP448015MG.mp4",
#             "Your video caption here",
#             True,
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_send_video_message(
#     user_id: str,
#     to: str,
#     message_type: str,
#     media_link: str,
#     media_caption: str,
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending a video message."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (video)")
#     print(f"  - to: {to}, media_link: {media_link}")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": user_id,
#             "to": to,
#             "message_type": message_type,
#             "media_link": media_link,
#             "media_caption": media_caption,
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data

#     if expected_success:
#         assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"


# # ==================== AUDIO MESSAGE TESTS ====================


# @pytest.mark.parametrize(
#     "user_id, to, message_type, media_link, expected_success",
#     [
#         (
#             "user1",
#             "918861832522",
#             "audio",
#             "https://aisensy-project-media-library-stg.s3.ap-south-1.amazonaws.com/AUDIO/6245d025fcb7966c46294618/565346_fileexampleMP3700KB.mp3",
#             True,
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_send_audio_message(
#     user_id: str,
#     to: str,
#     message_type: str,
#     media_link: str,
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending an audio message."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (audio)")
#     print(f"  - to: {to}, media_link: {media_link}")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": user_id,
#             "to": to,
#             "message_type": message_type,
#             "media_link": media_link,
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data

#     if expected_success:
#         assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"


# # ==================== DOCUMENT MESSAGE TESTS ====================


# @pytest.mark.parametrize(
#     "user_id, to, message_type, media_link, media_caption, media_filename, expected_success",
#     [
#         (
#             "user1",
#             "918861832522",
#             "document",
#             "https://aisensy-project-media-library-stg.s3.ap-south-1.amazonaws.com/FILE/6245d025fcb7966c46294618/4233108_sample51843456.jpeg",
#             "Your document caption here",
#             "wds",
#             True,
#         ),
#     ],
# )
# @pytest.mark.asyncio
# async def test_send_document_message(
#     user_id: str,
#     to: str,
#     message_type: str,
#     media_link: str,
#     media_caption: str,
#     media_filename: str,
#     expected_success: bool,
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending a document message."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (document)")
#     print(f"  - to: {to}, filename: {media_filename}")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": user_id,
#             "to": to,
#             "message_type": message_type,
#             "media_link": media_link,
#             "media_caption": media_caption,
#             "media_filename": media_filename,
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data

#     if expected_success:
#         assert result.data["success"] is True, f"Expected success but got: {result.data.get('error')}"


# # ==================== TEMPLATE MESSAGE TESTS ====================


@pytest.mark.asyncio
async def test_send_template_text_message(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Test sending a template text message (e.g., shipping confirmation)."""
    print(f"\n{'=' * 80}")
    print(f"Testing send_message (template - text)")
    print(f"{'=' * 80}")

    result = await direct_api_mcp_client.call_tool(
        "send_message",
        arguments={
            "user_id": "user1",
            "to": "918861832522",
            "message_type": "template",
            "template_name": "sample_shipping_confirmation",
            "template_language_code": "en_us",
            "template_language_policy": "deterministic",
            "template_components":[
      {
        "type": "BODY",
        "text": "Hi {{1}}, your order {{2}} has been confirmed! It will be delivered by {{3}}. Total amount is {{4}}. Thank you for shopping with us.",
        "example": {
          "body_text": [
            [
              "Rahul",
              "ORD12345",
              "Feb 5, 2026",
              "Rs 2,499"
            ]
          ]
        }
      },
      {
        "type": "FOOTER",
        "text": "We appreciate your business"
      },
      {
        "type": "BUTTONS",
        "buttons": [
          {
            "type": "URL",
            "text": "Track Order",
            "url": "https://yourstore.com/track/{{1}}",
            "example": [
              "https://yourstore.com/track/ORD12345"
            ]
          },
          {
            "type": "PHONE_NUMBER",
            "text": "Contact Support",
            "phone_number": "+918861832522"
          }
        ]
      }
    ],
        },
    )

    print(f"\n=== Result ===")
    print(json.dumps(result.data, indent=2))

    assert result.data is not None
    assert "success" in result.data


# @pytest.mark.asyncio
# async def test_send_template_image_message(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending a template message with image header."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (template - image)")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "template",
#             "template_name": "sample_image_template",
#             "template_language_code": "en",
#             "template_language_policy": "deterministic",
#             "template_components": [
#                 {
#                     "type": "header",
#                     "parameters": [
#                         {
#                             "type": "image",
#                             "image": {
#                                 "link": "https://aisensy-project-media-library-stg.s3.ap-south-1.amazonaws.com/IMAGE/6245d025fcb7966c46294618/2699676_babyyoda1.png"
#                             },
#                         }
#                     ],
#                 },
#                 {
#                     "type": "body",
#                     "parameters": [
#                         {"type": "text", "text": "Romit"}
#                     ],
#                 },
#             ],
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data


# @pytest.mark.asyncio
# async def test_send_template_video_message(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending a template message with video header."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (template - video)")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "template",
#             "template_name": "video_type_template",
#             "template_language_code": "en",
#             "template_language_policy": "deterministic",
#             "template_components": [
#                 {
#                     "type": "header",
#                     "parameters": [
#                         {
#                             "type": "video",
#                             "video": {
#                                 "link": "https://aisensy-project-media-library-stg.s3.ap-south-1.amazonaws.com/VIDEO/6245d025fcb7966c46294618/6334744_6467606fileexampleMP448015MG.mp4"
#                             },
#                         }
#                     ],
#                 },
#                 {
#                     "type": "body",
#                     "parameters": [
#                         {"type": "text", "text": "Romit"}
#                     ],
#                 },
#             ],
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data


# @pytest.mark.asyncio
# async def test_send_template_document_message(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending a template message with document header."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (template - document)")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "template",
#             "template_name": "document_type_template",
#             "template_language_code": "en",
#             "template_language_policy": "deterministic",
#             "template_components": [
#                 {
#                     "type": "header",
#                     "parameters": [
#                         {
#                             "type": "document",
#                             "document": {
#                                 "link": "https://aisensy-project-media-library-stg.s3.ap-south-1.amazonaws.com/FILE/6245d025fcb7966c46294618/3665271_samplePDF.pdf",
#                                 "filename": "qwerty",
#                             },
#                         }
#                     ],
#                 },
#                 {
#                     "type": "body",
#                     "parameters": [
#                         {"type": "text", "text": "Romit"}
#                     ],
#                 },
#             ],
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data


# @pytest.mark.asyncio
# async def test_send_template_header_footer_only(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending a template message with empty components (header/footer only)."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (template - header/footer only)")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "template",
#             "template_name": "header_footer_type_template",
#             "template_language_code": "en",
#             "template_language_policy": "deterministic",
#             "template_components": [],
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data


# @pytest.mark.asyncio
# async def test_send_template_cta_button_message(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending a template message with CTA button."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (template - CTA button)")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "template",
#             "template_name": "cta_button_type_template1",
#             "template_language_code": "en",
#             "template_language_policy": "deterministic",
#             "template_components": [
#                 {
#                     "type": "button",
#                     "sub_type": "url",
#                     "index": "1",
#                     "parameters": [
#                         {"type": "text", "text": "part-of-the-url"}
#                     ],
#                 }
#             ],
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data


# @pytest.mark.asyncio
# async def test_send_template_coupon_code_message(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending a template message with coupon code and limited time offer."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (template - coupon code)")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "template",
#             "template_name": "limited_time_offer_tem_2",
#             "template_language_code": "en",
#             "template_language_policy": "deterministic",
#             "template_components": [
#                 {
#                     "type": "header",
#                     "parameters": [
#                         {
#                             "type": "image",
#                             "image": {
#                                 "link": "https://aisensy-project-media-library-stg.s3.ap-south-1.amazonaws.com/IMAGE/6245d025fcb7966c46294618/2699676_babyyoda1.png"
#                             },
#                         }
#                     ],
#                 },
#                 {
#                     "type": "body",
#                     "parameters": [
#                         {"type": "text", "text": "Romit"},
#                         {"type": "text", "text": "20%"},
#                     ],
#                 },
#                 {
#                     "type": "limited_time_offer",
#                     "parameters": [
#                         {"type": "text", "text": "1234"}
#                     ],
#                 },
#                 {
#                     "type": "button",
#                     "sub_type": "copy_code",
#                     "index": 0,
#                     "parameters": [
#                         {"type": "coupon_code", "coupon_code": "FAB20"}
#                     ],
#                 },
#                 {
#                     "type": "button",
#                     "sub_type": "url",
#                     "index": "1",
#                     "parameters": [
#                         {"type": "text", "text": "part-of-the-url"}
#                     ],
#                 },
#             ],
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data


# @pytest.mark.asyncio
# async def test_send_template_complex_message(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending a complex template with video header, body, and CTA button."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (template - complex mix)")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "template",
#             "template_name": "complex_type_template",
#             "template_language_code": "en",
#             "template_language_policy": "deterministic",
#             "template_components": [
#                 {
#                     "type": "header",
#                     "parameters": [
#                         {
#                             "type": "video",
#                             "video": {
#                                 "link": "https://aisensy-project-media-library-stg.s3.ap-south-1.amazonaws.com/VIDEO/6245d025fcb7966c46294618/6334744_6467606fileexampleMP448015MG.mp4"
#                             },
#                         }
#                     ],
#                 },
#                 {
#                     "type": "body",
#                     "parameters": [
#                         {"type": "text", "text": "Romit"}
#                     ],
#                 },
#                 {
#                     "type": "button",
#                     "sub_type": "url",
#                     "index": "1",
#                     "parameters": [
#                         {"type": "text", "text": "part-of-the-link"}
#                     ],
#                 },
#             ],
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data


# # ==================== INTERACTIVE MESSAGE TESTS ====================


# @pytest.mark.asyncio
# async def test_send_interactive_single_product_message(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending an interactive single product message."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (interactive - single product)")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "interactive",
#             "interactive": {
#                 "type": "product",
#                 "body": {"text": "Body text of interactive msg here"},
#                 "footer": {"text": "Interactive Msg Footer"},
#                 "action": {
#                     "catalog_id": "570881508310768",
#                     "product_retailer_id": "someId15",
#                 },
#             },
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data


# @pytest.mark.asyncio
# async def test_send_interactive_product_list_message(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending an interactive product list message."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (interactive - product list)")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "interactive",
#             "interactive": {
#                 "type": "product_list",
#                 "header": {"type": "text", "text": "Interactive Msg Header"},
#                 "body": {"text": "Body text of interactive msg here"},
#                 "footer": {"text": "Interactive Msg Footer"},
#                 "action": {
#                     "catalog_id": "1242162653103312",
#                     "sections": [
#                         {
#                             "title": "Earings",
#                             "product_items": [
#                                 {"product_retailer_id": "44347337697575"},
#                                 {"product_retailer_id": "44347336419623"},
#                             ],
#                         },
#                         {
#                             "title": "Apparels",
#                             "product_items": [
#                                 {"product_retailer_id": "44237374004519"},
#                                 {"product_retailer_id": "44237514808615"},
#                             ],
#                         },
#                     ],
#                 },
#             },
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data


# @pytest.mark.asyncio
# async def test_send_interactive_flow_draft_message(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test sending an interactive flow message in draft mode."""
#     print(f"\n{'=' * 80}")
#     print(f"Testing send_message (interactive - draft flow)")
#     print(f"{'=' * 80}")

#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "interactive",
#             "interactive": {
#                 "type": "flow",
#                 "header": {"type": "text", "text": "Not shown in draft mode"},
#                 "body": {"text": "Not shown in draft mode"},
#                 "footer": {"text": "Not shown in draft mode"},
#                 "action": {
#                     "name": "flow",
#                     "parameters": {
#                         "flow_message_version": "3",
#                         "flow_action": "navigate",
#                         "flow_token": "random_user_generated_token",
#                         "flow_id": "242618178791268",
#                         "flow_cta": "Not shown in draft mode",
#                         "mode": "draft",
#                         "flow_action_payload": {
#                             "screen": "MY_FIRST_SCREEN",
#                             "data": {"custom_variable": "custom_value"},
#                         },
#                     },
#                 },
#             },
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert "success" in result.data


# # ==================== VALIDATION / ERROR TESTS ====================


# @pytest.mark.asyncio
# async def test_send_message_missing_to(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test that tool fails when 'to' is not provided."""
#     with pytest.raises(Exception):
#         await direct_api_mcp_client.call_tool(
#             "send_message",
#             arguments={
#                 "user_id": "user1",
#                 "message_type": "text",
#                 "text_body": "Hello",
#             },
#         )


# @pytest.mark.asyncio
# async def test_send_text_message_missing_text_body(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test that text message fails when text_body is not provided."""
#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "text",
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert result.data.get("success") is False


# @pytest.mark.asyncio
# async def test_send_image_message_missing_media_link(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test that image message fails when media_link is not provided."""
#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "image",
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert result.data.get("success") is False


# @pytest.mark.asyncio
# async def test_send_template_message_missing_template_name(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test that template message fails when template_name is not provided."""
#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "template",
#             "template_language_code": "en",
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert result.data.get("success") is False


# @pytest.mark.asyncio
# async def test_send_interactive_message_missing_interactive(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test that interactive message fails when interactive object is not provided."""
#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "interactive",
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert result.data.get("success") is False


# @pytest.mark.asyncio
# async def test_send_message_unsupported_type(
#     direct_api_mcp_client: Client[FastMCPTransport],
# ):
#     """Test that unsupported message type returns error."""
#     result = await direct_api_mcp_client.call_tool(
#         "send_message",
#         arguments={
#             "user_id": "user1",
#             "to": "917089379345",
#             "message_type": "sticker",
#         },
#     )

#     print(f"\n=== Result ===")
#     print(json.dumps(result.data, indent=2))

#     assert result.data is not None
#     assert result.data.get("success") is False
