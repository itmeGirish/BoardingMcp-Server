# Data Processing Agent - Entry Point
# Assembles the graph via functools.partial dependency injection
from functools import partial
from .graphs.data_processing import create_graph
from .states.data_processing import DataProcessingAgentState
from .prompts.data_processing import DATA_PROCESSING_SYSTEM_PROMPT
from .tools.data_processing import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from .nodes.data_processing import call_model_node


def _create_call_model_node_with_dependencies():
    return partial(
        call_model_node,
        system_prompt=DATA_PROCESSING_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES
    )


def _assemble_graph():
    return create_graph(
        state_class=DataProcessingAgentState,
        call_model_node_func=_create_call_model_node_with_dependencies(),
        tools=BACKEND_TOOLS
    )


# Create singleton - can be referenced in langgraph.json as:
# "data_processing_agent": "app.agents.whatsp_agents.data_processing_agent:data_processing_graph"
data_processing_graph = _assemble_graph()
