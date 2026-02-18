"""Review Agent assembly — final quality check and delivery."""
from functools import partial
from ..graphs.review import create_graph
from ..states.legal_drafting import LegalDraftingState
from ..prompts.review import REVIEW_SYSTEM_PROMPT
from ..tools.review import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from ..nodes.review import call_model_node


def _create_call_model_node():
    return partial(
        call_model_node,
        system_prompt=REVIEW_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES,
    )


def _assemble_graph():
    return create_graph(
        state_class=LegalDraftingState,
        call_model_node_func=_create_call_model_node(),
        tools=BACKEND_TOOLS,
    )


review_graph = _assemble_graph()
