# Broadcasting Supervisor Agent - Entry Point
# Assembles the graph via functools.partial dependency injection
# Connects sub-agents (data_processing, etc.) as sub-graph nodes
from functools import partial
from .graphs.supervisor_broadcasting import create_graph
from .states.supervisor_broadcasting import BroadcastingAgentState
from .prompts.supervisor_broadcasting import BROADCASTING_SYSTEM_PROMPT
from .tools.supervisor_broadcasting import BACKEND_TOOLS, BACKEND_TOOL_NAMES, DELEGATION_TOOL_MAP
from .nodes.supervisor_broadcasting import call_model_node, route_after_tool

# Import sub-agent graphs
from .data_processing_agent import data_processing_graph
from .compliance_agent import compliance_graph
from .segmentation_agent import segmentation_graph
from .content_creation_agent import content_creation_graph
from .delivery_agent import delivery_graph


def _create_call_model_node_with_dependencies():
    return partial(
        call_model_node,
        system_prompt=BROADCASTING_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES,
        delegation_tool_map=DELEGATION_TOOL_MAP,
    )


def _create_route_after_tool_func():
    return partial(
        route_after_tool,
        delegation_tool_map=DELEGATION_TOOL_MAP,
    )


def _assemble_graph():
    # Sub-agents connected to the supervisor
    # Add new agents here as they are created:
    #   "compliance": compliance_graph,
    #   "segmentation": segmentation_graph,
    #   etc.
    sub_agents = {
        "data_processing": data_processing_graph,
        "compliance": compliance_graph,
        "segmentation": segmentation_graph,
        "content_creation": content_creation_graph,
        "delivery": delivery_graph,
    }

    return create_graph(
        state_class=BroadcastingAgentState,
        call_model_node_func=_create_call_model_node_with_dependencies(),
        tools=BACKEND_TOOLS,
        route_after_tool_func=_create_route_after_tool_func(),
        sub_agents=sub_agents,
    )


# Create singleton - referenced in langgraph.json as:
# "broadcasting_agent": "app.agents.whatsp_agents.whatsp_broadcasting:broadcasting_graph"
broadcasting_graph = _assemble_graph()
