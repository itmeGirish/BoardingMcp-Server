"""
Localization node for legal drafting workflow.

Model: GLM-4.7 (via DRAFTING_MODELS["localization"])
Applies court-specific and state-specific formatting conventions.
"""
from ..base_agent import DraftingBaseAgentNode


class LocalizationAgentNode(DraftingBaseAgentNode):
    agent_name = "localization"
    max_iterations = 10


_node = LocalizationAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]
