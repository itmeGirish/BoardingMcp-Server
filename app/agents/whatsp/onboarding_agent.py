"""
This is the main entry point for the agent.
Onboarding workflow with step-by-step frontend forms.
The agent uses frontend tools (show_onboarding_*) to display forms and collect data.
"""
from typing import List
from copilotkit import CopilotKitState
from langchain.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from ...config import settings


class AgentState(CopilotKitState):
    proverbs: List[str]


@tool
def get_weather(location: str):
    """Get the weather for a given location."""
    return f"The weather for {location} is 70 degrees."


@tool
def show_onboarding_business_profile_form():
    """Display the business profile form to collect company information. Call this when user wants to start onboarding."""
    return "Business profile form displayed. Please fill in your business details."


@tool
def show_onboarding_project_form(company: str = ""):
    """Display the project creation form after business profile is complete. Call this after receiving business profile data."""
    return f"Project form displayed for company: {company}. Please enter your project name."


@tool
def show_onboarding_embedded_signup_form(project_name: str = ""):
    """Display the WhatsApp embedded signup form after project is created. Call this after receiving project data."""
    return f"WhatsApp setup form displayed for project: {project_name}. Please complete the WhatsApp Business setup."


@tool
def show_onboarding_success(company: str = "", project_name: str = "", business_name: str = "", category: str = ""):
    """Display the onboarding success message. Call this after all WhatsApp setup data is received."""
    return f"Onboarding complete! Company: {company}, Project: {project_name}, Business: {business_name}, Category: {category}"


# Backend tools that the LLM can call - these will be rendered by frontend useRenderToolCall
backend_tools = [
    get_weather,
    show_onboarding_business_profile_form,
    show_onboarding_project_form,
    show_onboarding_embedded_signup_form,
    show_onboarding_success,
]
backend_tool_names = [tool.name for tool in backend_tools]


def route_after_chat(response: BaseMessage) -> str:
    """
    Route based on tool calls:
    - If tool call is get_weather -> go to tool_node (execute on backend)
    - If tool call is show_onboarding_* -> go to END (render on frontend via useRenderToolCall)
    - If no tool calls -> go to END
    """
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls:
        return END

    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")
        # Only route to tool_node for non-rendering backend tools (like get_weather)
        # The show_onboarding_* tools are rendered by frontend, so go to END
        if tool_name == "get_weather":
            print(f"Routing to tool_node for backend tool: {tool_name}")
            return "tool_node"
        elif tool_name.startswith("show_onboarding"):
            print(f"Frontend render tool called: {tool_name} - ending graph for frontend to render")
            return END

    # Unknown tools - end
    print(f"Unknown tool call, ending graph execution")
    return END


async def chat_node(state: AgentState, config: RunnableConfig) -> dict:
    """Chat node that uses the LLM with tools - returns dict instead of Command."""
    model = ChatOpenAI(model=settings.LLM_MODEL, api_key=settings.OPENAI_API_KEY)

    # Get frontend tools from CopilotKit
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    print(f"🔵 [BACKEND] CopilotKit actions count: {len(copilotkit_actions)}")

    # Debug: Print the names of available frontend tools
    for action in copilotkit_actions:
        action_name = getattr(action, 'name', None) or (action.get('name') if isinstance(action, dict) else 'unknown')
        print(f"   - Frontend tool: {action_name}")

    model_with_tools = model.bind_tools(
        [
            *copilotkit_actions,  # Frontend tools first
            *backend_tools,        # Backend tools second
        ],
        parallel_tool_calls=False,
    )

    system_message = SystemMessage(
        content="""You are a helpful assistant for onboarding businesses to WhatsApp Business API.

## IMPORTANT: You have access to frontend tools that display forms in the user's browser.

## Available Frontend Tools (use these for onboarding):
- show_onboarding_business_profile_form: Display the business profile form (Step 1)
- show_onboarding_project_form: Display the project creation form (Step 2) - takes optional "company" parameter
- show_onboarding_embedded_signup_form: Display WhatsApp setup form (Step 3) - takes optional "project_name" parameter
- show_onboarding_success: Display success message (Step 4) - takes optional "company", "project_name", "business_name", "category" parameters

## Onboarding Workflow - FOLLOW THIS EXACTLY:

When a user says "Start user onboarding process" or wants to start onboarding:

### Step 1: Business Profile
- IMMEDIATELY call the tool `show_onboarding_business_profile_form` (no parameters needed)
- Say "Let me show you the business profile form to get started."
- Wait for user to submit

### Step 2: Project Creation
- When user submits with "Business profile submitted: ..."
- Call `show_onboarding_project_form` with company parameter from the submission
- Say "Great! Now let's create your project."

### Step 3: WhatsApp Setup
- When user submits with "Project created: ..."
- Call `show_onboarding_embedded_signup_form` with project_name parameter
- Say "Excellent! Final step - let's set up your WhatsApp Business."

### Step 4: Complete
- When user submits with "WhatsApp setup completed: ..."
- Call `show_onboarding_success` with all collected data
- Congratulate the user!

## CRITICAL:
- Always call the frontend tools - they will render forms in the user's browser
- Do NOT skip steps - follow the sequence exactly
- Parse user submissions to extract data for next step
"""
    )

    response = await model_with_tools.ainvoke(
        [
            system_message,
            *state["messages"],
        ],
        config,
    )

    return {"messages": [response]}


workflow = StateGraph(AgentState)
workflow.add_node("chat_node", chat_node)
workflow.add_node("tool_node", ToolNode(tools=backend_tools))

# Conditional routing after chat_node
workflow.add_conditional_edges(
    "chat_node",
    lambda state: route_after_chat(state["messages"][-1]),
    {
        "tool_node": "tool_node",
        END: END,
    }
)

workflow.add_edge("tool_node", "chat_node")
workflow.set_entry_point("chat_node")

graph = workflow.compile()
