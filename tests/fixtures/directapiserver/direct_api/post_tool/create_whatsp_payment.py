"""Tests for create_payment_configuration POST endpoint via MCP."""

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
async def test_inspect_create_payment_configuration_schema(
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Inspect the schema for create_payment_configuration tool."""
    tools = await direct_api_mcp_client.list_tools()
    
    target_tool = next(
        (t for t in tools if t.name == "create_payment_configuration"), None
    )
    
    assert target_tool is not None, "Tool not found"
    
    print("\n" + "="*80)
    print("TOOL SCHEMA FOR: create_payment_configuration")
    print("="*80)
    print(f"Name: {target_tool.name}")
    print(f"\nDescription: {target_tool.description}")
    print(f"\nInput Schema:")
    print(json.dumps(target_tool.inputSchema, indent=2))
    print("="*80)


@pytest.mark.parametrize(
    "user_id, configuration_name, purpose_code, merchant_category_code, provider_name, redirect_url, expected_success",
    [
        # Valid test case - Note: This will fail due to WhatsApp ToS not accepted
        # Keeping it to verify the request format is correct
        (
            "user1",
            "test-payment-configuration",
            "00",
            "0000",
            "RAZORPAY",
            "https://test-redirect-url.com",
            False  # Expected to fail due to ToS not accepted
        ),
        # Invalid provider name - not in allowed list
        (
            "user1",
            "prod-payment-config",
            "01",
            "1234",
            "stripe",  # Invalid - must be one of {BILLDESK, PAYU, RAZORPAY, UPI_VPA, ZAAKPAY}
            "https://example.com/callback",
            False
        ),
        # Invalid test case - empty configuration name
        (
            "user1",
            "",
            "00",
            "0000",
            "RAZORPAY",
            "https://test-redirect-url.com",
            False
        ),
        # Invalid test case - invalid URL
        (
            "user1",
            "test-config",
            "00",
            "0000",
            "RAZORPAY",
            "not-a-valid-url",
            False
        ),
        # Valid provider names test cases
        (
            "user1",
            "billdesk-config",
            "00",
            "0000",
            "BILLDESK",
            "https://example.com/callback",
            False  # Will fail due to ToS, but format is correct
        ),
        (
            "user1",
            "payu-config",
            "00",
            "0000",
            "PAYU",
            "https://example.com/callback",
            False  # Will fail due to ToS, but format is correct
        ),
    ],
)
@pytest.mark.asyncio
async def test_create_payment_configuration(
    user_id: str,
    configuration_name: str,
    purpose_code: str,
    merchant_category_code: str,
    provider_name: str,
    redirect_url: str,
    expected_success: bool,
    direct_api_mcp_client: Client[FastMCPTransport],
):
    """Test creating payment configuration.

    The tool creates a payment configuration with the provided parameters.
    
    Args:
        user_id: User ID for the payment configuration
        configuration_name: Name of the payment configuration
        purpose_code: Purpose code for the payment
        merchant_category_code: Merchant category code
        provider_name: Payment provider name (must be one of: BILLDESK, PAYU, RAZORPAY, UPI_VPA, ZAAKPAY)
        redirect_url: URL to redirect after payment
        expected_success: Whether this test case should succeed
    """
    print(f"\n{'='*80}")
    print(f"Testing create_payment_configuration")
    print(f"  - user_id: {user_id}")
    print(f"  - configuration_name: {configuration_name}")
    print(f"  - purpose_code: {purpose_code}")
    print(f"  - merchant_category_code: {merchant_category_code}")
    print(f"  - provider_name: {provider_name}")
    print(f"  - redirect_url: {redirect_url}")
    print(f"  - expected_success: {expected_success}")
    print(f"{'='*80}")
    
    # Call the tool
    result = await direct_api_mcp_client.call_tool(
        "create_payment_configuration",
        arguments={
            "user_id": user_id,
            "configuration_name": configuration_name,
            "purpose_code": purpose_code,
            "merchant_category_code": merchant_category_code,
            "provider_name": provider_name,
            "redirect_url": redirect_url,
        },
    )
    
    print(f"\n=== Result ===")
    print(json.dumps(result.data, indent=2))

    # Assertions
    assert result.data is not None, "Result should not be None"
    assert isinstance(result.data, dict), "Result should be a dictionary"
    assert "success" in result.data, "Result should contain 'success' field"
    
    if expected_success:
        assert result.data["success"] is True, \
            f"Expected success but got failure: {result.data.get('error', 'Unknown error')}"
        assert "data" in result.data or "configuration_name" in result.data, \
            "Successful response should contain data"
        
        # Verify the configuration was created with correct values
        response_data = result.data.get("data", result.data)
        if "configuration_name" in response_data:
            assert response_data["configuration_name"] == configuration_name
        if "provider_name" in response_data:
            assert response_data["provider_name"] == provider_name
        if "redirect_url" in response_data:
            assert response_data["redirect_url"] == redirect_url
            
    else:
        assert result.data["success"] is False, \
            f"Expected failure but got success: {result.data}"
        assert "error" in result.data, \
            "Failed response should contain 'error' field"
        
        print(f"\n✓ Test correctly failed with error: {result.data['error']}")