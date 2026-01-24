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
from ...config import logger


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
    # Prepare system message
    system_message = SystemMessage(content=system_prompt)
    
    # Combine with conversation history
    messages = [system_message] + state["messages"]
    
    # Create model with tools
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    model_with_tools = model.bind_tools(tools, parallel_tool_calls=True)
    
    # Invoke model
    response = await model_with_tools.ainvoke(messages, config)
    
    logger.debug("Model response received")
    
    # Check for tool calls
    tool_calls = getattr(response, "tool_calls", None)
    has_backend_tool_calls = False
    
    if tool_calls:
        # Check if any tool call is for backend tools
        has_backend_tool_calls = any(
            tc.get("name") in tool_names_set 
            for tc in tool_calls
        )
    
    # Route based on tool calls
    if has_backend_tool_calls:
        logger.info("Routing to tool_node")
        return Command(
            goto="tool_node",
            update={"messages": [response]},
        )
    else:
        logger.info("Routing to END")
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