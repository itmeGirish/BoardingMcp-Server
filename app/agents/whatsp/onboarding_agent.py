"""
This is the main entry point for the agent.
Onboarding workflow with step-by-step frontend forms.
The agent uses backend tools that trigger frontend rendering via useFrontendTool.
MCP tools are called when form data is submitted to actually create resources.
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
from ...config import settings, logger

# Import the MCP workflow tool
from ...workflows.whatsp.onboarding_workflow import run_onboarding_http_workflow


class AgentState(CopilotKitState):
    """Onboarding Agent State - synced with frontend"""
    proverbs: Optional[List[str]] = None
    # Onboarding state
    business_profile: Optional[dict] = None
    project: Optional[dict] = None
    whatsapp_setup: Optional[dict] = None
    onboarding_step: Optional[str] = "not_started"
    # Store results from MCP calls
    business_profile_result: Optional[dict] = None
    project_result: Optional[dict] = None
    embedded_signup_result: Optional[dict] = None


# ============================================
# Backend Tools - MCP workflow tools + demo tools
# These are called by the agent, frontend tools show forms
# ============================================

@tool
def get_weather(location: str) -> str:
    """
    Get the weather for a given location.
    Used for demonstration.
    """
    return f"The weather for {location} is 70 degrees and sunny."


@tool
async def create_business_profile_mcp(
    user_id: str,
    display_name: str,
    email: str,
    company: str,
    contact: str,
    timezone: str,
    currency: str,
    company_size: str,
    password: str
) -> Dict[str, Any]:
    """
    Create a business profile using the MCP workflow.
    Call this tool AFTER the user submits the business profile form.

    Args:
        user_id: Unique user identifier
        display_name: User's display name
        email: User's email address
        company: Company name
        contact: Contact number
        timezone: User's timezone (e.g., 'UTC', 'America/New_York')
        currency: Preferred currency (e.g., 'USD', 'EUR')
        company_size: Size of company (e.g., '1-10', '11-50', '51-200')
        password: Account password

    Returns:
        Result of business profile creation from MCP server
    """
    try:
        logger.info(f"Creating business profile for user: {user_id}, company: {company}")

        result = await run_onboarding_http_workflow.ainvoke({
            "user_id": user_id,
            "current_step": "business_profile",
            "business_profile": {
                "display_name": display_name,
                "email": email,
                "company": company,
                "contact": contact,
                "timezone": timezone,
                "currency": currency,
                "company_size": company_size,
                "password": password,
                "user_id": user_id,
                "onboarding_id": f"onb_{user_id}"
            },
            "project": None,
            "embedded_signup": None
        })

        logger.info(f"Business profile created successfully: {result}")
        return {
            "status": "success",
            "message": f"Business profile created for {company}",
            "result": result.get("business_profile_result", {})
        }
    except Exception as e:
        logger.error(f"Failed to create business profile: {e}")
        return {"status": "error", "message": str(e)}


@tool
async def create_project_mcp(
    user_id: str,
    project_name: str
) -> Dict[str, Any]:
    """
    Create a project using the MCP workflow.
    Call this tool AFTER the user submits the project creation form.

    Args:
        user_id: Unique user identifier
        project_name: Name of the project to create

    Returns:
        Result of project creation from MCP server
    """
    try:
        logger.info(f"Creating project '{project_name}' for user: {user_id}")

        result = await run_onboarding_http_workflow.ainvoke({
            "user_id": user_id,
            "current_step": "project",
            "business_profile": None,
            "project": {
                "name": project_name,
                "user_id": user_id
            },
            "embedded_signup": None
        })

        logger.info(f"Project created successfully: {result}")
        return {
            "status": "success",
            "message": f"Project '{project_name}' created successfully",
            "result": result.get("project_result", {})
        }
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        return {"status": "error", "message": str(e)}


@tool
async def create_embedded_signup_mcp(
    business_name: str,
    business_email: str,
    display_name: str,
    category: str,
    city: str = "",
    country: str = "United States",
    description: str = ""
) -> Dict[str, Any]:
    """
    Create WhatsApp embedded signup using the MCP workflow.
    Call this tool AFTER the user submits the WhatsApp setup form.

    Args:
        business_name: Name of the WhatsApp Business
        business_email: Business email address
        display_name: Display name for WhatsApp
        category: Business category (e.g., 'Retail', 'Technology')
        city: City (optional)
        country: Country (default: United States)
        description: Business description (optional)

    Returns:
        Result of embedded signup creation from MCP server
    """
    try:
        logger.info(f"Creating embedded signup for business: {business_name}")

        result = await run_onboarding_http_workflow.ainvoke({
            "user_id": "system",
            "current_step": "embedded_signup",
            "business_profile": None,
            "project": None,
            "embedded_signup": {
                "business_name": business_name,
                "business_email": business_email,
                "phone_code": 1,
                "website": "",
                "street_address": "",
                "city": city,
                "state": "",
                "zip_postal": "",
                "country": country,
                "timezone": "UTC",
                "display_name": display_name,
                "category": category,
                "description": description
            }
        })

        logger.info(f"Embedded signup created successfully: {result}")
        return {
            "status": "success",
            "message": f"WhatsApp Business '{business_name}' setup complete",
            "result": result.get("embedded_signup_result", {})
        }
    except Exception as e:
        logger.error(f"Failed to create embedded signup: {e}")
        return {"status": "error", "message": str(e)}


# Backend tools list - includes MCP workflow tools
backend_tools = [
    get_weather,
    create_business_profile_mcp,
    create_project_mcp,
    create_embedded_signup_mcp,
]

backend_tool_names = [t.name for t in backend_tools]


# ============================================
# Chat Node - using Command pattern from test_agentic_ui
# ============================================

async def chat_node(state: AgentState, config: RunnableConfig) -> Command[str]:
    """Main chat node that processes messages and decides on tool calls."""

    # 1. Define the model - use temperature=0 for deterministic tool calling
    model = ChatOpenAI(model=settings.LLM_MODEL, api_key=settings.OPENAI_API_KEY, temperature=0)

    # 2. Get frontend tools from CopilotKit
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    print(f"🔵 [BACKEND] CopilotKit actions count: {len(copilotkit_actions)}")

    for action in copilotkit_actions:
        action_name = getattr(action, 'name', None) or (action.get('name') if isinstance(action, dict) else 'unknown')
        print(f"   - Frontend tool: {action_name}")

    # 3. Bind the tools to the model (both frontend and backend tools)
    model_with_tools = model.bind_tools(
        [
            *copilotkit_actions,  # Frontend tools first
            *backend_tools,        # Backend tools second
        ],
        parallel_tool_calls=False,
    )

    # 4. Build context from current state
    onboarding_step = state.get("onboarding_step") or "not_started"

    # 5. Define the system message - focus on tool calling
    system_message = SystemMessage(
        content=f"""You are an onboarding assistant. You MUST use tools to show forms and create resources.

FRONTEND TOOLS (show forms to user):
- show_onboarding_business_profile_form(): Shows business profile form to user
- show_onboarding_project_form(company): Shows project creation form
- show_onboarding_embedded_signup_form(project_name): Shows WhatsApp setup form
- show_onboarding_success(company, project_name, business_name, category): Shows success message

BACKEND TOOLS (create resources via MCP):
- create_business_profile_mcp(...): Creates business profile in database
- create_project_mcp(user_id, project_name): Creates project in database
- create_embedded_signup_mcp(...): Creates WhatsApp embedded signup

WORKFLOW:
1. User says "Start user onboarding process"
   -> CALL show_onboarding_business_profile_form()

2. User submits "Business profile submitted: company=X, email=Y, display_name=Z..."
   -> First CALL create_business_profile_mcp(user_id="user123", display_name=Z, email=Y, company=X, ...)
   -> Then CALL show_onboarding_project_form(company=X)

3. User submits "Project created: name=X..."
   -> First CALL create_project_mcp(user_id="user123", project_name=X)
   -> Then CALL show_onboarding_embedded_signup_form(project_name=X)

4. User submits "WhatsApp setup completed: business_name=X, category=Y..."
   -> First CALL create_embedded_signup_mcp(business_name=X, business_email=..., display_name=..., category=Y)
   -> Then CALL show_onboarding_success(company, project_name, business_name, category)

IMPORTANT:
- When form data is submitted, FIRST call the MCP backend tool to save data, THEN show the next form
- Extract all parameters from the user message when calling MCP tools
- Use "user123" as user_id for now

Current step: {onboarding_step}
"""
    )

    # 6. Run the model
    response = await model_with_tools.ainvoke(
        [
            system_message,
            *state["messages"],
        ],
        config,
    )

    # 7. Route to tool node if any backend tool is called
    if route_to_tool_node(response):
        return Command(
            goto="tool_node",
            update={
                "messages": [response],
            },
        )

    # 8. End the graph if no backend tool calls
    return Command(
        goto=END,
        update={
            "messages": [response],
        },
    )


def route_to_tool_node(response: BaseMessage) -> bool:
    """Route to tool node if any tool call matches a backend tool."""
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls:
        return False

    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        if tool_name in backend_tool_names:
            print(f"🔧 [BACKEND] Tool called: {tool_name} - routing to tool_node")
            return True
    return False


# ============================================
# Workflow Graph
# ============================================

workflow = StateGraph(AgentState)
workflow.add_node("chat_node", chat_node)
workflow.add_node("tool_node", ToolNode(tools=backend_tools))

# Tool node always loops back to chat_node for response
workflow.add_edge("tool_node", "chat_node")
workflow.set_entry_point("chat_node")

graph = workflow.compile()
