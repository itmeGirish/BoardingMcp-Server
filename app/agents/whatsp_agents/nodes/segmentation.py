"""
Graph node functions for Segmentation Agent.

Thin subclass of BaseAgentNode — only configures agent_name and max_iterations.
All common logic (model creation, tool binding, routing) lives in BaseAgentNode.
"""

from ..base_agent import BaseAgentNode


class SegmentationAgentNode(BaseAgentNode):
    agent_name = "Segmentation"
    max_iterations = 15


_node = SegmentationAgentNode()
call_model_node = _node.call_model_node


__all__ = ["call_model_node"]
