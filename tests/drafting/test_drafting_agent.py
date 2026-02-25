"""
Comprehensive pytest for the drafting agent module.

Covers:
- Prompts (all 5 prompt files)
- Each node (LLM nodes mocked via patch.object, RAG nodes mocked via patch)
- Routers (supervisor_router, plan_router, review_router)
- merge_node (fan-in logic)
- Graph compilation (build_graph, legal_drafting_graph)
- DraftState type correctness
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rag_patch(module: str):
    """Patch the _rag helper in a parallel node module to return an empty list."""
    return patch(f"app.agents.drafting_agents.nodes.{module}._rag", return_value=[])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Prompts
# ─────────────────────────────────────────────────────────────────────────────

class TestPrompts:
    def test_supervisor_prompt_exists(self):
        from app.agents.drafting_agents.prompts.supervisor import SUPERVISOR_PROMPT
        assert isinstance(SUPERVISOR_PROMPT, str) and len(SUPERVISOR_PROMPT) > 20

    def test_intake_prompt_exists(self):
        from app.agents.drafting_agents.prompts.intake import INTAKE_PROMPT
        assert isinstance(INTAKE_PROMPT, str) and len(INTAKE_PROMPT) > 20

    def test_planner_prompt_exists(self):
        from app.agents.drafting_agents.prompts.llm_classifier import PLANNER_PROMPT
        assert isinstance(PLANNER_PROMPT, str) and len(PLANNER_PROMPT) > 20

    def test_drafting_prompt_exists(self):
        from app.agents.drafting_agents.prompts.drafting import DRAFTING_PROMPT
        assert isinstance(DRAFTING_PROMPT, str) and len(DRAFTING_PROMPT) > 20

    def test_review_prompt_exists(self):
        from app.agents.drafting_agents.prompts.review import REVIEW_PROMPT
        assert isinstance(REVIEW_PROMPT, str) and len(REVIEW_PROMPT) > 20

    def test_all_prompts_importable_from_init(self):
        from app.agents.drafting_agents.prompts import (
            SUPERVISOR_PROMPT,
            INTAKE_PROMPT,
            PLANNER_PROMPT,
            DRAFTING_PROMPT,
            REVIEW_PROMPT,
        )
        for p in [SUPERVISOR_PROMPT, INTAKE_PROMPT, PLANNER_PROMPT, DRAFTING_PROMPT, REVIEW_PROMPT]:
            assert isinstance(p, str) and len(p) > 0

    def test_prompts_are_unique(self):
        """Each prompt should be distinct — no copy-paste between agents."""
        from app.agents.drafting_agents.prompts import (
            SUPERVISOR_PROMPT, INTAKE_PROMPT, PLANNER_PROMPT,
            DRAFTING_PROMPT, REVIEW_PROMPT,
        )
        prompts = [SUPERVISOR_PROMPT, INTAKE_PROMPT, PLANNER_PROMPT, DRAFTING_PROMPT, REVIEW_PROMPT]
        assert len(set(prompts)) == 5, "Prompts are not unique — possible copy-paste"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Supervisor node (deterministic — no LLM, keyword-based)
# ─────────────────────────────────────────────────────────────────────────────

class TestSupervisorNode:
    def test_returns_intent_draft(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_node
        state = {"messages": [HumanMessage(content="Draft a legal notice for loan recovery")]}
        result = supervisor_node(state)
        assert result["intent"] == "draft"
        assert result["doc_type"] == "legal_notice"
        assert result["needs_clarification"] is False

    def test_returns_intent_question(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_node
        state = {"messages": [HumanMessage(content="What is the limitation period for contracts?")]}
        result = supervisor_node(state)
        assert result["intent"] == "question"

    def test_returns_needs_clarification_false(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_node
        state = {"messages": [HumanMessage(content="Draft a bail application for my client")]}
        result = supervisor_node(state)
        assert result["needs_clarification"] is False

    def test_supervisor_node_is_callable(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_node
        assert callable(supervisor_node)

    def test_doc_type_detected_from_keywords(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_node
        state = {"messages": [HumanMessage(content="I need to write a writ petition")]}
        result = supervisor_node(state)
        assert result["doc_type"] == "writ_petition"

    def test_unknown_doc_type_for_unrecognized_input(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_node
        state = {"messages": [HumanMessage(content="What is a tort?")]}
        result = supervisor_node(state)
        assert result["doc_type"] == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Supervisor router
# ─────────────────────────────────────────────────────────────────────────────

class TestSupervisorRouter:
    def test_routes_to_intake_draft_no_clarification(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_router
        assert supervisor_router({"intent": "draft", "needs_clarification": False}) == "intake"

    def test_routes_to_end_question(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_router
        assert supervisor_router({"intent": "question"}) == END

    def test_routes_to_end_draft_needs_clarification(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_router
        assert supervisor_router({"intent": "draft", "needs_clarification": True}) == END

    def test_routes_to_end_unknown_intent(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_router
        assert supervisor_router({"intent": "unknown"}) == END

    def test_routes_to_end_empty_state(self):
        from app.agents.drafting_agents.nodes.supervisor import supervisor_router
        assert supervisor_router({}) == END


# ─────────────────────────────────────────────────────────────────────────────
# 4. Intake node
# ─────────────────────────────────────────────────────────────────────────────

class TestIntakeNode:
    def _state(self):
        return {
            "messages": [HumanMessage(content="Draft legal notice for Rs 5 lakh loan recovery Mumbai")],
            "doc_type": "legal_notice",
        }

    def _mock_out(self):
        out = MagicMock()
        out.model_dump.return_value = {
            "parties": {"sender": "Ramesh", "receiver": "Suresh"},
            "facts": [{"date": "2025-01-01", "event": "loan disbursed"}],
            "jurisdiction": "Mumbai",
            "claims": {"amount": 500000},
            "evidence": ["bank transfer"],
        }
        return out

    def test_returns_intake_data(self):
        from app.agents.drafting_agents.nodes.intake import _IntakeAgent
        agent = _IntakeAgent()
        with patch.object(agent, "_invoke", return_value=self._mock_out()):
            result = agent.run(self._state())
        assert "intake_data" in result
        assert result["intake_data"]["jurisdiction"] == "Mumbai"

    def test_intake_data_has_parties(self):
        from app.agents.drafting_agents.nodes.intake import _IntakeAgent
        agent = _IntakeAgent()
        with patch.object(agent, "_invoke", return_value=self._mock_out()):
            result = agent.run(self._state())
        assert result["intake_data"]["parties"]["sender"] == "Ramesh"

    def test_intake_node_is_callable(self):
        from app.agents.drafting_agents.nodes.intake import intake_node
        assert callable(intake_node)

    def test_uses_intake_prompt_as_first_message(self):
        from app.agents.drafting_agents.nodes.intake import _IntakeAgent
        from app.agents.drafting_agents.prompts.intake import INTAKE_PROMPT
        agent = _IntakeAgent()
        captured = {}

        def _capture(messages, schema):
            captured["first"] = messages[0]
            return self._mock_out()

        with patch.object(agent, "_invoke", side_effect=_capture):
            agent.run(self._state())

        assert isinstance(captured["first"], SystemMessage)
        assert captured["first"].content == INTAKE_PROMPT

    def test_agent_name_is_intake(self):
        from app.agents.drafting_agents.nodes.intake import _IntakeAgent
        assert _IntakeAgent.agent_name == "intake"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Planner node (deterministic — no LLM, rule-based)
# ─────────────────────────────────────────────────────────────────────────────

class TestPlannerNode:
    def _state(self, doc_type="legal_notice"):
        return {
            "doc_type": doc_type,
            "intake_data": {"parties": {"sender": "A"}, "jurisdiction": "Delhi"},
        }

    def test_returns_agent_plan(self):
        from app.agents.drafting_agents.nodes.llm_classifier import planner_node
        result = planner_node(self._state())
        assert "agent_plan" in result
        assert len(result["agent_plan"]["run_agents"]) == 4

    def test_planner_node_is_callable(self):
        from app.agents.drafting_agents.nodes.llm_classifier import planner_node
        assert callable(planner_node)

    def test_core_agents_always_included(self):
        from app.agents.drafting_agents.nodes.llm_classifier import planner_node, _CORE_AGENTS
        result = planner_node(self._state(doc_type="unknown"))
        for agent in _CORE_AGENTS:
            assert agent in result["agent_plan"]["run_agents"]

    def test_citation_added_for_citation_doc_types(self):
        from app.agents.drafting_agents.nodes.llm_classifier import planner_node
        result = planner_node(self._state(doc_type="writ_petition"))
        assert "citation" in result["agent_plan"]["run_agents"]
        assert len(result["agent_plan"]["run_agents"]) == 5

    def test_citation_not_added_for_legal_notice(self):
        from app.agents.drafting_agents.nodes.llm_classifier import planner_node
        result = planner_node(self._state(doc_type="legal_notice"))
        assert "citation" not in result["agent_plan"]["run_agents"]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Plan router (fan-out)
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanRouter:
    def test_returns_sends_for_run_agents(self):
        from app.agents.drafting_agents.nodes.llm_classifier import plan_router
        from langgraph.types import Send
        state = {
            "doc_type": "legal_notice",
            "intake_data": {"parties": {}},
            "agent_plan": {"run_agents": ["template_pack", "compliance"]},
        }
        sends = plan_router(state)
        assert len(sends) == 2
        for s in sends:
            assert isinstance(s, Send)

    def test_fallback_to_core_when_empty(self):
        from app.agents.drafting_agents.nodes.llm_classifier import plan_router, _CORE_AGENTS
        from langgraph.types import Send
        state = {"agent_plan": {"run_agents": []}}
        sends = plan_router(state)
        assert len(sends) == len(_CORE_AGENTS)
        for s in sends:
            assert isinstance(s, Send)

    def test_fallback_when_no_plan(self):
        from app.agents.drafting_agents.nodes.llm_classifier import plan_router, _CORE_AGENTS
        sends = plan_router({})
        assert len(sends) == len(_CORE_AGENTS)

    def test_sends_carry_doc_type_and_intake_data(self):
        from app.agents.drafting_agents.nodes.llm_classifier import plan_router
        state = {
            "doc_type": "bail_application",
            "intake_data": {"jurisdiction": "Pune"},
            "agent_plan": {"run_agents": ["prayer"]},
        }
        sends = plan_router(state)
        assert sends[0].node == "prayer"
        assert sends[0].arg["doc_type"] == "bail_application"
        assert sends[0].arg["intake_data"]["jurisdiction"] == "Pune"

    def test_five_parallel_agents(self):
        from app.agents.drafting_agents.nodes.llm_classifier import plan_router
        from langgraph.types import Send
        state = {
            "doc_type": "writ_petition",
            "intake_data": {},
            "agent_plan": {
                "run_agents": ["template_pack", "compliance", "localization", "prayer", "citation"],
            },
        }
        sends = plan_router(state)
        assert len(sends) == 5
        node_names = [s.node for s in sends]
        for name in ["template_pack", "compliance", "localization", "prayer", "citation"]:
            assert name in node_names

    def test_invalid_agent_names_filtered(self):
        from app.agents.drafting_agents.nodes.llm_classifier import plan_router, _CORE_AGENTS
        state = {
            "doc_type": "legal_notice",
            "intake_data": {},
            "agent_plan": {"run_agents": ["bad_agent", "fake_node"]},
        }
        # Invalid names filtered → fallback to core agents
        sends = plan_router(state)
        assert len(sends) == len(_CORE_AGENTS)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Parallel RAG-backed nodes
# ─────────────────────────────────────────────────────────────────────────────

PAYLOAD = {"doc_type": "legal_notice", "intake_data": {"jurisdiction": "Delhi"}}


class TestTemplatePack:
    def test_returns_results_list(self):
        with _rag_patch("template_pack"):
            from app.agents.drafting_agents.nodes.template_pack import template_pack_node
            result = template_pack_node(PAYLOAD)
        assert "results" in result
        assert result["results"][0]["agent"] == "template_pack"

    def test_has_sections(self):
        with _rag_patch("template_pack"):
            from app.agents.drafting_agents.nodes.template_pack import template_pack_node
            result = template_pack_node(PAYLOAD)
        data = result["results"][0]["data"]
        assert "sections" in data and isinstance(data["sections"], list)

    def test_has_template_id(self):
        with _rag_patch("template_pack"):
            from app.agents.drafting_agents.nodes.template_pack import template_pack_node
            result = template_pack_node(PAYLOAD)
        data = result["results"][0]["data"]
        assert "template_id" in data
        assert "legal_notice" in data["template_id"]


class TestComplianceNode:
    def test_returns_results_list(self):
        with _rag_patch("compliance"):
            from app.agents.drafting_agents.nodes.compliance import compliance_node
            result = compliance_node(PAYLOAD)
        assert "results" in result
        assert result["results"][0]["agent"] == "compliance"

    def test_has_mandatory_sections(self):
        with _rag_patch("compliance"):
            from app.agents.drafting_agents.nodes.compliance import compliance_node
            result = compliance_node(PAYLOAD)
        data = result["results"][0]["data"]
        assert "mandatory_sections" in data


class TestLocalizationNode:
    def test_returns_results_list(self):
        with _rag_patch("localization"):
            from app.agents.drafting_agents.nodes.localization import localization_node
            result = localization_node(PAYLOAD)
        assert "results" in result
        assert result["results"][0]["agent"] == "localization"


class TestPrayerNode:
    def test_returns_results_list(self):
        with _rag_patch("prayer"):
            from app.agents.drafting_agents.nodes.prayer import prayer_node
            result = prayer_node(PAYLOAD)
        assert "results" in result
        assert result["results"][0]["agent"] == "prayer"


class TestCitationNode:
    def test_returns_results_list(self):
        with _rag_patch("citation"):
            from app.agents.drafting_agents.nodes.citation import citation_node
            result = citation_node({"doc_type": "writ_petition", "intake_data": {}})
        assert "results" in result
        assert result["results"][0]["agent"] == "citation"


# ─────────────────────────────────────────────────────────────────────────────
# 8. Merge node (fan-in)
# ─────────────────────────────────────────────────────────────────────────────

class TestMergeNode:
    def test_creates_draft_packet(self):
        from app.agents.drafting_agents.legal_drafting import merge_node
        state = {
            "doc_type": "legal_notice",
            "intake_data": {"parties": {"sender": "A"}},
            "results": [
                {"agent": "template_pack", "data": {"sections": ["facts", "prayer"]}},
                {"agent": "compliance", "data": {"mandatory_sections": ["demand"]}},
                {"agent": "localization", "data": {"court_format": "high_court"}},
                {"agent": "prayer", "data": {"prayers": ["Pay Rs 5L"]}},
            ],
        }
        result = merge_node(state)
        assert "draft_packet" in result
        packet = result["draft_packet"]
        assert packet["doc_type"] == "legal_notice"
        assert packet["template_pack"]["sections"] == ["facts", "prayer"]
        assert packet["compliance"]["mandatory_sections"] == ["demand"]
        assert packet["localization"]["court_format"] == "high_court"
        assert packet["prayer"]["prayers"] == ["Pay Rs 5L"]

    def test_empty_results(self):
        from app.agents.drafting_agents.legal_drafting import merge_node
        state = {"doc_type": "unknown", "intake_data": {}, "results": []}
        result = merge_node(state)
        packet = result["draft_packet"]
        assert packet["doc_type"] == "unknown"
        assert packet["template_pack"] == {}
        assert packet["compliance"] == {}

    def test_preserves_intake_data(self):
        from app.agents.drafting_agents.legal_drafting import merge_node
        state = {
            "doc_type": "legal_notice",
            "intake_data": {"jurisdiction": "Delhi", "parties": {"sender": "Ram"}},
            "results": [],
        }
        result = merge_node(state)
        assert result["draft_packet"]["intake_data"]["jurisdiction"] == "Delhi"

    def test_citation_included_when_present(self):
        from app.agents.drafting_agents.legal_drafting import merge_node
        state = {
            "doc_type": "writ_petition",
            "intake_data": {},
            "results": [
                {"agent": "citation", "data": {"citations": [{"case": "AIR 2020 SC 1"}]}},
            ],
        }
        result = merge_node(state)
        assert result["draft_packet"]["citation"]["citations"][0]["case"] == "AIR 2020 SC 1"

    def test_unknown_agent_in_results_stored(self):
        from app.agents.drafting_agents.legal_drafting import merge_node
        state = {
            "doc_type": "legal_notice",
            "intake_data": {},
            "results": [{"agent": "research", "data": {"principles": ["Art 226"]}}],
        }
        result = merge_node(state)
        assert result["draft_packet"]["research"]["principles"] == ["Art 226"]


# ─────────────────────────────────────────────────────────────────────────────
# 9. Drafting node
# ─────────────────────────────────────────────────────────────────────────────

class TestDraftingNode:
    def _state(self, revision_count=0):
        return {
            "draft_packet": {
                "doc_type": "legal_notice",
                "intake_data": {"parties": {"sender": "Ramesh"}},
                "template_pack": {"sections": ["facts", "prayer"]},
                "prayer": {"prayers": ["Pay Rs 5L within 15 days"]},
                "compliance": {},
                "localization": {},
                "citation": {},
            },
            "review_feedback": {},
            "revision_count": revision_count,
        }

    def _mock_out(self, text="LEGAL NOTICE\nPay Rs 5L."):
        out = MagicMock()
        out.draft_text = text
        return out

    def test_returns_draft_text(self):
        from app.agents.drafting_agents.nodes.drafting import _DraftingAgent
        agent = _DraftingAgent()
        with patch.object(agent, "_invoke", return_value=self._mock_out()):
            result = agent.run(self._state())
        assert "draft_text" in result
        assert "LEGAL NOTICE" in result["draft_text"]

    def test_increments_revision_count_from_zero(self):
        from app.agents.drafting_agents.nodes.drafting import _DraftingAgent
        agent = _DraftingAgent()
        with patch.object(agent, "_invoke", return_value=self._mock_out()):
            result = agent.run(self._state(revision_count=0))
        assert result["revision_count"] == 1

    def test_increments_revision_count_from_one(self):
        from app.agents.drafting_agents.nodes.drafting import _DraftingAgent
        agent = _DraftingAgent()
        with patch.object(agent, "_invoke", return_value=self._mock_out()):
            result = agent.run(self._state(revision_count=1))
        assert result["revision_count"] == 2

    def test_drafting_node_is_callable(self):
        from app.agents.drafting_agents.nodes.drafting import drafting_node
        assert callable(drafting_node)

    def test_uses_drafting_prompt_as_first_message(self):
        from app.agents.drafting_agents.nodes.drafting import _DraftingAgent
        from app.agents.drafting_agents.prompts.drafting import DRAFTING_PROMPT
        agent = _DraftingAgent()
        captured = {}

        def _capture(messages, schema):
            captured["first"] = messages[0]
            return self._mock_out()

        with patch.object(agent, "_invoke", side_effect=_capture):
            agent.run(self._state())

        assert isinstance(captured["first"], SystemMessage)
        assert captured["first"].content == DRAFTING_PROMPT

    def test_agent_name_is_drafting(self):
        from app.agents.drafting_agents.nodes.drafting import _DraftingAgent
        assert _DraftingAgent.agent_name == "drafting"


# ─────────────────────────────────────────────────────────────────────────────
# 10. Review node
# ─────────────────────────────────────────────────────────────────────────────

class TestReviewNode:
    def _state(self):
        return {
            "intake_data": {"parties": {"sender": "Ramesh"}},
            "draft_packet": {"doc_type": "legal_notice"},
            "draft_text": "LEGAL NOTICE\nPay Rs 5L.",
        }

    def _mock_out_no_revision(self):
        out = MagicMock()
        out.model_dump.return_value = {"needs_revision": False, "issues": [], "suggested_fixes": []}
        return out

    def _mock_out_revision(self):
        out = MagicMock()
        out.model_dump.return_value = {
            "needs_revision": True,
            "issues": ["Missing prayer block", "Inconsistent date"],
            "suggested_fixes": ["Add prayer", "Fix date"],
        }
        return out

    def test_returns_review_feedback_no_revision(self):
        from app.agents.drafting_agents.nodes.review import _ReviewAgent
        agent = _ReviewAgent()
        with patch.object(agent, "_invoke", return_value=self._mock_out_no_revision()):
            result = agent.run(self._state())
        assert "review_feedback" in result
        assert result["review_feedback"]["needs_revision"] is False

    def test_returns_review_feedback_with_issues(self):
        from app.agents.drafting_agents.nodes.review import _ReviewAgent
        agent = _ReviewAgent()
        with patch.object(agent, "_invoke", return_value=self._mock_out_revision()):
            result = agent.run(self._state())
        assert result["review_feedback"]["needs_revision"] is True
        assert len(result["review_feedback"]["issues"]) == 2
        assert "Missing prayer block" in result["review_feedback"]["issues"]

    def test_review_node_is_callable(self):
        from app.agents.drafting_agents.nodes.review import review_node
        assert callable(review_node)

    def test_uses_review_prompt_as_first_message(self):
        from app.agents.drafting_agents.nodes.review import _ReviewAgent
        from app.agents.drafting_agents.prompts.review import REVIEW_PROMPT
        agent = _ReviewAgent()
        captured = {}

        def _capture(messages, schema):
            captured["first"] = messages[0]
            return self._mock_out_no_revision()

        with patch.object(agent, "_invoke", side_effect=_capture):
            agent.run(self._state())

        assert isinstance(captured["first"], SystemMessage)
        assert captured["first"].content == REVIEW_PROMPT

    def test_agent_name_is_review(self):
        from app.agents.drafting_agents.nodes.review import _ReviewAgent
        assert _ReviewAgent.agent_name == "review"


# ─────────────────────────────────────────────────────────────────────────────
# 11. Review router
# ─────────────────────────────────────────────────────────────────────────────

class TestReviewRouter:
    def test_routes_to_drafting_when_needs_revision_under_limit(self):
        from app.agents.drafting_agents.nodes.review import review_router
        from app.agents.drafting_agents.config.workflow_config import MAX_DRAFT_REVISIONS
        # revision_count must be strictly less than MAX_DRAFT_REVISIONS to trigger revision
        state = {"review_feedback": {"needs_revision": True}, "revision_count": MAX_DRAFT_REVISIONS - 1}
        assert review_router(state) == "drafting"

    def test_routes_to_end_at_exact_revision_limit(self):
        from app.agents.drafting_agents.nodes.review import review_router
        from app.agents.drafting_agents.config.workflow_config import MAX_DRAFT_REVISIONS
        # revision_count == MAX_DRAFT_REVISIONS → no more revisions allowed
        state = {"review_feedback": {"needs_revision": True}, "revision_count": MAX_DRAFT_REVISIONS}
        assert review_router(state) == END

    def test_routes_to_end_when_no_revision_needed(self):
        from app.agents.drafting_agents.nodes.review import review_router
        state = {"review_feedback": {"needs_revision": False}, "revision_count": 0}
        assert review_router(state) == END

    def test_routes_to_end_at_revision_limit(self):
        from app.agents.drafting_agents.nodes.review import review_router
        state = {"review_feedback": {"needs_revision": True}, "revision_count": 2}
        assert review_router(state) == END

    def test_routes_to_end_above_revision_limit(self):
        from app.agents.drafting_agents.nodes.review import review_router
        state = {"review_feedback": {"needs_revision": True}, "revision_count": 5}
        assert review_router(state) == END

    def test_routes_to_end_when_empty_feedback(self):
        from app.agents.drafting_agents.nodes.review import review_router
        state = {"review_feedback": {}, "revision_count": 0}
        assert review_router(state) == END


# ─────────────────────────────────────────────────────────────────────────────
# 12. Graph compilation
# ─────────────────────────────────────────────────────────────────────────────

class TestGraphCompilation:
    def test_legal_drafting_graph_exists(self):
        from app.agents.drafting_agents.legal_drafting import legal_drafting_graph
        assert legal_drafting_graph is not None

    def test_graph_has_invoke(self):
        from app.agents.drafting_agents.legal_drafting import legal_drafting_graph
        assert callable(legal_drafting_graph.invoke)

    def test_build_graph_returns_compiled(self):
        from langgraph.graph.state import CompiledStateGraph
        from app.agents.drafting_agents.legal_drafting import build_graph
        assert isinstance(build_graph(), CompiledStateGraph)

    def test_graph_has_all_expected_nodes(self):
        from app.agents.drafting_agents.legal_drafting import build_graph
        graph = build_graph()
        expected = {
            "supervisor", "intake", "planner",
            "template_pack", "compliance", "localization", "prayer", "citation",
            "merge", "drafting", "review",
        }
        actual = set(graph.nodes.keys()) - {"__start__", "__end__"}
        assert expected.issubset(actual), f"Missing nodes: {expected - actual}"

    def test_graph_has_11_nodes(self):
        from app.agents.drafting_agents.legal_drafting import build_graph
        graph = build_graph()
        user_nodes = set(graph.nodes.keys()) - {"__start__", "__end__"}
        assert len(user_nodes) == 11


# ─────────────────────────────────────────────────────────────────────────────
# 13. DraftState type correctness
# ─────────────────────────────────────────────────────────────────────────────

class TestDraftState:
    def test_state_has_all_required_keys(self):
        from app.agents.drafting_agents.states.legal_drafting import DraftState
        hints = DraftState.__annotations__
        required = [
            "messages", "intent", "doc_type", "needs_clarification",
            "intake_data", "agent_plan", "results", "draft_packet",
            "draft_text", "revision_count", "review_feedback",
        ]
        for key in required:
            assert key in hints, f"DraftState missing field: {key}"

    def test_legal_drafting_state_alias(self):
        from app.agents.drafting_agents.states.legal_drafting import DraftState, LegalDraftingState
        assert LegalDraftingState is DraftState

    def test_state_importable_from_package(self):
        from app.agents.drafting_agents.states import DraftState
        assert DraftState is not None
