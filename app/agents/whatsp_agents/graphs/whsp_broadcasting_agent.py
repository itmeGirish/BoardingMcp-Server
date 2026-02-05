"""
LangGraph workflow structure definition for broadcasting

This module defines the graph topology for the broadcasting pipeline.

Graph Structure:
    START → call_model → [tool_node → call_model] → data_processing_node
            → segmentation_node → content_creation_node → compliance_node
            → delivery_node → analytics_node → END

The call_model node handles initial memory loading and verification via tools.
Once the LLM decides to proceed, the 6 pipeline nodes execute sequentially.
"""

from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from ....config import logger


# ============================================
# GRAPH FACTORY
# ============================================

def create_graph(state_class, call_model_node_func, tools, pipeline_nodes=None):
    """
    Create the broadcasting workflow graph structure.

    Args:
        state_class: State class for the graph
        call_model_node_func: The call_model node function (LLM orchestrator)
        tools: List of tools for the tool node
        pipeline_nodes: Dict of pipeline node functions (6 broadcasting steps)

    Returns:
        Compiled graph instance
    """
    logger.info("[BROADCASTING] Creating graph structure...")

    workflow = StateGraph(state_class)

    # Add LLM orchestrator + tool nodes
    workflow.add_node("call_model", call_model_node_func)
    workflow.add_node("tool_node", ToolNode(tools=tools))

    # Add 6 broadcasting pipeline nodes
    if pipeline_nodes:
        workflow.add_node("data_processing_node", pipeline_nodes["data_processing_node"])
        workflow.add_node("segmentation_node", pipeline_nodes["segmentation_node"])
        workflow.add_node("content_creation_node", pipeline_nodes["content_creation_node"])
        workflow.add_node("compliance_node", pipeline_nodes["compliance_node"])
        workflow.add_node("delivery_node", pipeline_nodes["delivery_node"])
        workflow.add_node("analytics_node", pipeline_nodes["analytics_node"])

    # Define edges
    workflow.set_entry_point("call_model")
    workflow.add_edge("tool_node", "call_model")

    # Pipeline edges are defined inside each node via Command(goto=...)
    # data_processing_node → segmentation_node → content_creation_node
    # → compliance_node → delivery_node → analytics_node → END

    # Compile
    graph = workflow.compile()

    logger.info("[BROADCASTING] Graph structure created successfully")
    logger.info("[BROADCASTING] Nodes: call_model, tool_node, data_processing_node, "
                "segmentation_node, content_creation_node, compliance_node, "
                "delivery_node, analytics_node")
    return graph


__all__ = [
    "create_graph",
]
