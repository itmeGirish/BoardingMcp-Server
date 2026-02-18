"""
Graph node functions for onboarding workflow.

Thin subclass of BaseAgentNode with extra verbose logging for debugging.
No iteration guard (max_iterations=None) since onboarding is interactive.
"""

from langgraph.graph import END
from langgraph.types import Command
from ....config import logger
from ..base_agent import BaseAgentNode


class OnboardingAgentNode(BaseAgentNode):
    agent_name = "Onboarding"
    max_iterations = None

    def _log_model_response(self, response) -> None:
        """Extra verbose logging for onboarding debugging."""
        logger.info(f"Response type: {type(response)}")
        logger.info(f"Response has content: {hasattr(response, 'content')}")

    def _route_response(self, response, has_backend_tool_calls, tool_names_set, **kwargs):
        """Override to add extra END logging for onboarding debugging."""
        if has_backend_tool_calls:
            logger.info("Routing to tool_node (backend tools)")
            return Command(goto="tool_node", update={"messages": [response]})
        else:
            logger.info("Routing to END (no backend tools or frontend tools only)")
            logger.info(
                f"Final response content: "
                f"{response.content[:200] if hasattr(response, 'content') else 'NO CONTENT'}"
            )
            logger.info(
                f"Final response tool_calls: "
                f"{response.tool_calls if hasattr(response, 'tool_calls') else 'NO TOOL CALLS'}"
            )
            return Command(goto=END, update={"messages": [response]})


_node = OnboardingAgentNode()
call_model_node = _node.call_model_node


__all__ = ["call_model_node"]
