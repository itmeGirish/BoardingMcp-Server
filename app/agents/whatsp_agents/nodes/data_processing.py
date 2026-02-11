"""
Graph node functions for Data Processing Agent.

Pure node functions for the data processing sub-graph.
Same pattern as supervisor_broadcasting and onboarding agents.
"""

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.types import Command
from ....config import logger

MAX_ITERATIONS = 15


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
    Call the language model node for data processing agent.

    Args:
        state: Current agent state (DataProcessingAgentState)
        config: Runnable configuration
        system_prompt: Data processing system prompt
        tools: List of backend tools to bind to model
        tool_names_set: Set of backend tool names for routing

    Returns:
        Command specifying next node (tool_node or END)
    """
    tool_message_count = sum(1 for msg in state["messages"] if isinstance(msg, ToolMessage))

    if tool_message_count >= MAX_ITERATIONS:
        logger.warning(f"[DataProcessing] Max iterations ({MAX_ITERATIONS}) reached. Forcing END.")
        return Command(goto=END, update={"messages": [AIMessage(content="Data processing complete. Maximum iteration limit reached.")]})

    recent_messages = state["messages"][-2:] if len(state["messages"]) > 2 else state["messages"]
    logger.info(f"[DataProcessing] Call model with {len(state['messages'])} messages, {tool_message_count} tool results, last 2:")
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
        logger.info("[DataProcessing] Model response received successfully")
    except Exception as e:
        logger.error(f"[DataProcessing] Model invocation failed: {e}", exc_info=True)
        raise

    # Check for tool calls
    tool_calls = getattr(response, "tool_calls", None)
    has_backend_tool_calls = False

    if tool_calls:
        logger.info(f"[DataProcessing] Tool calls: {[tc.get('name') for tc in tool_calls]}")
        has_backend_tool_calls = any(
            tc.get("name") in tool_names_set
            for tc in tool_calls
        )

    # Route based on tool calls
    if has_backend_tool_calls:
        logger.info("[DataProcessing] Routing to tool_node (backend tools)")
        return Command(
            goto="tool_node",
            update={"messages": [response]},
        )
    else:
        logger.info("[DataProcessing] Routing to END")
        return Command(
            goto=END,
            update={"messages": [response]},
        )


__all__ = [
    "call_model_node",
]
