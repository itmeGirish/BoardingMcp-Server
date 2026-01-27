"""
CopilotKit tools for onboarding workflow

This module defines the LangChain tools that integrate with
the MCP server for the onboarding workflow.

IMPORTANT: These tools run in LangGraph's ASGI context.
We use ThreadPoolExecutor to run MCP calls in separate threads with their own event loops.
This pattern matches the working implementation and avoids all async/event loop conflicts.
"""

import asyncio
import json
import logging
import concurrent.futures
import nest_asyncio
from langchain.tools import tool

from ...config import logger

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Thread pool for running MCP calls in separate threads
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


# ============================================
# SYNC WRAPPERS - Run MCP calls in new event loop
# ============================================

def _run_create_business_profile_sync(
    user_id: str,
    display_name: str,
    email: str,
    company: str,
    contact: str,
    timezone: str,
    currency: str,
    company_size: str,
    password: str,
    onboarding_id: str
):
    """Run MCP create_business_profile synchronously in a new event loop."""
    # Import MCP modules INSIDE the function to avoid event loop conflicts
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.utils.whsp_onboarding_agent import parse_mcp_result_with_debug as parse_mcp_result, normalize_timezone

    async def _call():
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🔧 [MCP] Creating fresh MCP client...")
        # Create fresh MCP client with new connection
        client = MultiServerMCPClient({
            "BoardingMCP": {
                "url": "http://127.0.0.1:9001/mcp",
                "transport": "streamable-http"
            }
        })

        logger.info("🔧 [MCP] Opening MCP session...")
        async with client.session("BoardingMCP") as session:
            logger.info("🔧 [MCP] Loading MCP tools...")
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}
            logger.info(f"🔧 [MCP] Loaded {len(mcp_tools)} tools")

            create_business_tool = mcp_tools["create_business_profile"]

            # Normalize timezone before calling MCP
            normalized_timezone = normalize_timezone(timezone)
            logger.info(f"🔧 [MCP] Calling create_business_profile for {email}...")

            result = await create_business_tool.ainvoke({
                "display_name": display_name,
                "email": email,
                "company": company,
                "contact": contact,
                "timezone": normalized_timezone,
                "currency": currency,
                "company_size": company_size,
                "password": password,
                "user_id": user_id,
                "onboarding_id": onboarding_id
            })

            logger.info("🔧 [MCP] Tool call completed, parsing result...")
            # Parse MCP result
            parsed = parse_mcp_result(result)
            logger.info(f"🔧 [MCP] Result status: {parsed.get('status', 'unknown')}")
            return parsed

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call())
    finally:
        loop.close()


def _run_create_project_sync(user_id: str, name: str):
    """Run MCP create_project synchronously in a new event loop."""
    # Import MCP modules INSIDE the function to avoid event loop conflicts
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.utils.whsp_onboarding_agent import parse_mcp_result_with_debug as parse_mcp_result

    async def _call():
        # Create fresh MCP client with new connection
        client = MultiServerMCPClient({
            "BoardingMCP": {
                "url": "http://127.0.0.1:9001/mcp",
                "transport": "streamable-http"
            }
        })

        async with client.session("BoardingMCP") as session:
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}

            create_project_tool = mcp_tools["create_project"]

            result = await create_project_tool.ainvoke({
                "user_id": user_id,
                "name": name
            })

            # Parse MCP result
            return parse_mcp_result(result)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call())
    finally:
        loop.close()


def _run_generate_embedded_signup_url_sync(
    user_id: str,
    business_name: str,
    business_email: str,
    phone_code: int,
    phone_number: str,
    website: str,
    street_address: str,
    city: str,
    state: str,
    zip_postal: str,
    country: str,
    timezone: str,
    display_name: str,
    category: str,
    description: str = None
):
    """Run MCP generate_embedded_signup_url synchronously in a new event loop."""
    # Import MCP modules INSIDE the function to avoid event loop conflicts
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.utils.whsp_onboarding_agent import parse_mcp_result_with_debug as parse_mcp_result, normalize_timezone, normalize_country_code

    async def _call():
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🔧 [MCP] Creating fresh MCP client for embedded signup...")
        # Create fresh MCP client with new connection
        client = MultiServerMCPClient({
            "BoardingMCP": {
                "url": "http://127.0.0.1:9001/mcp",
                "transport": "streamable-http"
            }
        })

        logger.info("🔧 [MCP] Opening MCP session...")
        async with client.session("BoardingMCP") as session:
            logger.info("🔧 [MCP] Loading MCP tools...")
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}
            logger.info(f"🔧 [MCP] Loaded {len(mcp_tools)} tools")

            generate_signup_tool = mcp_tools["generate_embedded_signup_url"]

            # Normalize timezone and country before calling MCP
            logger.info("🔧 [MCP] Normalizing timezone and country codes...")
            normalized_timezone = normalize_timezone(timezone)
            normalized_country = normalize_country_code(country)
            logger.info(f"🔧 [MCP]   Timezone: {timezone} -> {normalized_timezone}")
            logger.info(f"🔧 [MCP]   Country: {country} -> {normalized_country}")

            logger.info(f"🔧 [MCP] Calling generate_embedded_signup_url for {business_email}...")
            result = await generate_signup_tool.ainvoke({
                "user_id": user_id,
                "business_name": business_name,
                "business_email": business_email,
                "phone_code": phone_code,
                "phone_number": phone_number,
                "website": website,
                "street_address": street_address,
                "city": city,
                "state": state,
                "zip_postal": zip_postal,
                "country": normalized_country,
                "timezone": normalized_timezone,
                "display_name": display_name,
                "category": category,
                "description": description
            })

            logger.info("🔧 [MCP] Tool call completed, parsing result...")
            # Parse MCP result
            parsed = parse_mcp_result(result)
            logger.info(f"🔧 [MCP] Result status: {parsed.get('status', 'unknown')}")
            return parsed

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call())
    finally:
        loop.close()


def _run_get_kyc_submission_status_sync(user_id: str):
    """Run MCP get_kyc_submission_status synchronously in a new event loop."""
    # Import MCP modules INSIDE the function to avoid event loop conflicts
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.utils.whsp_onboarding_agent import parse_mcp_result_with_debug as parse_mcp_result

    async def _call():
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🔧 [MCP] Creating fresh MCP client for KYC status check...")
        # Create fresh MCP client with new connection
        client = MultiServerMCPClient({
            "BoardingMCP": {
                "url": "http://127.0.0.1:9001/mcp",
                "transport": "streamable-http"
            }
        })

        logger.info("🔧 [MCP] Opening MCP session...")
        async with client.session("BoardingMCP") as session:
            logger.info("🔧 [MCP] Loading MCP tools...")
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}
            logger.info(f"🔧 [MCP] Loaded {len(mcp_tools)} tools")

            get_kyc_status_tool = mcp_tools["get_kyc_submission_status"]

            logger.info(f"🔧 [MCP] Calling get_kyc_submission_status for user_id: {user_id}...")
            result = await get_kyc_status_tool.ainvoke({
                "user_id": user_id
            })

            logger.info("🔧 [MCP] Tool call completed, parsing result...")
            # Parse MCP result
            parsed = parse_mcp_result(result)
            logger.info(f"🔧 [MCP] Result status: {parsed.get('status', 'unknown')}")
            return parsed

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call())
    finally:
        loop.close()


def _run_regenerate_jwt_bearer_token_sync(user_id: str, direct_api: bool = True):
    """Run MCP regenerate_jwt_bearer_token synchronously in a new event loop.

    This connects to the Direct API MCP server (port 9002) to:
    1. Fetch email, password, project_id from database
    2. Generate base64 token
    3. Call API to regenerate JWT bearer token
    4. Store the generated JWT token in database
    """
    # Import MCP modules INSIDE the function to avoid event loop conflicts
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.utils.whsp_onboarding_agent import parse_mcp_result_with_debug as parse_mcp_result

    async def _call():
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🔧 [MCP] Creating fresh MCP client for JWT token regeneration...")
        # Create fresh MCP client with connection to Direct API MCP server
        client = MultiServerMCPClient({
            "DirectApiMCP": {
                "url": "http://127.0.0.1:9002/mcp",
                "transport": "streamable-http"
            }
        })

        logger.info("🔧 [MCP] Opening MCP session to Direct API server...")
        async with client.session("DirectApiMCP") as session:
            logger.info("🔧 [MCP] Loading MCP tools from Direct API server...")
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}
            logger.info(f"🔧 [MCP] Loaded {len(mcp_tools)} tools from Direct API server")

            regenerate_jwt_tool = mcp_tools["regenerate_jwt_bearer_token"]

            logger.info(f"🔧 [MCP] Calling regenerate_jwt_bearer_token for user_id: {user_id}...")
            result = await regenerate_jwt_tool.ainvoke({
                "user_id": user_id,
                "direct_api": direct_api
            })

            logger.info("🔧 [MCP] Tool call completed, parsing result...")
            # Parse MCP result
            parsed = parse_mcp_result(result)
            logger.info(f"🔧 [MCP] Result status: {parsed.get('status', 'unknown')}")
            return parsed

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call())
    finally:
        loop.close()


# ============================================
# STEP 1: BUSINESS PROFILE TOOL
# ============================================

@tool
def show_business_profile_form(
    user_id: str,
    display_name: str,
    email: str,
    company: str,
    contact: str,
    timezone: str,
    currency: str,
    company_size: str,
    password: str,
    onboarding_id: str
) -> str:
    """
    Display the business profile form AND create business profile via MCP as STEP 1 of onboarding.

    This is called when you receive "Workflow business profile submitted" message.
    It calls the MCP create_business_profile tool and then shows the project form.

    Args:
        user_id: User's unique identifier
        display_name: User's display name
        email: User's email address
        company: Company name
        contact: Contact number
        timezone: Timezone - accepts "Asia/Calcutta" (auto-converted to "Asia/Calcutta GMT+05:30")
        currency: Currency code (e.g., "INR")
        company_size: Company size (e.g., "1-10", "11-50", "51-200")
        password: User password
        onboarding_id: Onboarding identifier

    Returns:
        JSON string containing the MCP result
    """
    logger.info("🔧 [BACKEND] show_business_profile_form called for user: %s", user_id)

    try:
        logger.info("🔧 [BACKEND] Submitting MCP call to thread pool...")
        # Run MCP call in thread pool to avoid event loop conflicts
        future = _executor.submit(
            _run_create_business_profile_sync,
            user_id=user_id,
            display_name=display_name,
            email=email,
            company=company,
            contact=contact,
            timezone=timezone,
            currency=currency,
            company_size=company_size,
            password=password,
            onboarding_id=onboarding_id
        )
        logger.info("🔧 [BACKEND] Waiting for MCP result (timeout: 60s)...")
        result = future.result(timeout=60)

        # Ensure result is a dict
        if not isinstance(result, dict):
            logger.error("MCP returned non-dict result: %s", type(result))
            result = {"error": "Invalid MCP response format", "status": "failed"}

        logger.info("🔧 [BACKEND] Business profile creation result: %s", result.get('status', 'unknown'))

        # Log what we're returning to the agent
        result_json = json.dumps(result, ensure_ascii=False)
        logger.info("🔧 [BACKEND] Returning to agent: %s", result_json[:200])

        # Always return a valid JSON string
        return result_json

    except Exception as e:
        error_msg = str(e)
        logger.error("🔧 [BACKEND] Business profile error: %s", e, exc_info=True)
        # Ensure we always return valid JSON
        return json.dumps({"error": error_msg, "status": "failed", "details": "Exception in show_business_profile_form"}, ensure_ascii=False)


# ============================================
# STEP 2: PROJECT TOOL
# ============================================

@tool
def show_project_form(
    user_id: str,
    name: str
) -> str:
    """
    Display the project form AND create project via MCP as STEP 2 of onboarding.

    This is called when you receive "Workflow project submitted" message.
    It calls the MCP create_project tool and then shows the embedded signup form.
    The business_id is automatically fetched from the database based on user_id.

    Args:
        user_id: User's unique identifier - used to fetch the associated business_id from database
        name: Project name

    Returns:
        JSON string containing the MCP result
    """
    logger.info("🔧 [BACKEND] show_project_form called for user: %s, project: %s", user_id, name)

    try:
        # Run MCP call in thread pool to avoid event loop conflicts
        future = _executor.submit(_run_create_project_sync, user_id=user_id, name=name)
        result = future.result(timeout=30)

        # Ensure result is a dict
        if not isinstance(result, dict):
            logger.error("MCP returned non-dict result: %s", type(result))
            result = {"error": "Invalid MCP response format", "status": "failed"}

        logger.info("🔧 [BACKEND] Project creation result: %s", result.get('status', 'unknown'))
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        error_msg = str(e)
        logger.error("🔧 [BACKEND] Project creation error: %s", e, exc_info=True)
        return json.dumps({"error": error_msg, "status": "failed", "details": "Exception in show_project_form"}, ensure_ascii=False)


# ============================================
# STEP 3: EMBEDDED SIGNUP TOOL
# ============================================

@tool
def show_embedded_signup_form(
    user_id: str,
    business_name: str,
    business_email: str,
    phone_code: int,
    phone_number: str,
    website: str,
    street_address: str,
    city: str,
    state: str,
    zip_postal: str,
    country: str,
    timezone: str,
    display_name: str,
    category: str,
    description: str = ""
) -> str:
    """
    Display the embedded signup form AND submit final onboarding via MCP as STEP 3.

    This is called when you receive "Workflow embedded signup submitted" message.
    It calls the MCP generate_embedded_signup_url tool and completes the entire onboarding process.

    Args:
        user_id: User's unique identifier
        business_name: Business name for embedded signup
        business_email: Business email address
        phone_code: Phone country code as integer (e.g., 91 for India, 1 for USA)
        phone_number: Full phone number (e.g., "+919876543210")
        website: Business website URL
        street_address: Street address
        city: City
        state: State/Province
        zip_postal: ZIP or postal code
        country: Country - accepts full name like "India" (auto-converted to "IN")
        timezone: Timezone - accepts "Asia/Calcutta" (auto-converted to "Asia/Calcutta GMT+05:30")
        display_name: Display name
        category: Business category
        description: Optional business description

    Returns:
        JSON string containing the MCP result with signup URL
    """
    logger.info("🔧 [BACKEND] show_embedded_signup_form called for user: %s", user_id)

    try:
        # Run MCP call in thread pool to avoid event loop conflicts
        future = _executor.submit(
            _run_generate_embedded_signup_url_sync,
            user_id=user_id,
            business_name=business_name,
            business_email=business_email,
            phone_code=phone_code,
            phone_number=phone_number,
            website=website,
            street_address=street_address,
            city=city,
            state=state,
            zip_postal=zip_postal,
            country=country,
            timezone=timezone,
            display_name=display_name,
            category=category,
            description=description or None
        )
        logger.info("🔧 [BACKEND] Waiting for embedded signup URL generation (timeout: 60s)...")
        result = future.result(timeout=60)

        # Ensure result is a dict
        if not isinstance(result, dict):
            logger.error("MCP returned non-dict result: %s", type(result))
            result = {"error": "Invalid MCP response format", "status": "failed"}

        logger.info("🔧 [BACKEND] Embedded signup result: %s", result.get('status', 'unknown'))
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        error_msg = str(e)
        logger.error("🔧 [BACKEND] Embedded signup error: %s", e, exc_info=True)
        return json.dumps({"error": error_msg, "status": "failed", "details": "Exception in show_embedded_signup_form"}, ensure_ascii=False)


# ============================================
# STEP 4: CHECK VERIFICATION STATUS TOOL
# ============================================

@tool
def check_verification_status(user_id: str) -> str:
    """
    Check the KYC/WABA verification status after user completes embedded signup.

    This is called AFTER the user has clicked the embedded signup URL and completed
    the Facebook signup process. It checks if the WhatsApp Business Account (WABA)
    verification is complete.

    The project_id is automatically fetched from the database based on user_id.

    Args:
        user_id: User's unique identifier - used to fetch the associated project from database

    Returns:
        JSON string containing:
        - success: true if verification is complete
        - data: KYC submission status details
        - error: Error message if verification is pending or failed
    """
    logger.info("🔧 [BACKEND] check_verification_status called for user: %s", user_id)

    try:
        # Run MCP call in thread pool to avoid event loop conflicts
        future = _executor.submit(_run_get_kyc_submission_status_sync, user_id=user_id)
        logger.info("🔧 [BACKEND] Waiting for KYC status check (timeout: 30s)...")
        result = future.result(timeout=30)

        # Ensure result is a dict
        if not isinstance(result, dict):
            logger.error("MCP returned non-dict result: %s", type(result))
            result = {"error": "Invalid MCP response format", "status": "failed"}

        logger.info("🔧 [BACKEND] KYC status check result: %s", result.get('status', 'unknown'))
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        error_msg = str(e)
        logger.error("🔧 [BACKEND] KYC status check error: %s", e, exc_info=True)
        return json.dumps({"error": error_msg, "status": "failed", "details": "Exception in check_verification_status"}, ensure_ascii=False)


# ============================================
# STEP 5: REGENERATE JWT BEARER TOKEN TOOL (FINAL STEP)
# ============================================

@tool
def regenerate_jwt_bearer_token_tool(user_id: str) -> str:
    """
    Test Business WhatsApp & Regenerate JWT Bearer Token as the FINAL STEP of onboarding.

    This tool is called ONLY AFTER the WABA verification is SUCCESSFUL (check_verification_status returned success).
    It connects to the Direct API MCP server to:
    1. Fetch email, password, project_id from the database using user_id
    2. Generate a base64 token in format <email>:<password>:<projectId>
    3. Call the API to regenerate a new JWT bearer token
    4. Store the generated JWT token in the database

    After this tool completes successfully, the WhatsApp onboarding is COMPLETE.

    Args:
        user_id: User's unique identifier - used to fetch credentials and project info from database

    Returns:
        JSON string containing:
        - success: true if JWT token was generated and saved
        - data: Contains the generated JWT token details
        - error: Error message if token generation failed
    """
    logger.info("🔧 [BACKEND] regenerate_jwt_bearer_token_tool called for user: %s", user_id)

    try:
        # Run MCP call in thread pool to avoid event loop conflicts
        future = _executor.submit(_run_regenerate_jwt_bearer_token_sync, user_id=user_id, direct_api=True)
        logger.info("🔧 [BACKEND] Waiting for JWT token regeneration (timeout: 60s)...")
        result = future.result(timeout=60)

        # Ensure result is a dict
        if not isinstance(result, dict):
            logger.error("MCP returned non-dict result: %s", type(result))
            result = {"error": "Invalid MCP response format", "status": "failed"}

        logger.info("🔧 [BACKEND] JWT token regeneration result: %s", result.get('status', 'unknown'))
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        error_msg = str(e)
        logger.error("🔧 [BACKEND] JWT token regeneration error: %s", e, exc_info=True)
        return json.dumps({"error": error_msg, "status": "failed", "details": "Exception in regenerate_jwt_bearer_token_tool"}, ensure_ascii=False)


# ============================================
# TOOLS EXPORTS
# ============================================

# List of all backend tools for the workflow
BACKEND_TOOLS = [
    show_business_profile_form,
    show_project_form,
    show_embedded_signup_form,
    check_verification_status,
    regenerate_jwt_bearer_token_tool,  # Final step - JWT generation after verification success
]

# Set of tool names for O(1) lookup
BACKEND_TOOL_NAMES = {tool.name for tool in BACKEND_TOOLS}