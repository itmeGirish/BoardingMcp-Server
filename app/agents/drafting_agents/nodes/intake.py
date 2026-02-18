"""
Intake node for legal drafting workflow.

Model: Kimi K2.5 (via DRAFTING_MODELS["intake"])
Single-pass extraction — extract facts and save in one turn.
"""
from ..base_agent import DraftingBaseAgentNode


class IntakeAgentNode(DraftingBaseAgentNode):
    agent_name = "intake"
    max_iterations = 5


_node = IntakeAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]
