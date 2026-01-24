"""
CopilotKit tools for onboarding workflow

This module defines the LangChain tools that integrate with
the MCP server for the onboarding workflow.

IMPORTANT: These tools run in LangGraph's ASGI context.
We use asyncio.to_thread() to avoid blocking the event loop.
"""

import asyncio
import json
import logging
from langchain.tools import tool

from ..mcp_client import whsp_onboarding_agent as mcp_client

logger = logging.getLogger(__name__)


# ============================================
# HELPER: Non-blocking async wrapper
# ============================================

async def _run_async_in_thread(async_func, *args, **kwargs):
    """
    Run an async function in a separate thread to avoid blocking.
    
    This is necessary because LangGraph runs in an ASGI context
    where blocking calls are not allowed.
    
    Args:
        async_func: The async function to run
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        Result from the async function
    """
    def sync_wrapper():
        # Create new event loop in thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()
    
    # Run in thread pool to avoid blocking
    return await asyncio.to_thread(sync_wrapper)


# ============================================
# STEP 1: BUSINESS PROFILE TOOL
# ============================================

@tool
async def show_business_profile_form(
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
    logger.info("Business profile form called for user: %s", user_id)
    
    try:
        # Use to_thread to avoid blocking in ASGI context
        result = await _run_async_in_thread(
            mcp_client.create_business_profile,
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
        
        logger.info("Business profile creation result: %s", result.get('status', 'unknown'))
        return json.dumps(result)
        
    except Exception as e:
        logger.error("Business profile error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# STEP 2: PROJECT TOOL
# ============================================

@tool
async def show_project_form(
    user_id: str,
    name: str
) -> str:
    """
    Display the project form AND create project via MCP as STEP 2 of onboarding.
    
    This is called when you receive "Workflow project submitted" message.
    It calls the MCP create_project tool and then shows the embedded signup form.

    Args:
        user_id: User's unique identifier
        name: Project name
    
    Returns:
        JSON string containing the MCP result
    """
    logger.info("Project form called for user: %s, project: %s", user_id, name)
    
    try:
        # Use to_thread to avoid blocking in ASGI context
        result = await _run_async_in_thread(
            mcp_client.create_project,
            user_id=user_id,
            name=name
        )
        
        logger.info("Project creation result: %s", result.get('status', 'unknown'))
        return json.dumps(result)
        
    except Exception as e:
        logger.error("Project creation error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# STEP 3: EMBEDDED SIGNUP TOOL
# ============================================

@tool
async def show_embedded_signup_form(
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
    logger.info("Embedded signup form called for user: %s", user_id)
    
    try:
        # Use to_thread to avoid blocking in ASGI context
        result = await _run_async_in_thread(
            mcp_client.generate_embedded_signup_url,
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
        
        logger.info("Embedded signup result: %s", result.get('status', 'unknown'))
        return json.dumps(result)
        
    except Exception as e:
        logger.error("Embedded signup error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# TOOLS EXPORTS
# ============================================

# List of all backend tools for the workflow
BACKEND_TOOLS = [
    show_business_profile_form,
    show_project_form,
    show_embedded_signup_form,
]

# Set of tool names for O(1) lookup
BACKEND_TOOL_NAMES = {tool.name for tool in BACKEND_TOOLS}