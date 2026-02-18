"""
Research node for legal drafting workflow.

Model: Kimi K2.5 (via DRAFTING_MODELS["research"])
Deep search — web + RAG + LLM knowledge.
"""
from ..base_agent import DraftingBaseAgentNode


class ResearchAgentNode(DraftingBaseAgentNode):
    agent_name = "research"
    max_iterations = 10


_node = ResearchAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]
