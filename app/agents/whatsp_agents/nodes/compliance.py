"""
Graph node functions for Compliance Agent.

Pure node functions for the compliance sub-graph.
Same pattern as data_processing and supervisor_broadcasting agents.
"""

from langchain_core.messages import SystemMessage
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
    Call the language model node for compliance agent.

    Args:
        state: Current agent state (ComplianceAgentState)
        config: Runnable configuration
        system_prompt: Compliance system prompt
        tools: List of backend tools to bind to model
        tool_names_set: Set of backend tool names for routing

    Returns:
        Command specifying next node (tool_node or END)
    """
    recent_messages = state["messages"][-2:] if len(state["messages"]) > 2 else state["messages"]
    logger.info(f"[Compliance] Call model with {len(state['messages'])} messages, last 2:")
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
        logger.info("[Compliance] Model response received successfully")
    except Exception as e:
        logger.error(f"[Compliance] Model invocation failed: {e}", exc_info=True)
        raise

    # Check for tool calls
    tool_calls = getattr(response, "tool_calls", None)
    has_backend_tool_calls = False

    if tool_calls:
        logger.info(f"[Compliance] Tool calls: {[tc.get('name') for tc in tool_calls]}")
        has_backend_tool_calls = any(
            tc.get("name") in tool_names_set
            for tc in tool_calls
        )

    # Route based on tool calls
    if has_backend_tool_calls:
        logger.info("[Compliance] Routing to tool_node (backend tools)")
        return Command(
            goto="tool_node",
            update={"messages": [response]},
        )
    else:
        logger.info("[Compliance] Routing to END")
        return Command(
            goto=END,
            update={"messages": [response]},
        )


__all__ = [
    "call_model_node",
]
