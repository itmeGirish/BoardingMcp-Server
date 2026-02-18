"""
Supervisor-specific agent node that adds delegation routing.

Extends BaseAgentNode with:
- delegation_tool_map parameter for sub-agent routing
- Priority-based routing (delegation > backend tools > END)
- route_after_tool() for post-tool-node routing
"""

from langchain_core.messages import ToolMessage
from langgraph.graph import END
from langgraph.types import Command
from ....config import logger
from .base_agent_node import BaseAgentNode


class SupervisorAgentNode(BaseAgentNode):
    """
    Agent node for supervisor agents that delegate to sub-agents.

    Overrides _route_response to implement delegation priority:
    1. Delegation tool called -> route to tool_node (route_after_tool sends to sub-agent)
    2. Backend tool called -> route to tool_node
    3. No tool calls -> route to END
    """

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
            # Priority 1: Delegation tools -> route to tool_node
            for tc in tool_calls:
                tc_name = tc.get("name")
                if tc_name in delegation_tool_map:
                    target_agent = delegation_tool_map[tc_name]
                    logger.info(f"{prefix} Delegating to sub-agent: {target_agent}")
                    return Command(
                        goto="tool_node",
                        update={"messages": [response]},
                    )

            # Priority 2: Backend tools -> route to tool_node
            if has_backend_tool_calls:
                logger.info(f"{prefix} Routing to tool_node (backend tools)")
                return Command(
                    goto="tool_node",
                    update={"messages": [response]},
                )

        # No tool calls -> END
        logger.info(f"{prefix} Routing to END")
        return Command(goto=END, update={"messages": [response]})

    @staticmethod
    def route_after_tool(state, delegation_tool_map: dict = None) -> str:
        """
        Route after tool_node execution.

        Checks if the last tool call was a delegation tool.
        If so, routes to the corresponding sub-agent node.
        Otherwise, routes back to call_model.
        """
        if not delegation_tool_map:
            return "call_model"

        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, ToolMessage):
                if msg.name in delegation_tool_map:
                    target = delegation_tool_map[msg.name]
                    logger.info(f"[Broadcasting] Post-tool routing to sub-agent: {target}")
                    return target
            else:
                break

        return "call_model"
