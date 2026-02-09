# Delivery Agent - Entry Point
# Assembles the graph via functools.partial dependency injection
# Business Policy: send_marketing_lite_message FIRST, fallback to send_message
from functools import partial
from .graphs.delivery import create_graph
from .states.delivery import DeliveryAgentState
from .prompts.delivery import DELIVERY_SYSTEM_PROMPT
from .tools.delivery import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from .nodes.delivery import call_model_node


def _create_call_model_node_with_dependencies():
    return partial(
        call_model_node,
        system_prompt=DELIVERY_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES
    )


def _assemble_graph():
    return create_graph(
        state_class=DeliveryAgentState,
        call_model_node_func=_create_call_model_node_with_dependencies(),
        tools=BACKEND_TOOLS
    )


# Create singleton - can be referenced as sub-agent by supervisor
delivery_graph = _assemble_graph()
