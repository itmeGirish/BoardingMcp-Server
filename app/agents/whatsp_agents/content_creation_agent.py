# Content Creation Agent - Entry Point
# Assembles the graph via functools.partial dependency injection
from functools import partial
from .graphs.content_creation import create_graph
from .states.content_creation import ContentCreationAgentState
from .prompts.content_creation import CONTENT_CREATION_SYSTEM_PROMPT
from .tools.content_creation import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from .nodes.content_creation import call_model_node


def _create_call_model_node_with_dependencies():
    return partial(
        call_model_node,
        system_prompt=CONTENT_CREATION_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES
    )


def _assemble_graph():
    return create_graph(
        state_class=ContentCreationAgentState,
        call_model_node_func=_create_call_model_node_with_dependencies(),
        tools=BACKEND_TOOLS
    )


# Create singleton - can be referenced as sub-agent by supervisor
content_creation_graph = _assemble_graph()
