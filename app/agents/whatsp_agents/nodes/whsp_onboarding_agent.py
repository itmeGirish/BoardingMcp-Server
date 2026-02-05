"""
Graph node functions for onboarding workflow

This module contains ONLY the pure node functions.
No routing logic, no imports of tools/prompts/graph.
Just the executable node functions.
"""

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.types import Command
from ....config import logger


# ============================================
# NODE: CALL MODEL
# ============================================

async def call_model_node(
    state,
    config: RunnableConfig,
    system_prompt: str,
    tools: list,
    tool_names_set: set
):
    """
    Call the language model node.

    This is a PURE node function that:
    1. Takes state and dependencies as parameters
    2. Calls the model
    3. Returns Command for routing

    Args:
        state: Current agent state
        config: Runnable configuration
        system_prompt: System prompt to use
        tools: List of tools to bind to model
        tool_names_set: Set of tool names for routing

    Returns:
        Command specifying next node
    """
    # Log recent messages to debug tool results
    recent_messages = state["messages"][-2:] if len(state["messages"]) > 2 else state["messages"]
    logger.info(f"📨 Call model with {len(state['messages'])} messages, last 2:")
    for i, msg in enumerate(recent_messages):
        msg_type = type(msg).__name__
        content_preview = str(getattr(msg, 'content', ''))[:150]
        logger.info(f"  [{i}] {msg_type}: {content_preview}")

    # Prepare system message
    system_message = SystemMessage(content=system_prompt)

    # Combine with conversation history
    messages = [system_message] + state["messages"]

    # Get frontend tools (CopilotKit actions) from state
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    logger.info(f"CopilotKit actions count: {len(copilotkit_actions)}")

    for action in copilotkit_actions:
        action_name = getattr(action, 'name', None) or (action.get('name') if isinstance(action, dict) else 'unknown')
        logger.info(f"  - Frontend tool: {action_name}")

    # Create model with ALL tools (backend + frontend)
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    all_tools = [*copilotkit_actions, *tools]  # Frontend first, backend second
    model_with_tools = model.bind_tools(all_tools, parallel_tool_calls=False)

    # Invoke model
    try:
        response = await model_with_tools.ainvoke(messages, config)
        logger.info("Model response received successfully")
        logger.info(f"Response type: {type(response)}")
        logger.info(f"Response has content: {hasattr(response, 'content')}")

    except Exception as e:
        logger.error(f"Model invocation failed: {e}", exc_info=True)
        raise

    # Check for tool calls
    tool_calls = getattr(response, "tool_calls", None)
    has_backend_tool_calls = False

    if tool_calls:
        logger.info(f"Tool calls made: {[tc.get('name') for tc in tool_calls]}")
        # Check if any tool call is for backend tools
        has_backend_tool_calls = any(
            tc.get("name") in tool_names_set
            for tc in tool_calls
        )

    # Route based on tool calls
    if has_backend_tool_calls:
        logger.info("Routing to tool_node (backend tools)")
        return Command(
            goto="tool_node",
            update={"messages": [response]},
        )
    else:
        logger.info("Routing to END (no backend tools or frontend tools only)")
        logger.info(f"Final response content: {response.content[:200] if hasattr(response, 'content') else 'NO CONTENT'}")
        logger.info(f"Final response tool_calls: {response.tool_calls if hasattr(response, 'tool_calls') else 'NO TOOL CALLS'}")
        return Command(
            goto=END,
            update={"messages": [response]},
        )


# ============================================
# EXPORTS
# ============================================

__all__ = [
    "call_model_node",
]
