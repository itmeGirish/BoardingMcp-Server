"""Tests for DraftingBaseAgentNode and model registry."""
import pytest
from app.agents.drafting_agents.base_agent import (
    DraftingBaseAgentNode,
    DraftingSupervisorAgentNode,
    DRAFTING_MODELS,
    get_drafting_model,
)


class TestDraftingModels:
    def test_all_agents_registered(self):
        """All 12 agents must be in DRAFTING_MODELS."""
        required = [
            "supervisor", "intake", "fact_extraction",
            "llm_classifier", "template_pack",
            "compliance", "localization", "prayer",
            "research", "citation", "drafting", "review",
        ]
        for agent in required:
            assert agent in DRAFTING_MODELS, f"Missing model for: {agent}"

    def test_registry_has_exactly_12_entries(self):
        """DRAFTING_MODELS should have exactly 12 agent entries."""
        assert len(DRAFTING_MODELS) == 12

    def test_glm_agents(self):
        """GLM-4.7 agents: supervisor, llm_classifier, template_pack, compliance, localization, prayer."""
        from app.services.llm_service import glm_model
        glm_agents = ["supervisor", "llm_classifier", "template_pack", "compliance", "localization", "prayer"]
        for agent in glm_agents:
            assert DRAFTING_MODELS[agent] is glm_model, \
                f"{agent} should use glm_model, got {DRAFTING_MODELS[agent]}"

    def test_kimi_agents(self):
        """Kimi K2.5 agents: intake, fact_extraction, research, citation, drafting, review."""
        from app.services.llm_service import ollma_model
        kimi_agents = ["intake", "fact_extraction", "research", "citation", "drafting", "review"]
        for agent in kimi_agents:
            assert DRAFTING_MODELS[agent] is ollma_model, \
                f"{agent} should use ollma_model, got {DRAFTING_MODELS[agent]}"

    def test_get_drafting_model_returns_correct(self):
        """get_drafting_model should return the registered model for a known agent."""
        model = get_drafting_model("supervisor")
        assert model is DRAFTING_MODELS["supervisor"]

    def test_get_drafting_model_all_agents(self):
        """get_drafting_model should return correct model for every registered agent."""
        for agent_name, expected_model in DRAFTING_MODELS.items():
            model = get_drafting_model(agent_name)
            assert model is expected_model, \
                f"get_drafting_model('{agent_name}') returned wrong model"

    def test_get_drafting_model_fallback(self):
        """get_drafting_model should return default model for unknown agent names."""
        model = get_drafting_model("nonexistent_agent")
        assert model is not None  # Should return default (glm_model)

    def test_get_drafting_model_fallback_is_glm(self):
        """Fallback model should be glm_model."""
        from app.services.llm_service import glm_model
        model = get_drafting_model("unknown_agent_xyz")
        assert model is glm_model


class TestBaseAgentNode:
    def test_default_agent_name(self):
        """Default agent_name should be 'base'."""
        node = DraftingBaseAgentNode()
        assert node.agent_name == "base"

    def test_default_max_iterations(self):
        """Default max_iterations should be 15."""
        node = DraftingBaseAgentNode()
        assert node.max_iterations == 15

    def test_default_forced_end_message_is_none(self):
        """Default forced_end_message should be None (auto-generated)."""
        node = DraftingBaseAgentNode()
        assert node.forced_end_message is None

    def test_model_property(self):
        """Model property should resolve from DRAFTING_MODELS at runtime."""
        node = DraftingBaseAgentNode()
        node.agent_name = "supervisor"
        model = node.model
        assert model is DRAFTING_MODELS["supervisor"]

    def test_model_property_changes_with_agent_name(self):
        """Changing agent_name should change the model returned."""
        node = DraftingBaseAgentNode()
        node.agent_name = "supervisor"
        supervisor_model = node.model
        node.agent_name = "intake"
        intake_model = node.model
        # These should resolve to different model instances
        # (glm_model vs ollma_model)
        assert supervisor_model is DRAFTING_MODELS["supervisor"]
        assert intake_model is DRAFTING_MODELS["intake"]

    def test_log_prefix(self):
        """Log prefix should include agent name."""
        node = DraftingBaseAgentNode()
        node.agent_name = "intake"
        assert node._get_log_prefix() == "[Drafting:intake]"

    def test_log_prefix_default(self):
        """Default log prefix uses 'base'."""
        node = DraftingBaseAgentNode()
        assert node._get_log_prefix() == "[Drafting:base]"

    def test_forced_end_message_auto_generated(self):
        """Auto-generated forced end message should include agent name."""
        node = DraftingBaseAgentNode()
        node.agent_name = "test"
        msg = node._get_forced_end_message()
        assert "test" in msg
        assert "complete" in msg.lower() or "limit" in msg.lower()

    def test_custom_forced_end_message(self):
        """Custom forced_end_message should override auto-generated one."""
        node = DraftingBaseAgentNode()
        node.forced_end_message = "Custom end"
        assert node._get_forced_end_message() == "Custom end"

    def test_count_tool_messages(self):
        """_count_tool_messages should count ToolMessage instances."""
        from langchain_core.messages import ToolMessage, HumanMessage, AIMessage
        node = DraftingBaseAgentNode()
        state = {
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(content="hi"),
                ToolMessage(content="result", tool_call_id="1"),
                ToolMessage(content="result2", tool_call_id="2"),
            ]
        }
        assert node._count_tool_messages(state) == 2

    def test_count_tool_messages_empty(self):
        """_count_tool_messages should return 0 for no tool messages."""
        from langchain_core.messages import HumanMessage
        node = DraftingBaseAgentNode()
        state = {"messages": [HumanMessage(content="hello")]}
        assert node._count_tool_messages(state) == 0

    def test_check_iteration_guard_under_limit(self):
        """Iteration guard should return None when under limit."""
        from langchain_core.messages import HumanMessage
        node = DraftingBaseAgentNode()
        node.max_iterations = 15
        state = {"messages": [HumanMessage(content="hello")]}
        result = node._check_iteration_guard(state)
        assert result is None

    def test_check_iteration_guard_at_limit(self):
        """Iteration guard should return Command when at limit."""
        from langchain_core.messages import ToolMessage
        node = DraftingBaseAgentNode()
        node.max_iterations = 2
        state = {
            "messages": [
                ToolMessage(content="r1", tool_call_id="1"),
                ToolMessage(content="r2", tool_call_id="2"),
            ]
        }
        result = node._check_iteration_guard(state)
        assert result is not None  # Should return a Command

    def test_check_iteration_guard_disabled(self):
        """Iteration guard should be disabled when max_iterations is None."""
        from langchain_core.messages import ToolMessage
        node = DraftingBaseAgentNode()
        node.max_iterations = None
        state = {
            "messages": [
                ToolMessage(content=f"r{i}", tool_call_id=str(i))
                for i in range(100)
            ]
        }
        result = node._check_iteration_guard(state)
        assert result is None

    def test_build_messages(self):
        """_build_messages should prepend system prompt."""
        from langchain_core.messages import HumanMessage, SystemMessage
        node = DraftingBaseAgentNode()
        state = {"messages": [HumanMessage(content="hello")]}
        result = node._build_messages(state, "You are a legal assistant.")
        assert len(result) == 2
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "You are a legal assistant."
        assert isinstance(result[1], HumanMessage)


class TestSupervisorNode:
    def test_agent_name(self):
        """Supervisor agent_name should be 'supervisor'."""
        node = DraftingSupervisorAgentNode()
        assert node.agent_name == "supervisor"

    def test_no_iteration_limit(self):
        """Supervisor should have no iteration limit (None)."""
        node = DraftingSupervisorAgentNode()
        assert node.max_iterations is None

    def test_inherits_from_base(self):
        """DraftingSupervisorAgentNode must inherit from DraftingBaseAgentNode."""
        assert issubclass(DraftingSupervisorAgentNode, DraftingBaseAgentNode)

    def test_model_is_glm(self):
        """Supervisor model should resolve to glm_model."""
        from app.services.llm_service import glm_model
        node = DraftingSupervisorAgentNode()
        assert node.model is glm_model

    def test_route_after_tool_default(self):
        """route_after_tool should return 'call_model' when no delegation map."""
        result = DraftingSupervisorAgentNode.route_after_tool(
            state={"messages": []},
            delegation_tool_map=None,
        )
        assert result == "call_model"

    def test_route_after_tool_empty_map(self):
        """route_after_tool should return 'call_model' with empty delegation map."""
        result = DraftingSupervisorAgentNode.route_after_tool(
            state={"messages": []},
            delegation_tool_map={},
        )
        assert result == "call_model"

    def test_route_after_tool_with_delegation(self):
        """route_after_tool should route to sub-agent when delegation tool found."""
        from langchain_core.messages import ToolMessage
        state = {
            "messages": [
                ToolMessage(content="ok", tool_call_id="1", name="delegate_to_intake"),
            ]
        }
        delegation_map = {"delegate_to_intake": "security_gate"}
        result = DraftingSupervisorAgentNode.route_after_tool(
            state=state,
            delegation_tool_map=delegation_map,
        )
        assert result == "security_gate"

    def test_route_after_tool_non_delegation_tool(self):
        """route_after_tool should return 'call_model' for non-delegation tool messages."""
        from langchain_core.messages import ToolMessage, HumanMessage
        state = {
            "messages": [
                HumanMessage(content="hello"),
                ToolMessage(content="result", tool_call_id="1", name="some_backend_tool"),
            ]
        }
        delegation_map = {"delegate_to_intake": "security_gate"}
        result = DraftingSupervisorAgentNode.route_after_tool(
            state=state,
            delegation_tool_map=delegation_map,
        )
        # The ToolMessage name is not in delegation_map, but ToolMessage breaks the loop
        # so it returns "call_model"
        assert result == "call_model"
