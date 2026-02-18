"""
Supervisor node for legal drafting workflow.

Model: GLM-4.7 (via DRAFTING_MODELS["supervisor"])
"""
from ..base_agent import DraftingSupervisorAgentNode


class LegalDraftingSupervisorNode(DraftingSupervisorAgentNode):
    agent_name = "supervisor"


_node = LegalDraftingSupervisorNode()
call_model_node = _node.call_model_node
route_after_tool = DraftingSupervisorAgentNode.route_after_tool

__all__ = ["call_model_node", "route_after_tool"]
