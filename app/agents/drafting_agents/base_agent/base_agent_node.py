"""
Base class for all agent nodes in the legal drafting workflow.

Imports model connections from app/services/llm_service.py
and maps them to agents via DRAFTING_MODELS registry.

Model policy (per CLAUD.md):
    GLM-4.7   → Supervisor (fast routing)
    Kimi K2.5 → Intake, FactExtraction, Research, Drafting, Review
"""

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command
from ....config import logger
from ....services.llm_service import glm_model, ollma_model


# ── Model registry ───────────────────────────────────────────────
# To swap a model: change the value here. No other file changes needed.
# Model policy (per CLAUD.md):
#   GLM-4.7   → Supervisor, LLM Classifier, Template Pack, Compliance, Localization, Prayer
#   Kimi K2.5 → Intake, Fact Extraction, Research, Citation, Drafting, Review
DRAFTING_MODELS = {
    "supervisor":       glm_model,       # GLM-4.7  — fast routing
    "intake":           ollma_model,      # Kimi K2.5 — conversational
    "fact_extraction":  ollma_model,      # Kimi K2.5 — extraction
    "llm_classifier":   glm_model,       # GLM-4.7  — semantic classification
    "template_pack":    glm_model,       # GLM-4.7  — structure generation
    "compliance":       glm_model,       # GLM-4.7  — compliance checks
    "localization":     glm_model,       # GLM-4.7  — formatting rules
    "prayer":           glm_model,       # GLM-4.7  — relief generation
    "research":         ollma_model,      # Kimi K2.5 — deep search
    "citation":         ollma_model,      # Kimi K2.5 — citation retrieval
    "drafting":         ollma_model,      # Kimi K2.5 — long-form gen
    "review":           ollma_model,      # Kimi K2.5 — QA
}

# Fallback if agent_name not in registry
_default_model = glm_model


def get_drafting_model(agent_name: str):
    """Return the configured model for a drafting agent."""
    return DRAFTING_MODELS.get(agent_name, _default_model)


class DraftingBaseAgentNode:
    """
    Base class for legal drafting agent nodes.

    Subclasses MUST set:
        agent_name: str  — key in DRAFTING_MODELS (e.g. "intake", "research")

    Subclasses MAY override:
        max_iterations: int | None
        forced_end_message: str
    """

    agent_name: str = "base"
    max_iterations: int | None = 15
    forced_end_message: str | None = None

    @property
    def model(self):
        """Model is resolved from DRAFTING_MODELS at runtime."""
        return get_drafting_model(self.agent_name)

    # ── Logging ──────────────────────────────────────────────────

    def _get_log_prefix(self) -> str:
        return f"[Drafting:{self.agent_name}]"

    def _log_recent_messages(self, state) -> None:
        prefix = self._get_log_prefix()
        tool_count = self._count_tool_messages(state)
        recent = state["messages"][-2:] if len(state["messages"]) > 2 else state["messages"]

        logger.info(
            f"{prefix} call_model — {len(state['messages'])} msgs, "
            f"{tool_count} tool results"
        )
        for i, msg in enumerate(recent):
            msg_type = type(msg).__name__
            preview = str(getattr(msg, "content", ""))[:150]
            logger.info(f"  [{i}] {msg_type}: {preview}")

    def _log_model_response(self, response) -> None:
        """Hook for extra logging. Override in subclasses."""
        pass

    # ── Iteration guard ──────────────────────────────────────────

    def _count_tool_messages(self, state) -> int:
        """Count tool messages in THIS agent's run only.

        Sub-agents receive the full message history from the supervisor.
        We only count tool messages AFTER the last SystemMessage (which marks
        the start of this agent's invocation) to avoid counting tools from
        previous pipeline steps.
        """
        messages = state.get("messages", [])
        # Find the last system message index (marks start of this agent's context)
        last_system_idx = -1
        for i, msg in enumerate(messages):
            if isinstance(msg, SystemMessage):
                last_system_idx = i

        # Count ToolMessages only after the last system message
        start = last_system_idx + 1 if last_system_idx >= 0 else 0
        return sum(1 for msg in messages[start:] if isinstance(msg, ToolMessage))

    def _get_forced_end_message(self) -> str:
        if self.forced_end_message is not None:
            return self.forced_end_message
        return f"{self.agent_name} complete. Maximum iteration limit reached."

    def _check_iteration_guard(self, state) -> Command | None:
        if self.max_iterations is None:
            return None

        tool_count = self._count_tool_messages(state)
        if tool_count >= self.max_iterations:
            prefix = self._get_log_prefix()
            logger.warning(
                f"{prefix} Max iterations ({self.max_iterations}) reached. Forcing END."
            )
            return Command(
                goto=END,
                update={"messages": [AIMessage(content=self._get_forced_end_message())]},
            )
        return None

    # ── Message building ─────────────────────────────────────────

    def _build_messages(self, state, system_prompt: str) -> list:
        return [SystemMessage(content=system_prompt)] + state["messages"]

    # ── CopilotKit integration ───────────────────────────────────

    def _get_copilotkit_actions(self, state) -> list:
        actions = state.get("copilotkit", {}).get("actions", [])
        logger.info(f"CopilotKit actions count: {len(actions)}")
        for action in actions:
            name = (
                getattr(action, "name", None)
                or (action.get("name") if isinstance(action, dict) else "unknown")
            )
            logger.info(f"  - Frontend tool: {name}")
        return actions

    # ── Model creation & invocation ──────────────────────────────

    def _create_model_with_tools(self, copilotkit_actions: list, tools: list):
        from langchain_openai import ChatOpenAI

        if isinstance(self.model, ChatOpenAI):
            all_tools = [*copilotkit_actions, *tools]
            return self.model.bind_tools(all_tools, parallel_tool_calls=False)

        return self.model.bind_tools(tools)

    async def _invoke_model(self, model_with_tools, messages, config: RunnableConfig):
        prefix = self._get_log_prefix()
        try:
            response = await model_with_tools.ainvoke(messages, config)
            logger.info(f"{prefix} Model response received")
            return response
        except Exception as e:
            logger.error(f"{prefix} Model invocation failed: {e}", exc_info=True)
            raise

    # ── Tool call detection & routing ────────────────────────────

    def _detect_backend_tool_calls(self, response, tool_names_set: set) -> bool:
        prefix = self._get_log_prefix()
        tool_calls = getattr(response, "tool_calls", None)
        if tool_calls:
            logger.info(f"{prefix} Tool calls: {[tc.get('name') for tc in tool_calls]}")
            return any(tc.get("name") in tool_names_set for tc in tool_calls)
        return False

    def _route_response(
        self,
        response,
        has_backend_tool_calls: bool,
        tool_names_set: set,
        **kwargs,
    ) -> Command:
        prefix = self._get_log_prefix()
        if has_backend_tool_calls:
            logger.info(f"{prefix} → tool_node")
            return Command(goto="tool_node", update={"messages": [response]})
        logger.info(f"{prefix} → END")
        return Command(goto=END, update={"messages": [response]})

    # ── Main entry point ─────────────────────────────────────────

    async def call_model_node(
        self,
        state,
        config: RunnableConfig,
        system_prompt: str,
        tools: list,
        tool_names_set: set,
        **kwargs,
    ) -> Command:
        guard = self._check_iteration_guard(state)
        if guard is not None:
            return guard

        self._log_recent_messages(state)
        messages = self._build_messages(state, system_prompt)
        copilotkit_actions = self._get_copilotkit_actions(state)
        model_with_tools = self._create_model_with_tools(copilotkit_actions, tools)
        response = await self._invoke_model(model_with_tools, messages, config)
        self._log_model_response(response)
        has_backend = self._detect_backend_tool_calls(response, tool_names_set)
        return self._route_response(response, has_backend, tool_names_set, **kwargs)
