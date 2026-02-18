"""Base agent node classes for the whatsp_agents workflow."""

from .base_agent_node import BaseAgentNode, default_model
from .supervisor_agent_node import SupervisorAgentNode

__all__ = [
    "BaseAgentNode",
    "SupervisorAgentNode",
    "default_model",
]
