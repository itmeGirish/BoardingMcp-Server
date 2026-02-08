"""
LangGraph workflow structure for Data Processing Agent.

Graph Structure:
    START -> call_model -> [tool_node -> call_model] -> END
"""

from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from ....config import logger


def create_graph(state_class, call_model_node_func, tools):
    """
    Create the data processing agent workflow graph.

    Args:
        state_class: DataProcessingAgentState class
        call_model_node_func: The call_model node function (with deps injected)
        tools: List of backend tools for the tool node

    Returns:
        Compiled graph instance
    """
    logger.info("Creating data processing agent graph structure...")

    workflow = StateGraph(state_class)

    # Add nodes
    workflow.add_node("call_model", call_model_node_func)
    workflow.add_node("tool_node", ToolNode(tools=tools))

    # Define edges
    workflow.set_entry_point("call_model")
    workflow.add_edge("tool_node", "call_model")

    # Compile
    graph = workflow.compile()

    logger.info("Data processing agent graph created successfully")
    return graph


__all__ = [
    "create_graph",
]
