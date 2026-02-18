"""Citation node. Model: Kimi K2.5 (via DRAFTING_MODELS["citation"])."""
from ..base_agent import DraftingBaseAgentNode


class CitationAgentNode(DraftingBaseAgentNode):
    agent_name = "citation"
    max_iterations = 10


_node = CitationAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]
