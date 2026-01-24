"""
Onboarding Agent - Interactive Multi-Step Workflow
Converts the OnboardingFlow workflow into CopilotKit-compatible tools
Flow:
1. User starts onboarding → show_business_profile_form
2. Business profile submitted → process_business_profile_and_show_project_form
3. Project submitted → process_project_and_show_embedded_signup_form
4. Embedded signup submitted → submit_final_onboarding_mcp
"""

from typing import List, Optional, Dict, Any
from copilotkit import CopilotKitState
from langchain.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
import asyncio
import nest_asyncio
import concurrent.futures
import json

# Import state definitions
from app.workflows.whatsp.state import (
    CreateBusinessProfileState,
    CreateProjectState,
    EmbeddedSignupUrlState,
)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Thread pool for running MCP calls in separate thread
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


class AgentState(CopilotKitState):
    """State for the onboarding agent"""
    pass


# ============================================
# Timezone Helper
# ============================================

def normalize_timezone(timezone: str) -> str:
    """
    Normalize timezone to the format expected by MCP server.
    MCP server expects format: "Asia/Calcutta GMT+05:30"
    """
    # Common timezone mappings to MCP server format
    timezone_map = {
        "Asia/Calcutta": "Asia/Calcutta GMT+05:30",
        "Asia/Kolkata": "Asia/Calcutta GMT+05:30",
        "GMT+05:30": "Asia/Calcutta GMT+05:30",
        "GMT+5:30": "Asia/Calcutta GMT+05:30",
        "IST": "Asia/Calcutta GMT+05:30",
    }
    
    # If already in correct format, return as-is
    if "GMT" in timezone and "/" in timezone:
        return timezone
    
    # Return mapped timezone or original if no mapping exists
    return timezone_map.get(timezone, timezone)


def normalize_country_code(country: str) -> str:
    """
    Normalize country name to ISO 2-character country code.
    MCP server expects 2-character codes like "IN", "US", etc.
    """
    # Common country name to ISO code mappings
    country_map = {
        "India": "IN",
        "United States": "US",
        "United Kingdom": "GB",
        "Canada": "CA",
        "Australia": "AU",
        "Germany": "DE",
        "France": "FR",
        "Japan": "JP",
        "China": "CN",
        "Singapore": "SG",
    }
    
    # If already 2 characters, assume it's a code
    if len(country) == 2:
        return country.upper()
    
    # Return mapped code or original if no mapping exists
    return country_map.get(country, country)


# ============================================
# MCP Tool Helpers - Run in separate thread
# ============================================

def _run_mcp_create_business_sync(
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
    """Run MCP create_business_profile tool synchronously in a new event loop."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools

    async def _call_create_business():
        client = MultiServerMCPClient({
            "FormsMCP": {
                "url": "http://127.0.0.1:9001/mcp",
                "transport": "streamable-http"
            }
        })

        async with client.session("FormsMCP") as session:
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}

            create_business_tool = mcp_tools["create_business_profile"]
            
            # Normalize timezone before sending to MCP
            normalized_timezone = normalize_timezone(timezone)
            print(f"🔧 [MCP] Original timezone: {timezone}, Normalized: {normalized_timezone}")
            
            result = await create_business_tool.ainvoke({
                "user_id": user_id,
                "display_name": display_name,
                "email": email,
                "company": company,
                "contact": contact,
                "timezone": normalized_timezone,
                "currency": currency,
                "company_size": company_size,
                "password": password,
                "onboarding_id": onboarding_id
            })

            # Parse MCP result
            if hasattr(result, 'content'):
                result_data = result.content
            else:
                result_data = result

            # Handle list format from MCP
            if isinstance(result_data, list) and len(result_data) > 0:
                first_item = result_data[0]
                if isinstance(first_item, dict) and first_item.get('type') == 'text':
                    text_content = first_item['text']
                    try:
                        result_data = json.loads(text_content)
                    except:
                        result_data = {"status": "success", "message": text_content}

            return result_data

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call_create_business())
    finally:
        loop.close()


def _run_mcp_create_project_sync(
    user_id: str,
    name: str
):
    """Run MCP create_project tool synchronously in a new event loop."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools

    async def _call_create_project():
        client = MultiServerMCPClient({
            "FormsMCP": {
                "url": "http://127.0.0.1:9001/mcp",
                "transport": "streamable-http"
            }
        })

        async with client.session("FormsMCP") as session:
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}

            create_project_tool = mcp_tools["create_project"]
            result = await create_project_tool.ainvoke({
                "user_id": user_id,
                "name": name
            })

            # Parse MCP result
            if hasattr(result, 'content'):
                result_data = result.content
            else:
                result_data = result

            # Handle list format from MCP
            if isinstance(result_data, list) and len(result_data) > 0:
                first_item = result_data[0]
                if isinstance(first_item, dict) and first_item.get('type') == 'text':
                    text_content = first_item['text']
                    try:
                        result_data = json.loads(text_content)
                    except:
                        result_data = {"status": "success", "message": text_content}

            return result_data

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call_create_project())
    finally:
        loop.close()


def _run_mcp_embedded_signup_sync(
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
    """Run MCP generate_embedded_signup_url tool synchronously in a new event loop."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools

    async def _call_embedded_signup():
        client = MultiServerMCPClient({
            "FormsMCP": {
                "url": "http://127.0.0.1:9001/mcp",
                "transport": "streamable-http"
            }
        })

        async with client.session("FormsMCP") as session:
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}
            
            # Use the correct tool name
            embedded_signup_tool = mcp_tools["generate_embedded_signup_url"]
            
            # Normalize timezone before sending to MCP
            normalized_timezone = normalize_timezone(timezone)
            normalized_country = normalize_country_code(country)
            print(f"🔧 [MCP] Original timezone: {timezone}, Normalized: {normalized_timezone}")
            print(f"🔧 [MCP] Original country: {country}, Normalized: {normalized_country}")
            
            result = await embedded_signup_tool.ainvoke({
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

            # Parse MCP result
            if hasattr(result, 'content'):
                result_data = result.content
            else:
                result_data = result

            # Handle list format from MCP
            if isinstance(result_data, list) and len(result_data) > 0:
                first_item = result_data[0]
                if isinstance(first_item, dict) and first_item.get('type') == 'text':
                    text_content = first_item['text']
                    try:
                        result_data = json.loads(text_content)
                    except:
                        result_data = {"status": "success", "message": text_content}

            return result_data

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call_embedded_signup())
    finally:
        loop.close()


# ============================================
# Step 1: Business Profile Form
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
        timezone: Timezone - use format "Asia/Calcutta GMT+05:30" (will auto-convert if just "Asia/Calcutta")
        currency: Currency code (e.g., "INR")
        company_size: Company size (e.g., "1-10", "11-50", "51-200")
        password: User password
        onboarding_id: Onboarding identifier
    """
    print(f"🔧 [BACKEND] show_business_profile_form called")
    print(f"🔧 [BACKEND]   user_id: {user_id}")
    print(f"🔧 [BACKEND]   display_name: {display_name}")
    print(f"🔧 [BACKEND]   company: {company}")
    print(f"🔧 [BACKEND]   email: {email}")
    print(f"🔧 [BACKEND]   timezone: {timezone}")

    try:
        # Run MCP business creation in thread pool to avoid blocking event loop
        future = _executor.submit(
            _run_mcp_create_business_sync,
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
        result = future.result(timeout=30)

        print(f"🔧 [BACKEND] MCP business creation result: {result}")

        # Return raw MCP result
        return json.dumps(result) if isinstance(result, dict) else str(result)

    except Exception as e:
        print(f"🔧 [BACKEND] MCP business creation error: {e}")
        import traceback
        traceback.print_exc()
        # Return error as JSON
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# Step 2: Project Form
# ============================================

@tool
def show_project_form(
    user_id: str,
    name: str
) -> str:
    """
    Display the project form AND create project via MCP as Step 2 of onboarding.
    This is called when you receive "Workflow project submitted" message.
    It calls the MCP create_project tool and then shows the embedded signup form.

    Args:
        user_id: User's unique identifier (from business profile step)
        name: Project name
    """
    print(f"🔧 [BACKEND] show_project_form called")
    print(f"🔧 [BACKEND]   user_id: {user_id}")
    print(f"🔧 [BACKEND]   name: {name}")

    try:
        # Run MCP project creation in thread pool
        future = _executor.submit(
            _run_mcp_create_project_sync,
            user_id=user_id,
            name=name
        )
        result = future.result(timeout=30)

        print(f"🔧 [BACKEND] MCP project creation result: {result}")

        # Return raw MCP result
        return json.dumps(result) if isinstance(result, dict) else str(result)

    except Exception as e:
        print(f"🔧 [BACKEND] MCP project creation error: {e}")
        import traceback
        traceback.print_exc()
        # Return error as JSON
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# Step 3: Embedded Signup Form
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
    Display the embedded signup form AND submit final onboarding via MCP as Step 3.
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
        country: Country - accepts full name like "India" (will be auto-converted to "IN")
        timezone: Timezone - use format "Asia/Calcutta GMT+05:30" (will auto-convert if just "Asia/Calcutta")
        display_name: Display name
        category: Business category
        description: Optional business description
    """
    print(f"🔧 [BACKEND] show_embedded_signup_form called")
    print(f"🔧 [BACKEND]   user_id: {user_id}")
    print(f"🔧 [BACKEND]   business_name: {business_name}")
    print(f"🔧 [BACKEND]   business_email: {business_email}")
    print(f"🔧 [BACKEND]   phone_code: {phone_code}")
    print(f"🔧 [BACKEND]   phone_number: {phone_number}")
    print(f"🔧 [BACKEND]   timezone: {timezone}")

    try:
        # Run MCP embedded signup in thread pool
        future = _executor.submit(
            _run_mcp_embedded_signup_sync,
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
        result = future.result(timeout=30)

        print(f"🔧 [BACKEND] MCP embedded signup result: {result}")

        # Return raw MCP result
        return json.dumps(result) if isinstance(result, dict) else str(result)

    except Exception as e:
        print(f"🔧 [BACKEND] MCP embedded signup error: {e}")
        import traceback
        traceback.print_exc()
        # Return error as JSON
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# Agent Configuration
# ============================================

backend_tools = [
    show_business_profile_form,
    show_project_form,
    show_embedded_signup_form
]
backend_tool_names = [tool.name for tool in backend_tools]


async def chat_node(state: AgentState, config: RunnableConfig) -> Command[str]:
    model = ChatOpenAI(model="gpt-4o-mini")

    model_with_tools = model.bind_tools(
        [
            *state.get("copilotkit", {}).get("actions", []),
            *backend_tools,
        ],
        parallel_tool_calls=True,
    )

    system_message = SystemMessage(
        content=f"""You are a helpful onboarding assistant.

CRITICAL ONBOARDING WORKFLOW - FOLLOW EXACTLY (3 STEPS):

STEP 1 - When you see "Workflow business profile submitted" with parameters:
- IMMEDIATELY call show_business_profile_form with ALL these required parameters:
  * user_id, display_name, email, company, contact, timezone, currency, company_size, password, onboarding_id
- This will create the business profile via MCP AND display the project form

STEP 2 - When you see "Workflow project submitted" with parameters:
- IMMEDIATELY call show_project_form with these required parameters:
  * user_id, name
- This will create the project via MCP AND display the embedded signup form

STEP 3 - When you see "Workflow embedded signup submitted" with parameters:
- IMMEDIATELY call show_embedded_signup_form with ALL these required parameters:
  * user_id, business_name, business_email, phone_code (integer like 91), phone_number (full number like "+919876543210"), website, street_address, city, state, zip_postal, country, timezone, display_name, category
  * Optional: description
- This will create the embedded signup via MCP AND complete the onboarding

IMPORTANT: Do NOT ask for confirmation. When you see "Workflow X submitted", IMMEDIATELY call the corresponding tool with ALL parameters from that message."""
    )

    response = await model_with_tools.ainvoke(
        [
            system_message,
            *state["messages"],
        ],
        config,
    )

    if route_to_tool_node(response):
        print("routing to tool node")
        return Command(
            goto="tool_node",
            update={
                "messages": [response],
            },
        )

    return Command(
        goto=END,
        update={
            "messages": [response],
        },
    )


def route_to_tool_node(response: BaseMessage):
    """Route to tool node if any tool call matches a backend tool name."""
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls:
        return False

    for tool_call in tool_calls:
        if tool_call.get("name") in backend_tool_names:
            return True
    return False


workflow = StateGraph(AgentState)
workflow.add_node("chat_node", chat_node)
workflow.add_node("tool_node", ToolNode(tools=backend_tools))
workflow.add_edge("tool_node", "chat_node")
workflow.set_entry_point("chat_node")

graph = workflow.compile()