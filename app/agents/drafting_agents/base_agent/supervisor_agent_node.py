"""
Supervisor-specific agent node for the legal drafting workflow.

Extends DraftingBaseAgentNode with:
- delegation_tool_map for sub-agent routing
- Priority-based routing (delegation > backend tools > END)
- route_after_tool() for post-tool-node routing
"""

from langchain_core.messages import ToolMessage
from langgraph.graph import END
from langgraph.types import Command
from ....config import logger
from .base_agent_node import DraftingBaseAgentNode


class DraftingSupervisorAgentNode(DraftingBaseAgentNode):
    """
    Supervisor node that delegates to sub-agents.

    Routing priority:
    1. Delegation tool called → tool_node → route_after_tool → sub-agent
    2. Backend tool called → tool_node → call_model
    3. No tool calls → END
    """

    agent_name = "supervisor"
    max_iterations: int | None = None  # Supervisors have no iteration limit

    def _route_response(
        self,
        response,
        has_backend_tool_calls: bool,
        tool_names_set: set,
        **kwargs,
    ) -> Command:
        prefix = self._get_log_prefix()
        delegation_tool_map = kwargs.get("delegation_tool_map", {})
        tool_calls = getattr(response, "tool_calls", None)

        if tool_calls:
            for tc in tool_calls:
                tc_name = tc.get("name")
                if tc_name in delegation_tool_map:
                    target = delegation_tool_map[tc_name]
                    logger.info(f"{prefix} Delegating → {target}")
                    return Command(
                        goto="tool_node",
                        update={"messages": [response]},
                    )

            if has_backend_tool_calls:
                logger.info(f"{prefix} → tool_node (backend)")
                return Command(
                    goto="tool_node",
                    update={"messages": [response]},
                )

        logger.info(f"{prefix} → END")
        return Command(goto=END, update={"messages": [response]})

    @staticmethod
    def route_after_tool(state, delegation_tool_map: dict = None) -> str:
        """
        Route after tool_node execution.

        If last tool call was a delegation tool, route to that sub-agent.
        Otherwise, route back to call_model.
        """
        if not delegation_tool_map:
            return "call_model"

        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, ToolMessage):
                if msg.name in delegation_tool_map:
                    target = delegation_tool_map[msg.name]
                    logger.info(f"[Drafting:supervisor] Post-tool → {target}")
                    return target
            else:
                break

        return "call_model"
