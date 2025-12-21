import pytest
import pytest_asyncio
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from inline_snapshot import snapshot


@pytest_asyncio.fixture
async def main_mcp_client():
    async with Client("mcp_servers/direct_api_server.py") as mcp_client:
        yield mcp_client


@pytest.mark.asyncio
async def test_list_tools(main_mcp_client: Client[FastMCPTransport]):
    list_tools = await main_mcp_client.list_tools()

    assert len(list_tools) == snapshot(53)
    
    tool_names = sorted([tool.name for tool in list_tools])
    assert tool_names == snapshot([
    "compare_template",
    "connect_catalog",
    "create_catalog",
    "create_flow",
    "create_payment_configuration",
    "create_product",
    "create_qr_code_and_short_link",
    "create_upload_session",
    "delete_flow",
    "delete_media_by_id",
    "delete_wa_template_by_id",
    "delete_wa_template_by_name",
    "deprecate_flow",
    "disconnect_catalog",
    "edit_template",
    "fb_verification_status",
    "generate_payment_configuration_oauth_link",
    "get_business_info",
    "get_catalog",
    "get_display_name_status",
    "get_flow_assets",
    "get_flow_by_id",
    "get_flows",
    "get_media_upload_session",
    "get_messaging_health_status",
    "get_payment_configuration_by_name",
    "get_payment_configurations",
    "get_phone_number",
    "get_phone_numbers",
    "get_products",
    "get_profile",
    "get_qr_codes",
    "get_template_by_id",
    "get_templates",
    "get_waba_analytics",
    "get_whatsapp_business_encryption",
    "get_whatsapp_commerce_settings",
    "mark_message_as_read",
    "publish_flow",
    "regenerate_jwt_bearer_token",
    "retrieve_media_by_id",
    "send_marketing_lite_message",
    "send_message",
    "set_business_public_key",
    "show_hide_catalog",
    "submit_whatsapp_template_message",
    "update_business_profile_details",
    "update_business_profile_picture",
    "update_flow_json",
    "update_flow_metadata",
    "update_qr_code",
    "upload_media",
    "upload_media_to_session",
])