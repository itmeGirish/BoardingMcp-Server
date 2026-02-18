"""
Graph node functions for Analytics & Optimization Agent.

Thin subclass of BaseAgentNode — only configures agent_name and max_iterations.
All common logic (model creation, tool binding, routing) lives in BaseAgentNode.
"""

from ..base_agent import BaseAgentNode


class AnalyticsAgentNode(BaseAgentNode):
    agent_name = "Analytics"
    max_iterations = 15


_node = AnalyticsAgentNode()
call_model_node = _node.call_model_node


__all__ = ["call_model_node"]
