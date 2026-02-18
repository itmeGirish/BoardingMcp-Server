"""Template Pack node. Model: GLM-4.7 (via DRAFTING_MODELS["template_pack"])."""
from ..base_agent import DraftingBaseAgentNode


class TemplatPackAgentNode(DraftingBaseAgentNode):
    agent_name = "template_pack"
    max_iterations = 10


_node = TemplatPackAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]
