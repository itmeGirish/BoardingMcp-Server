"""Drafting Agent assembly — dynamic document generation."""
from functools import partial
from ..graphs.drafting import create_graph
from ..states.legal_drafting import LegalDraftingState
from ..prompts.drafting import DRAFTING_SYSTEM_PROMPT
from ..tools.drafting import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from ..nodes.drafting import call_model_node


def _create_call_model_node():
    return partial(
        call_model_node,
        system_prompt=DRAFTING_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES,
    )


def _assemble_graph():
    return create_graph(
        state_class=LegalDraftingState,
        call_model_node_func=_create_call_model_node(),
        tools=BACKEND_TOOLS,
    )


drafting_graph = _assemble_graph()
