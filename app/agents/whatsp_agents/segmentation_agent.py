# Segmentation Agent - Entry Point
# Assembles the graph via functools.partial dependency injection
from functools import partial
from .graphs.segmentation import create_graph
from .states.segmentation import SegmentationAgentState
from .prompts.segmentation import SEGMENTATION_SYSTEM_PROMPT
from .tools.segmentation import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from .nodes.segmentation import call_model_node


def _create_call_model_node_with_dependencies():
    return partial(
        call_model_node,
        system_prompt=SEGMENTATION_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES
    )


def _assemble_graph():
    return create_graph(
        state_class=SegmentationAgentState,
        call_model_node_func=_create_call_model_node_with_dependencies(),
        tools=BACKEND_TOOLS
    )


# Create singleton - can be referenced as sub-agent by supervisor
segmentation_graph = _assemble_graph()
