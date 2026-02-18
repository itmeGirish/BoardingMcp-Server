"""
LLM Classifier node for legal drafting workflow.

Semantic document classification based on gathered facts.
Non-interactive — operates on previously gathered facts only.
"""
from ..base_agent import DraftingBaseAgentNode


class LLMClassifierAgentNode(DraftingBaseAgentNode):
    agent_name = "llm_classifier"
    max_iterations = 10


_node = LLMClassifierAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]
