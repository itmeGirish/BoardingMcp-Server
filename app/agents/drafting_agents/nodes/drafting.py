"""
Drafting node for legal drafting workflow.

Model: Kimi K2.5 (via DRAFTING_MODELS["drafting"])
Higher iteration limit for complex document generation.
"""
from ..base_agent import DraftingBaseAgentNode


class DraftingAgentNode(DraftingBaseAgentNode):
    agent_name = "drafting"
    max_iterations = 10


_node = DraftingAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]
