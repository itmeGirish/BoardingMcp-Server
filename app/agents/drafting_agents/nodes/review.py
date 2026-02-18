"""
Review node for legal drafting workflow.

Model: Kimi K2.5 (via DRAFTING_MODELS["review"])
Final quality check and delivery.
"""
from ..base_agent import DraftingBaseAgentNode


class ReviewAgentNode(DraftingBaseAgentNode):
    agent_name = "review"
    max_iterations = 15


_node = ReviewAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]
