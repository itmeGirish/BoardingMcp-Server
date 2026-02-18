"""
Prayer node for legal drafting workflow.

Model: GLM-4.7 (via DRAFTING_MODELS["prayer"])
Generates correct prayers and reliefs based on doc_type and legal framework.
"""
from ..base_agent import DraftingBaseAgentNode


class PrayerAgentNode(DraftingBaseAgentNode):
    agent_name = "prayer"
    max_iterations = 10


_node = PrayerAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]
