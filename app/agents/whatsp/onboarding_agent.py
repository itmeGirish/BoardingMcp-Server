"""
This is the main entry point for the agent.
Onboarding workflow with step-by-step frontend forms.
"""
from typing import List
from copilotkit import CopilotKitState
from langchain.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
import asyncio
import nest_asyncio
import concurrent.futures
import json
from ...workflows import run_onboarding_http_workflow
from ...config import settings

nest_asyncio.apply()


_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

class AgentState(CopilotKitState):
    proverbs: List[str]

@tool
def get_weather(location: str):
    """Get the weather for a given location."""
    return f"The weather for {location} is 70 degrees."


backend_tools = [get_weather, run_onboarding_http_workflow]
backend_tool_names = [tool.name for tool in backend_tools]


async def chat_node(state: AgentState, config: RunnableConfig) -> Command[str]:
    """Chat node that uses the LLM with tools."""
    model = ChatOpenAI(model=settings.LLM_MODEL, api_key=settings.OPENAI_API_KEY)

    model_with_tools = model.bind_tools(
        [
            *state.get("copilotkit", {}).get("actions", []),
            *backend_tools,
        ],
        parallel_tool_calls=False,
    )

    system_message = SystemMessage(
        content="""You are a helpful assistant for onboarding businesses to WhatsApp Business API.

## Onboarding Workflow - FOLLOW THIS EXACTLY:

When a user wants to start onboarding or says "Start user onboarding process", follow these steps IN ORDER:

### Step 1: Business Profile
- Call the frontend tool `show_onboarding_business_profile_form` to display the business profile form
- Wait for the user to submit the form with their business details (display_name, email, company, contact, timezone, currency, company_size)

### Step 2: Project Creation
- After receiving business profile data, call `show_onboarding_project_form` with the company name
- Wait for the user to submit the project name

### Step 3: WhatsApp Setup
- After receiving project data, call `show_onboarding_embedded_signup_form` with the project name
- Wait for the user to submit the WhatsApp business setup details

### Step 4: Complete
- After receiving all WhatsApp setup data, call `show_onboarding_success` to show the completion screen
- Congratulate the user on completing the onboarding

## Important Rules:
1. ALWAYS use the frontend form tools (show_onboarding_*) for step-by-step data collection
2. Do NOT use run_onboarding_http_workflow directly - use the form tools instead
3. Each form must be shown one at a time in sequence
4. Parse the submitted data from user messages and pass relevant info to the next form tool
5. Be encouraging and helpful throughout the process

## Example Flow:
User: "Start user onboarding process"
Assistant: [calls show_onboarding_business_profile_form]

User: "Business profile submitted: display_name=John, email=john@company.com, company=Acme Inc..."
Assistant: [calls show_onboarding_project_form with company="Acme Inc"]

User: "Project created: name=WhatsApp Integration"
Assistant: [calls show_onboarding_embedded_signup_form with project_name="WhatsApp Integration"]

User: "WhatsApp setup completed: business_name=Acme, category=Technology..."
Assistant: [calls show_onboarding_success with all the collected data]
"""
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
