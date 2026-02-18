"""
Base class for all agent nodes in the broadcasting workflow.

Centralizes:
- Model selection (imports from app.services.llm_service)
- CopilotKit action extraction
- Tool binding
- Model invocation with error handling
- Tool call detection and routing
- Iteration guard logic
- Structured logging

To change the LLM model for ALL agents, update app/services/llm_service.py
or switch the default_model below.
"""

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command
from ....config import logger
from ....services.llm_service import ollma_model


# ── Centralized model ────────────────────────────────────────────
# Imported from app/services/llm_service.py — change model config there.
default_model = ollma_model


class BaseAgentNode:
    """
    Base class encapsulating the common call_model_node logic.

    Subclasses MUST set:
        agent_name: str           - e.g. "Analytics", "Compliance"

    Subclasses MAY override:
        max_iterations: int|None  - None means no iteration guard
        forced_end_message: str   - Message when max iterations hit
        model_name: str           - Override the LLM model
        temperature: float        - Override the LLM temperature

    Subclasses MAY override methods:
        _log_model_response()     - For extra verbose logging
        _route_response()         - For custom routing (supervisor delegation)
    """

    agent_name: str = "Base"
    max_iterations: int | None = 15
    forced_end_message: str | None = None
    model = default_model  # Override in subclass to use nvidia_model, ollma_model, etc.

    # ── Logging helpers ──────────────────────────────────────────

    def _get_log_prefix(self) -> str:
        return f"[{self.agent_name}]"

    def _log_recent_messages(self, state) -> None:
        prefix = self._get_log_prefix()
        tool_message_count = self._count_tool_messages(state)
        recent = state["messages"][-2:] if len(state["messages"]) > 2 else state["messages"]

        logger.info(
            f"{prefix} Call model with {len(state['messages'])} messages, "
            f"{tool_message_count} tool results, last 2:"
        )
        for i, msg in enumerate(recent):
            msg_type = type(msg).__name__
            content_preview = str(getattr(msg, "content", ""))[:150]
            logger.info(f"  [{i}] {msg_type}: {content_preview}")

    def _log_model_response(self, response) -> None:
        """Hook for extra logging after model response. Override in subclasses."""
        pass

    # ── Iteration guard ──────────────────────────────────────────

    def _count_tool_messages(self, state) -> int:
        return sum(1 for msg in state["messages"] if isinstance(msg, ToolMessage))

    def _get_forced_end_message(self) -> str:
        if self.forced_end_message is not None:
            return self.forced_end_message
        return f"{self.agent_name} complete. Maximum iteration limit reached."

    def _check_iteration_guard(self, state) -> Command | None:
        if self.max_iterations is None:
            return None

        tool_message_count = self._count_tool_messages(state)
        if tool_message_count >= self.max_iterations:
            prefix = self._get_log_prefix()
            logger.warning(
                f"{prefix} Max iterations ({self.max_iterations}) reached "
                f"with {tool_message_count} tool results. Forcing END."
            )
            return Command(
                goto=END,
                update={"messages": [AIMessage(content=self._get_forced_end_message())]},
            )
        return None

    # ── Message building ─────────────────────────────────────────

    def _build_messages(self, state, system_prompt: str) -> list:
        system_message = SystemMessage(content=system_prompt)
        return [system_message] + state["messages"]

    # ── CopilotKit integration ───────────────────────────────────

    def _get_copilotkit_actions(self, state) -> list:
        copilotkit_actions = state.get("copilotkit", {}).get("actions", [])
        logger.info(f"CopilotKit actions count: {len(copilotkit_actions)}")

        for action in copilotkit_actions:
            action_name = (
                getattr(action, "name", None)
                or (action.get("name") if isinstance(action, dict) else "unknown")
            )
            logger.info(f"  - Frontend tool: {action_name}")

        return copilotkit_actions

    # ── Model creation & invocation ──────────────────────────────

    def _create_model_with_tools(self, copilotkit_actions: list, tools: list):
        from langchain_openai import ChatOpenAI

        if isinstance(self.model, ChatOpenAI):
            all_tools = [*copilotkit_actions, *tools]
            return self.model.bind_tools(all_tools, parallel_tool_calls=False)

        # Non-OpenAI models (Ollama etc.): bind only backend tools.
        # CopilotKit frontend actions use OpenAI-specific schemas that
        # Ollama can't parse (empty {} objects, complex nested types).
        # The frontend handles CopilotKit actions independently.
        return self.model.bind_tools(tools)

    async def _invoke_model(self, model_with_tools, messages, config: RunnableConfig):
        prefix = self._get_log_prefix()
        try:
            response = await model_with_tools.ainvoke(messages, config)
            logger.info(f"{prefix} Model response received successfully")
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
        """Route based on tool calls. Override in SupervisorAgentNode for delegation."""
        prefix = self._get_log_prefix()

        if has_backend_tool_calls:
            logger.info(f"{prefix} Routing to tool_node (backend tools)")
            return Command(goto="tool_node", update={"messages": [response]})
        else:
            logger.info(f"{prefix} Routing to END")
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
        """
        Main graph node function. Wrapped with functools.partial in assembly files.

        Args:
            state: Current agent state
            config: Runnable configuration
            system_prompt: System prompt string
            tools: List of backend tools
            tool_names_set: Set of backend tool names
            **kwargs: Extra args (e.g. delegation_tool_map for supervisor)
        """
        # 1. Iteration guard
        guard_result = self._check_iteration_guard(state)
        if guard_result is not None:
            return guard_result

        # 2. Log recent messages
        self._log_recent_messages(state)

        # 3. Build messages
        messages = self._build_messages(state, system_prompt)

        # 4. Get CopilotKit actions
        copilotkit_actions = self._get_copilotkit_actions(state)

        # 5. Create model with tools
        model_with_tools = self._create_model_with_tools(copilotkit_actions, tools)

        # 6. Invoke model
        response = await self._invoke_model(model_with_tools, messages, config)

        # 7. Extra logging hook
        self._log_model_response(response)

        # 8. Detect and route
        has_backend = self._detect_backend_tool_calls(response, tool_names_set)
        return self._route_response(response, has_backend, tool_names_set, **kwargs)
