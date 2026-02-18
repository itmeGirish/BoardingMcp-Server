"""LangGraph workflow structure for Drafting sub-agent. Topology only."""
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from ....config import logger


def create_graph(state_class, call_model_node_func, tools):
    """Create drafting graph: START -> call_model -> [tool_node -> call_model] -> END"""
    logger.info("Creating Drafting graph structure...")
    workflow = StateGraph(state_class)
    workflow.add_node("call_model", call_model_node_func)
    workflow.add_node("tool_node", ToolNode(tools=tools))
    workflow.set_entry_point("call_model")
    workflow.add_edge("tool_node", "call_model")
    graph = workflow.compile()
    logger.info("Drafting graph created successfully")
    return graph
