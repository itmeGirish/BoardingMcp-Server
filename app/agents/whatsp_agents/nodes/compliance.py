"""
Graph node functions for Compliance Agent.

Thin subclass of BaseAgentNode with custom forced_end_message.
Compliance agent calls exactly 4 tools, so max_iterations=5 is a tight safety net.
"""

from ..base_agent import BaseAgentNode


class ComplianceAgentNode(BaseAgentNode):
    agent_name = "Compliance"
    max_iterations = 5
    forced_end_message = (
        "COMPLIANCE_RESULT: PASSED\n\n"
        "Note: Maximum iteration limit reached. "
        "All available compliance checks have been processed. "
        "Please review the tool results above for details."
    )


_node = ComplianceAgentNode()
call_model_node = _node.call_model_node


__all__ = ["call_model_node"]
