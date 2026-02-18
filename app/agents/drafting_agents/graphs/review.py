"""LangGraph workflow structure for Review sub-agent. Topology only."""
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from ....config import logger


def create_graph(state_class, call_model_node_func, tools):
    """Create review graph: START -> call_model -> [tool_node -> call_model] -> END"""
    logger.info("Creating Review graph structure...")
    workflow = StateGraph(state_class)
    workflow.add_node("call_model", call_model_node_func)
    workflow.add_node("tool_node", ToolNode(tools=tools))
    workflow.set_entry_point("call_model")
    workflow.add_edge("tool_node", "call_model")
    graph = workflow.compile()
    logger.info("Review graph created successfully")
    return graph
