"""
Compliance node for legal drafting workflow.

Model: GLM-4.7 (via DRAFTING_MODELS["compliance"])
Validates limitation periods, annexures, and statutory compliance.
"""
from ..base_agent import DraftingBaseAgentNode


class ComplianceAgentNode(DraftingBaseAgentNode):
    agent_name = "compliance"
    max_iterations = 10


_node = ComplianceAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]
