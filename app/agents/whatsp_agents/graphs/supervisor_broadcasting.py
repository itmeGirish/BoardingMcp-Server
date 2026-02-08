"""
LangGraph workflow structure for broadcasting supervisor

This module contains ONLY the graph structure.
No node logic, no tool imports.
Just the graph topology.

Graph Structure (with sub-agents):
    START -> call_model -> [tool_node -> route_after_tool -> call_model | sub-agent] -> END
                                                              |
                                                              v
                                                        data_processing -> call_model
                                                        (future agents) -> call_model
"""

from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from ....config import logger


# ============================================
# GRAPH FACTORY
# ============================================

def create_graph(
    state_class,
    call_model_node_func,
    tools,
    route_after_tool_func=None,
    sub_agents: dict = None,
):
    """
    Create the broadcasting supervisor workflow graph.

    Supports sub-agent delegation: when a delegation tool is called,
    the graph routes to the corresponding sub-agent graph instead of
    back to call_model.

    Args:
        state_class: BroadcastingAgentState class
        call_model_node_func: The call_model node function (with deps injected)
        tools: List of backend tools for the tool node
        route_after_tool_func: Optional routing function for post-tool routing
                               (determines if we go to call_model or a sub-agent)
        sub_agents: Dict of {node_name: compiled_graph} for sub-agent nodes
                    e.g., {"data_processing": data_processing_graph}

    Returns:
        Compiled graph instance
    """
    logger.info("Creating broadcasting supervisor graph structure...")

    workflow = StateGraph(state_class)

    # Core nodes
    workflow.add_node("call_model", call_model_node_func)
    workflow.add_node("tool_node", ToolNode(tools=tools))

    # Add sub-agent nodes
    if sub_agents:
        for agent_name, agent_graph in sub_agents.items():
            workflow.add_node(agent_name, agent_graph)
            # After sub-agent completes, return to supervisor call_model
            workflow.add_edge(agent_name, "call_model")
            logger.info(f"  Sub-agent registered: {agent_name}")

    # Entry point
    workflow.set_entry_point("call_model")

    # Routing after tool_node
    if route_after_tool_func and sub_agents:
        # Conditional routing: tool_node -> call_model OR sub-agent
        possible_targets = ["call_model"] + list(sub_agents.keys())
        workflow.add_conditional_edges(
            "tool_node",
            route_after_tool_func,
            possible_targets,
        )
        logger.info(f"  Conditional routing from tool_node: {possible_targets}")
    else:
        # Simple routing: tool_node -> call_model
        workflow.add_edge("tool_node", "call_model")

    # Compile
    graph = workflow.compile()

    logger.info("Broadcasting supervisor graph created successfully")
    return graph


__all__ = [
    "create_graph",
]
