# Compliance Agent - Entry Point
# Assembles the graph via functools.partial dependency injection
from functools import partial
from .graphs.compliance import create_graph
from .states.compliance import ComplianceAgentState
from .prompts.compliance import COMPLIANCE_SYSTEM_PROMPT
from .tools.compliance import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from .nodes.compliance import call_model_node


def _create_call_model_node_with_dependencies():
    return partial(
        call_model_node,
        system_prompt=COMPLIANCE_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES
    )


def _assemble_graph():
    return create_graph(
        state_class=ComplianceAgentState,
        call_model_node_func=_create_call_model_node_with_dependencies(),
        tools=BACKEND_TOOLS
    )


# Create singleton - can be referenced as sub-agent by supervisor
compliance_graph = _assemble_graph()
