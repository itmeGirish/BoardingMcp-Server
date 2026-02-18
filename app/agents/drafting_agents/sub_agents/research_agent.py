"""Research Agent assembly — Deep Search with web search + RAG + LLM."""
from functools import partial
from ..graphs.research import create_graph
from ..states.legal_drafting import LegalDraftingState
from ..prompts.research import RESEARCH_SYSTEM_PROMPT
from ..tools.research import BACKEND_TOOLS, BACKEND_TOOL_NAMES
from ..nodes.research import call_model_node


def _create_call_model_node():
    return partial(
        call_model_node,
        system_prompt=RESEARCH_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES,
    )


def _assemble_graph():
    return create_graph(
        state_class=LegalDraftingState,
        call_model_node_func=_create_call_model_node(),
        tools=BACKEND_TOOLS,
    )


research_graph = _assemble_graph()
