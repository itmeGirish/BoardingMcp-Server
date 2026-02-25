"""
DraftingBaseAgentNode — minimal base class for all LLM-backed drafting nodes.

Each subclass sets:
    agent_name     — used for model lookup + logging
    max_iterations — iteration guard limit (None = disabled)

Usage (simple function pattern matching test.py):
    class _MyAgent(DraftingBaseAgentNode):
        agent_name = "my_agent"

        def run(self, state) -> dict:
            out = self._invoke([SystemMessage(content=PROMPT), *state["messages"]], MySchema)
            return {"result": out.field}

    my_node = _MyAgent().run
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import END
from langgraph.types import Command

from ..config.llm_config import get_drafting_model


class DraftingBaseAgentNode:
    agent_name: str = "base"
    max_iterations: int | None = 15
    forced_end_message: str | None = None

    # ── Model ────────────────────────────────────────────────────────────────

    @property
    def model(self):
        """Resolve LLM from DRAFTING_MODELS via agent_name at runtime."""
        return get_drafting_model(self.agent_name)

    # ── Logging ──────────────────────────────────────────────────────────────

    def _get_log_prefix(self) -> str:
        return f"[Drafting:{self.agent_name}]"

    def _get_forced_end_message(self) -> str:
        if self.forced_end_message is not None:
            return self.forced_end_message
        return (
            f"{self.agent_name} reached iteration limit — returning partial result."
        )

    # ── Iteration guard ──────────────────────────────────────────────────────

    def _count_tool_messages(self, state: dict) -> int:
        return sum(
            1 for msg in state.get("messages", []) if isinstance(msg, ToolMessage)
        )

    def _check_iteration_guard(self, state: dict):
        """Return a Command(goto=END) if iteration limit reached, else None."""
        if self.max_iterations is None:
            return None
        if self._count_tool_messages(state) >= self.max_iterations:
            return Command(
                goto=END,
                update={"error_message": self._get_forced_end_message()},
            )
        return None

    # ── Message building ─────────────────────────────────────────────────────

    def _build_messages(self, state: dict, system_prompt: str) -> list:
        """Prepend system prompt to state messages."""
        return [SystemMessage(content=system_prompt), *state.get("messages", [])]

    # ── LLM invocation ───────────────────────────────────────────────────────

    def _invoke(self, messages: list, output_schema):
        """Call model.with_structured_output(schema).invoke(messages)."""
        return self.model.with_structured_output(output_schema).invoke(messages)

    # ── Override in subclass ─────────────────────────────────────────────────

    def run(self, state: dict) -> dict:
        raise NotImplementedError(f"{type(self).__name__}.run() not implemented")
