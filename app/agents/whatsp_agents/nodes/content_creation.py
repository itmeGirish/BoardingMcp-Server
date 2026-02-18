"""
Graph node functions for Content Creation Agent.

Thin subclass of BaseAgentNode — higher max_iterations for template lifecycle
(list, submit, poll, select may need more iterations).
"""

from ..base_agent import BaseAgentNode


class ContentCreationAgentNode(BaseAgentNode):
    agent_name = "ContentCreation"
    max_iterations = 20


_node = ContentCreationAgentNode()
call_model_node = _node.call_model_node


__all__ = ["call_model_node"]
