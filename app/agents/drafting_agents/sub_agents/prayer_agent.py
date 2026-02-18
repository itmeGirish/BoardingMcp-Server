"""Prayer Agent assembly — partial dependency injection."""
from functools import partial
from ..graphs.prayer import create_graph
from ..states.legal_drafting import LegalDraftingState
from ..prompts.prayer import PRAYER_SYSTEM_PROMPT
from ..tools.prayer import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from ..nodes.prayer import call_model_node


def _create_call_model_node():
    return partial(
        call_model_node,
        system_prompt=PRAYER_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES,
    )


def _assemble_graph():
    return create_graph(
        state_class=LegalDraftingState,
        call_model_node_func=_create_call_model_node(),
        tools=BACKEND_TOOLS,
    )


prayer_graph = _assemble_graph()
