"""
Graph node functions for Data Processing Agent.

Thin subclass of BaseAgentNode — only configures agent_name and max_iterations.
All common logic (model creation, tool binding, routing) lives in BaseAgentNode.
"""

from ..base_agent import BaseAgentNode


class DataProcessingAgentNode(BaseAgentNode):
    agent_name = "DataProcessing"
    max_iterations = 15


_node = DataProcessingAgentNode()
call_model_node = _node.call_model_node


__all__ = ["call_model_node"]
