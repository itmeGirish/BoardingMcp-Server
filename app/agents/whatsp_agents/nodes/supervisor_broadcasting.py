"""
Graph node functions for broadcasting supervisor workflow.

Thin subclass of SupervisorAgentNode — adds delegation routing to sub-agents.
Exports both call_model_node and route_after_tool for backward compatibility.
"""

from ..base_agent import SupervisorAgentNode


class BroadcastingSupervisorNode(SupervisorAgentNode):
    agent_name = "Broadcasting"


_node = BroadcastingSupervisorNode()
call_model_node = _node.call_model_node
route_after_tool = SupervisorAgentNode.route_after_tool


__all__ = ["call_model_node", "route_after_tool"]
