"""DraftingSupervisorAgentNode — supervisor-specific routing helper."""
from __future__ import annotations
from langchain_core.messages import ToolMessage
from .base import DraftingBaseAgentNode


class DraftingSupervisorAgentNode(DraftingBaseAgentNode):
    agent_name: str = "supervisor"
    max_iterations = None  # supervisor has no iteration cap

    @staticmethod
    def route_after_tool(state: dict, delegation_tool_map=None) -> str:
        """
        Route to a sub-agent if the last ToolMessage matches a delegation tool,
        otherwise return 'call_model'.
        """
        delegation_map = delegation_tool_map or {}
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, ToolMessage):
                tool_name = getattr(msg, "name", None)
                if tool_name and tool_name in delegation_map:
                    return delegation_map[tool_name]
                return "call_model"
        return "call_model"
