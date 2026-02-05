# ONLY this file imports everything:
from functools import partial
from .graphs.whsp_broadcasting_agent import create_graph
from .states.whsp_broadcasting_agent import BroadcastingAgentState
from .prompts.whsp_broadcasting_agent import BROADCASTING_SYSTEM_PROMPT
from .tools.whsp_broadcasting_agent import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from .nodes.whsp_broadcasting_agent import (
    call_model_node,
    data_processing_node,
    segmentation_node,
    content_creation_node,
    compliance_node,
    delivery_node,
    analytics_node,
)


# Wires everything together:
def _create_call_model_node_with_dependencies():
    return partial(
        call_model_node,
        system_prompt=BROADCASTING_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES
    )

def _assemble_graph():
    return create_graph(
        state_class=BroadcastingAgentState,
        call_model_node_func=_create_call_model_node_with_dependencies(),
        tools=BACKEND_TOOLS,
        pipeline_nodes={
            "data_processing_node": data_processing_node,
            "segmentation_node": segmentation_node,
            "content_creation_node": content_creation_node,
            "compliance_node": compliance_node,
            "delivery_node": delivery_node,
            "analytics_node": analytics_node,
        }
    )

# Create singleton
broadcasting_graph = _assemble_graph()
