"""
This is the main entry point for the agent.
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

    
backend_tools = [get_weather,run_onboarding_http_workflow]
backend_tool_names = [tool.name for tool in backend_tools]


async def chat_node(state: AgentState, config: RunnableConfig) -> Command[str]:
    """Chat node that uses the LLM with tools."""
    model = ChatOpenAI(model=settings.LLM_MODEL,api_key=settings.OPENAI_API_KEY)

    model_with_tools = model.bind_tools(
        [
            *state.get("copilotkit", {}).get("actions", []),
            *backend_tools,
        ],
        parallel_tool_calls=False,
    )

    system_message = SystemMessage(
        content=f"""You are a helpful assistant on Onboarding the Business . The current proverbs are {state.get('proverbs', [])}.

Your needs use workflow tool for onboarding process.
1. Use to get the onboarding workflow tool to onboard a business.
  
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

