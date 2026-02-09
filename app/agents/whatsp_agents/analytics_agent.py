# Analytics & Optimization Agent - Entry Point
# Assembles the graph via functools.partial dependency injection
# Uses get_waba_analytics + get_messaging_health_status MCP tools
from functools import partial
from .graphs.analytics import create_graph
from .states.analytics import AnalyticsAgentState
from .prompts.analytics import ANALYTICS_SYSTEM_PROMPT
from .tools.analytics import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from .nodes.analytics import call_model_node


def _create_call_model_node_with_dependencies():
    return partial(
        call_model_node,
        system_prompt=ANALYTICS_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES
    )


def _assemble_graph():
    return create_graph(
        state_class=AnalyticsAgentState,
        call_model_node_func=_create_call_model_node_with_dependencies(),
        tools=BACKEND_TOOLS
    )


# Create singleton - can be referenced as sub-agent by supervisor
analytics_graph = _assemble_graph()
