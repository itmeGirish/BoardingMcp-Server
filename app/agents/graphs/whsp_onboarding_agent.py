"""
LangGraph workflow structure definition

This module contains ONLY the graph structure.
No node logic, no tool imports.
Just the graph topology.
"""

import logging
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from ...config import logger


# ============================================
# GRAPH FACTORY
# ============================================

def create_graph(state_class, call_model_node_func, tools):
    """
    Create the workflow graph structure.
    
    This function ONLY defines the graph structure:
    - Which nodes exist
    - How they connect
    - Entry and exit points
    
    Args:
        state_class: State class for the graph
        call_model_node_func: The call_model node function
        tools: List of tools for the tool node
    
    Returns:
        Compiled graph instance
    
    Graph Structure:
        START → call_model → [tool_node → call_model] → END
    """
    logger.info("Creating graph structure...")
    
    # Initialize workflow
    workflow = StateGraph(state_class)
    
    # Add nodes
    workflow.add_node("call_model", call_model_node_func)
    workflow.add_node("tool_node", ToolNode(tools=tools))
    
    # Define edges
    workflow.set_entry_point("call_model")
    workflow.add_edge("tool_node", "call_model")
    
    # Compile
    graph = workflow.compile()
    
    logger.info("Graph structure created successfully")
    return graph


__all__ = [
    "create_graph",
]