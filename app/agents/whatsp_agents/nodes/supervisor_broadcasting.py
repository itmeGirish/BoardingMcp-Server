"""
Graph node functions for broadcasting supervisor workflow

This module contains ONLY the pure node functions.
No routing logic, no imports of tools/prompts/graph.
Just the executable node functions.

Routing supports:
- tool_node: Standard backend tool execution
- Sub-agent delegation: Routes to sub-agent graphs (data_processing, etc.)
- END: No more tool calls
"""

from langchain_core.messages import SystemMessage, ToolMessage
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
    tool_names_set: set,
    delegation_tool_map: dict = None
):
    """
    Call the language model node for broadcasting supervisor.

    This is a PURE node function that:
    1. Takes state and dependencies as parameters
    2. Calls the model with system prompt + conversation history
    3. Binds CopilotKit frontend actions + backend tools
    4. Returns Command for routing based on tool calls

    Routing priority:
    1. If a delegation tool is called -> route to the corresponding sub-agent node
    2. If a backend tool is called -> route to tool_node
    3. Otherwise -> route to END

    Args:
        state: Current agent state (BroadcastingAgentState)
        config: Runnable configuration
        system_prompt: Broadcasting system prompt
        tools: List of backend tools to bind to model
        tool_names_set: Set of backend tool names for routing
        delegation_tool_map: Dict mapping delegation tool names to sub-agent node names
                             e.g., {"delegate_to_data_processing": "data_processing"}

    Returns:
        Command specifying next node (tool_node, sub-agent node, or END)
    """
    if delegation_tool_map is None:
        delegation_tool_map = {}

    recent_messages = state["messages"][-2:] if len(state["messages"]) > 2 else state["messages"]
    logger.info(f"[Broadcasting] Call model with {len(state['messages'])} messages, last 2:")
    for i, msg in enumerate(recent_messages):
        msg_type = type(msg).__name__
        content_preview = str(getattr(msg, 'content', ''))[:150]
        logger.info(f"  [{i}] {msg_type}: {content_preview}")

    system_message = SystemMessage(content=system_prompt)
    messages = [system_message] + state["messages"]

    # Get frontend tools (CopilotKit actions) from state
    copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
    logger.info(f"CopilotKit actions count: {len(copilotkit_actions)}")

    for action in copilotkit_actions:
        action_name = getattr(action, 'name', None) or (action.get('name') if isinstance(action, dict) else 'unknown')
        logger.info(f"  - Frontend tool: {action_name}")

    # Create model with ALL tools (frontend + backend)
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    all_tools = [*copilotkit_actions, *tools]
    model_with_tools = model.bind_tools(all_tools, parallel_tool_calls=False)

    try:
        response = await model_with_tools.ainvoke(messages, config)
        logger.info("[Broadcasting] Model response received successfully")
    except Exception as e:
        logger.error(f"[Broadcasting] Model invocation failed: {e}", exc_info=True)
        raise

    # Check for tool calls and determine routing
    tool_calls = getattr(response, "tool_calls", None)

    if tool_calls:
        tool_call_names = [tc.get("name") for tc in tool_calls]
        logger.info(f"[Broadcasting] Tool calls: {tool_call_names}")

        # Priority 1: Check for delegation tool calls -> route to sub-agent
        for tc in tool_calls:
            tc_name = tc.get("name")
            if tc_name in delegation_tool_map:
                target_agent = delegation_tool_map[tc_name]
                logger.info(f"[Broadcasting] Delegating to sub-agent: {target_agent}")
                # Execute the delegation tool first (via tool_node), then route to sub-agent
                return Command(
                    goto="tool_node",
                    update={"messages": [response]},
                )

        # Priority 2: Check for backend tool calls -> route to tool_node
        has_backend_tool_calls = any(
            tc.get("name") in tool_names_set
            for tc in tool_calls
        )

        if has_backend_tool_calls:
            logger.info("[Broadcasting] Routing to tool_node (backend tools)")
            return Command(
                goto="tool_node",
                update={"messages": [response]},
            )

    # No tool calls -> END
    logger.info("[Broadcasting] Routing to END")
    return Command(
        goto=END,
        update={"messages": [response]},
    )


# ============================================
# NODE: ROUTE AFTER TOOL
# ============================================

def route_after_tool(state, delegation_tool_map: dict = None):
    """
    Route after tool_node execution.

    Checks if the last tool call was a delegation tool.
    If so, routes to the corresponding sub-agent node.
    Otherwise, routes back to call_model.

    Args:
        state: Current agent state
        delegation_tool_map: Dict mapping delegation tool names to sub-agent node names

    Returns:
        str: Next node name ("call_model" or sub-agent name)
    """
    if not delegation_tool_map:
        return "call_model"

    # Only check the most recent contiguous block of ToolMessages.
    # Break as soon as we hit a non-ToolMessage (AIMessage, HumanMessage, etc.)
    # This prevents re-routing to old delegation tools from earlier in history.
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, ToolMessage):
            if msg.name in delegation_tool_map:
                target = delegation_tool_map[msg.name]
                logger.info(f"[Broadcasting] Post-tool routing to sub-agent: {target}")
                return target
        else:
            # Hit a non-tool message, stop searching
            break

    return "call_model"


__all__ = [
    "call_model_node",
    "route_after_tool",
]
