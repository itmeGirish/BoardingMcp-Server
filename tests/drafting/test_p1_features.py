"""Tests for P1 features: citation hash verification, VALID_TRANSITIONS,
session pause/resume, audit trail persistence, and clarification PAUSED behavior.

250+ tests are NOT re-tested here; these focus only on NEW P1 additions.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.agents.drafting_agents.gates.citation_confidence import (
    check_citation_confidence,
    verify_citation_hashes,
    CONFIDENCE_THRESHOLD,
)
from app.database.postgresql.postgresql_repositories.drafting.drafting_session_repo import (
    VALID_TRANSITIONS,
)


# =========================================================================
# 1. verify_citation_hashes — pure function tests
# =========================================================================

class TestVerifyCitationHashes:
    """Tests for verify_citation_hashes (CLAUDE.md Section 2.2)."""

    def test_empty_citations_passes(self):
        result = verify_citation_hashes([], set())
        assert result["passed"] is True
        assert result["gate"] == "citation_hash_verification"
        assert result["verified_citations"] == []
        assert result["discarded_citations"] == []
        assert result["details"]["total"] == 0

    def test_all_verified(self):
        citations = [
            {"citation_text": "Case A", "verification_hash": "abc123"},
            {"citation_text": "Case B", "citation_hash": "def456"},
        ]
        verified_hashes = {"abc123", "def456"}
        result = verify_citation_hashes(citations, verified_hashes)
        assert result["passed"] is True
        assert len(result["verified_citations"]) == 2
        assert len(result["discarded_citations"]) == 0

    def test_all_discarded_no_hash(self):
        citations = [
            {"citation_text": "No Hash Case", "confidence": 0.90},
        ]
        result = verify_citation_hashes(citations, {"abc"})
        assert result["passed"] is False
        assert len(result["discarded_citations"]) == 1
        assert result["discarded_citations"][0]["reason"] == "no_hash"

    def test_all_discarded_hash_not_in_db(self):
        citations = [
            {"citation_text": "Unknown Hash", "verification_hash": "xyz999"},
        ]
        result = verify_citation_hashes(citations, {"abc123"})
        assert result["passed"] is False
        assert len(result["discarded_citations"]) == 1
        assert result["discarded_citations"][0]["reason"] == "hash_not_in_verified_db"

    def test_mixed_verified_and_discarded(self):
        citations = [
            {"citation_text": "Good", "verification_hash": "hash1"},
            {"citation_text": "Bad", "verification_hash": "hash2"},
            {"citation_text": "No Hash"},
        ]
        verified_hashes = {"hash1"}
        result = verify_citation_hashes(citations, verified_hashes)
        assert result["passed"] is False
        assert len(result["verified_citations"]) == 1
        assert len(result["discarded_citations"]) == 2
        assert result["details"]["total"] == 3
        assert result["details"]["verified"] == 1
        assert result["details"]["discarded"] == 2

    def test_citation_hash_field_fallback(self):
        """citation_hash is used if verification_hash is absent."""
        citations = [
            {"citation_text": "Fallback", "citation_hash": "fb_hash"},
        ]
        result = verify_citation_hashes(citations, {"fb_hash"})
        assert result["passed"] is True
        assert len(result["verified_citations"]) == 1

    def test_verification_hash_takes_precedence(self):
        """verification_hash is preferred over citation_hash."""
        citations = [
            {
                "citation_text": "Dual",
                "verification_hash": "v_hash",
                "citation_hash": "c_hash",
            },
        ]
        # Only v_hash is in verified set
        result = verify_citation_hashes(citations, {"v_hash"})
        assert result["passed"] is True

    def test_verification_hash_precedence_wrong_hash(self):
        """When verification_hash is present but wrong, citation_hash is NOT checked."""
        citations = [
            {
                "citation_text": "Dual Wrong",
                "verification_hash": "wrong",
                "citation_hash": "correct",
            },
        ]
        result = verify_citation_hashes(citations, {"correct"})
        # verification_hash "wrong" not in set → discarded
        assert result["passed"] is False
        assert len(result["discarded_citations"]) == 1

    def test_empty_hash_treated_as_no_hash(self):
        citations = [
            {"citation_text": "Empty Hash", "verification_hash": ""},
        ]
        result = verify_citation_hashes(citations, {"abc"})
        assert result["passed"] is False
        assert result["discarded_citations"][0]["reason"] == "no_hash"

    def test_none_hash_treated_as_no_hash(self):
        citations = [
            {"citation_text": "None Hash", "verification_hash": None},
        ]
        result = verify_citation_hashes(citations, {"abc"})
        assert result["passed"] is False
        assert result["discarded_citations"][0]["reason"] == "no_hash"

    def test_empty_verified_hashes_discards_all(self):
        citations = [
            {"citation_text": "A", "verification_hash": "h1"},
            {"citation_text": "B", "verification_hash": "h2"},
        ]
        result = verify_citation_hashes(citations, set())
        assert result["passed"] is False
        assert len(result["discarded_citations"]) == 2

    def test_verified_citations_preserve_original_data(self):
        """Verified citations should contain the full original dict."""
        citations = [
            {
                "citation_text": "Full Data",
                "verification_hash": "h1",
                "confidence": 0.95,
                "source_doc_id": "DOC-1",
            },
        ]
        result = verify_citation_hashes(citations, {"h1"})
        assert result["verified_citations"][0]["confidence"] == 0.95
        assert result["verified_citations"][0]["source_doc_id"] == "DOC-1"

    def test_discarded_citations_show_citation_text(self):
        citations = [
            {"citation_text": "Specific Text", "verification_hash": "bad"},
        ]
        result = verify_citation_hashes(citations, set())
        assert result["discarded_citations"][0]["citation_text"] == "Specific Text"

    def test_discarded_unknown_citation_text(self):
        """Missing citation_text defaults to 'unknown'."""
        citations = [{"verification_hash": "bad"}]
        result = verify_citation_hashes(citations, set())
        assert result["discarded_citations"][0]["citation_text"] == "unknown"

    def test_large_batch(self):
        """Test with 100 citations, 50 verified."""
        citations = [
            {"citation_text": f"Case_{i}", "verification_hash": f"h_{i}"}
            for i in range(100)
        ]
        verified = {f"h_{i}" for i in range(50)}
        result = verify_citation_hashes(citations, verified)
        assert result["passed"] is False
        assert result["details"]["verified"] == 50
        assert result["details"]["discarded"] == 50


# =========================================================================
# 2. VALID_TRANSITIONS — 20-phase pipeline validation
# =========================================================================

class TestValidTransitions:
    """Tests for VALID_TRANSITIONS dict in DraftingSessionRepository."""

    EXPECTED_PHASES = {
        "INITIALIZED", "SECURITY", "INTAKE", "FACT_VALIDATION",
        "CLASSIFICATION", "ROUTE_RESOLUTION", "CLARIFICATION",
        "TEMPLATE_PACK", "PARALLEL_AGENTS", "OPTIONAL_AGENTS",
        "CITATION_VALIDATION", "CONTEXT_MERGE", "DRAFTING",
        "REVIEW", "STAGING_RULES", "PROMOTION", "EXPORT",
        "COMPLETED", "PAUSED", "FAILED",
    }

    def test_all_20_phases_present(self):
        assert set(VALID_TRANSITIONS.keys()) == self.EXPECTED_PHASES

    def test_exactly_20_phases(self):
        assert len(VALID_TRANSITIONS) == 20

    def test_initialized_can_go_to_security(self):
        assert "SECURITY" in VALID_TRANSITIONS["INITIALIZED"]

    def test_initialized_can_fail(self):
        assert "FAILED" in VALID_TRANSITIONS["INITIALIZED"]

    def test_completed_has_no_transitions(self):
        assert VALID_TRANSITIONS["COMPLETED"] == []

    def test_failed_can_restart(self):
        assert "INITIALIZED" in VALID_TRANSITIONS["FAILED"]

    def test_paused_can_resume_to_any_active_phase(self):
        paused = VALID_TRANSITIONS["PAUSED"]
        # PAUSED should be able to resume to any active phase
        for phase in self.EXPECTED_PHASES - {"INITIALIZED", "COMPLETED", "PAUSED"}:
            assert phase in paused, f"PAUSED should allow transition to {phase}"

    def test_paused_cannot_go_to_initialized(self):
        assert "INITIALIZED" not in VALID_TRANSITIONS["PAUSED"]

    def test_paused_cannot_go_to_completed(self):
        assert "COMPLETED" not in VALID_TRANSITIONS["PAUSED"]

    def test_paused_cannot_go_to_paused(self):
        assert "PAUSED" not in VALID_TRANSITIONS["PAUSED"]

    def test_clarification_can_pause(self):
        assert "PAUSED" in VALID_TRANSITIONS["CLARIFICATION"]

    def test_fact_validation_can_pause(self):
        assert "PAUSED" in VALID_TRANSITIONS["FACT_VALIDATION"]

    def test_context_merge_can_pause(self):
        assert "PAUSED" in VALID_TRANSITIONS["CONTEXT_MERGE"]

    def test_security_cannot_pause(self):
        """Security gate should not need to pause."""
        assert "PAUSED" not in VALID_TRANSITIONS["SECURITY"]

    def test_forward_only_pipeline(self):
        """Each non-terminal phase should transition forward, not backward."""
        ordered = [
            "INITIALIZED", "SECURITY", "INTAKE", "FACT_VALIDATION",
            "CLASSIFICATION", "ROUTE_RESOLUTION", "CLARIFICATION",
            "TEMPLATE_PACK", "PARALLEL_AGENTS", "OPTIONAL_AGENTS",
            "CITATION_VALIDATION", "CONTEXT_MERGE", "DRAFTING",
            "REVIEW", "STAGING_RULES", "PROMOTION", "EXPORT",
            "COMPLETED",
        ]
        for i, phase in enumerate(ordered[:-1]):  # skip COMPLETED
            allowed = VALID_TRANSITIONS[phase]
            # At least one forward target (next in pipeline or FAILED/PAUSED)
            forward_targets = [t for t in allowed if t not in ("FAILED", "PAUSED")]
            if forward_targets:
                # The forward target should be later in the pipeline
                for target in forward_targets:
                    target_idx = ordered.index(target)
                    assert target_idx > i, (
                        f"{phase} -> {target} is backwards "
                        f"({i} -> {target_idx})"
                    )

    def test_every_phase_can_fail_except_completed(self):
        """Every active phase should have FAILED as a valid transition."""
        for phase in self.EXPECTED_PHASES - {"COMPLETED", "PAUSED", "FAILED"}:
            assert "FAILED" in VALID_TRANSITIONS[phase], (
                f"{phase} should be able to transition to FAILED"
            )

    def test_linear_pipeline_order(self):
        """The primary pipeline path should be linear."""
        linear = [
            ("INITIALIZED", "SECURITY"),
            ("SECURITY", "INTAKE"),
            ("INTAKE", "FACT_VALIDATION"),
            ("FACT_VALIDATION", "CLASSIFICATION"),
            ("CLASSIFICATION", "ROUTE_RESOLUTION"),
            ("ROUTE_RESOLUTION", "CLARIFICATION"),
            ("CLARIFICATION", "TEMPLATE_PACK"),
            ("TEMPLATE_PACK", "PARALLEL_AGENTS"),
            ("PARALLEL_AGENTS", "OPTIONAL_AGENTS"),
            ("OPTIONAL_AGENTS", "CITATION_VALIDATION"),
            ("CITATION_VALIDATION", "CONTEXT_MERGE"),
            ("CONTEXT_MERGE", "DRAFTING"),
            ("DRAFTING", "REVIEW"),
            ("REVIEW", "STAGING_RULES"),
            ("STAGING_RULES", "PROMOTION"),
            ("PROMOTION", "EXPORT"),
            ("EXPORT", "COMPLETED"),
        ]
        for from_phase, to_phase in linear:
            assert to_phase in VALID_TRANSITIONS[from_phase], (
                f"Missing linear transition: {from_phase} -> {to_phase}"
            )


# =========================================================================
# 3. Pipeline gate node audit trail + PAUSED behavior
# =========================================================================

# Helper to build mock that prevents real DB calls
def _mock_db_context():
    """Context manager that mocks get_session to prevent real DB calls."""
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.exec = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]), first=MagicMock(return_value=None)))
    return mock_session


class TestSecurityGateAuditTrail:
    """Tests for security_gate_node audit trail persistence."""

    @pytest.mark.asyncio
    async def test_audit_saves_validation(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import security_gate_node
        from langchain_core.messages import HumanMessage

        state = {
            "messages": [HumanMessage(content="Draft a bail application")],
            "drafting_session_id": "sess-001",
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation") as mock_val, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output") as mock_out, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase") as mock_phase:
            result = await security_gate_node(state)

            mock_val.assert_called_once()
            args = mock_val.call_args
            assert args[0][0] == "sess-001"
            assert args[0][1] == "security_normalizer"
            assert args[0][2] is True  # passed

            mock_out.assert_called_once()
            assert mock_out.call_args[0][1] == "security_gate"
            assert mock_out.call_args[0][2] == "sanitized_input"

            mock_phase.assert_called_once_with("sess-001", "SECURITY")

    @pytest.mark.asyncio
    async def test_no_audit_without_session_id(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import security_gate_node
        from langchain_core.messages import HumanMessage

        state = {"messages": [HumanMessage(content="Draft something")]}

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation") as mock_val, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output") as mock_out, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase") as mock_phase:
            await security_gate_node(state)

            # All audit helpers should still be called, but with None session_id
            # The helpers themselves short-circuit on None session_id
            mock_val.assert_called_once()
            assert mock_val.call_args[0][0] is None


class TestFactValidationGateAuditTrail:
    """Tests for fact_validation_gate_node audit trail."""

    @pytest.mark.asyncio
    async def test_saves_two_validations(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import fact_validation_gate_node

        state = {"drafting_session_id": "sess-002", "document_type": "demand_letter"}

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation") as mock_val, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output") as mock_out, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase") as mock_phase, \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.return_value = _mock_db_context()

            result = await fact_validation_gate_node(state)

            # Should save two validations: fact_completeness + jurisdiction
            assert mock_val.call_count == 2
            gate_names = [call[0][1] for call in mock_val.call_args_list]
            assert "fact_completeness" in gate_names
            assert "jurisdiction" in gate_names

            mock_phase.assert_called_once_with("sess-002", "FACT_VALIDATION")


class TestClarificationGatePausedBehavior:
    """Tests for clarification_gate_node STOP/RESUME behavior."""

    @pytest.mark.asyncio
    async def test_continues_with_placeholders_when_clarification_needed(self):
        """Clarification gate continues (no PAUSE) — missing fields become placeholders."""
        from app.agents.drafting_agents.nodes.pipeline_gates import clarification_gate_node

        state = {
            "drafting_session_id": "sess-003",
            "llm_classification": {"doc_type": "Bail Application", "confidence": 0.20},
            "fact_validation_result": None,
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_clarification_questions") as mock_cq, \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.return_value = _mock_db_context()

            result = await clarification_gate_node(state)

            # Pipeline continues with CLARIFICATION phase (not PAUSED)
            assert result["drafting_phase"] == "CLARIFICATION"
            assert result["needs_clarification"] is True
            # Missing fields are recorded for placeholder generation
            assert len(result["clarification_questions"]) > 0
            mock_cq.assert_called_once()

    @pytest.mark.asyncio
    async def test_continues_when_no_clarification_needed(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import clarification_gate_node

        state = {
            "drafting_session_id": "sess-004",
            "llm_classification": {"doc_type": "Legal Notice", "confidence": 0.90},
            "fact_validation_result": None,
        }

        # Mock check_clarification_needed to return no-clarification result
        no_clarification = {
            "passed": True,
            "gate": "clarification_handler",
            "needs_clarification": False,
            "questions": [],
            "hard_blocks": [],
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._pause_session") as mock_pause, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_clarification_questions") as mock_cq, \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs, \
             patch("app.agents.drafting_agents.gates.check_clarification_needed", return_value=no_clarification):
            mock_gs.return_value = _mock_db_context()

            result = await clarification_gate_node(state)

            # Phase should NOT be PAUSED
            assert result["drafting_phase"] == "CLARIFICATION"
            assert result["needs_clarification"] is False
            mock_pause.assert_not_called()

    @pytest.mark.asyncio
    async def test_saves_clarification_questions_to_db(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import clarification_gate_node

        state = {
            "drafting_session_id": "sess-005",
            "llm_classification": {"doc_type": "Bail Application", "confidence": 0.20},
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._pause_session"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_clarification_questions") as mock_cq, \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.return_value = _mock_db_context()

            result = await clarification_gate_node(state)

            if result["needs_clarification"]:
                mock_cq.assert_called_once()
                args = mock_cq.call_args[0]
                assert args[0] == "sess-005"
                assert isinstance(args[1], list)

    @pytest.mark.asyncio
    async def test_returns_questions_in_state(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import clarification_gate_node

        state = {
            "drafting_session_id": "sess-006",
            "llm_classification": {"doc_type": "Bail Application", "confidence": 0.20},
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._pause_session"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_clarification_questions"), \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.return_value = _mock_db_context()

            result = await clarification_gate_node(state)

            if result["needs_clarification"]:
                assert "clarification_questions" in result
                assert isinstance(result["clarification_questions"], list)


class TestContextMergeGatePausedBehavior:
    """Tests for context_merge_gate_node hard block → PAUSED."""

    @pytest.mark.asyncio
    async def test_pauses_on_hard_blocks(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import context_merge_gate_node

        state = {
            "drafting_session_id": "sess-007",
            "parallel_outputs": [
                {
                    "type": "compliance_report",
                    "data": {
                        "mandatory_sections": [],
                        "mandatory_annexures": [],
                        "hard_block": True,
                        "hard_block_reason": "Jurisdiction not supported",
                    },
                },
            ],
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._pause_session") as mock_pause, \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.return_value = _mock_db_context()

            result = await context_merge_gate_node(state)

            assert result["drafting_phase"] == "PAUSED"
            assert len(result["hard_blocks"]) > 0
            mock_pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_continues_without_hard_blocks(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import context_merge_gate_node

        state = {
            "drafting_session_id": "sess-008",
            "parallel_outputs": [],
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._pause_session") as mock_pause, \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.return_value = _mock_db_context()

            result = await context_merge_gate_node(state)

            assert result["drafting_phase"] == "CONTEXT_MERGE"
            mock_pause.assert_not_called()


class TestCitationValidationGateTwoPhase:
    """Tests for citation_validation_gate_node two-phase validation."""

    @pytest.mark.asyncio
    async def test_two_phase_both_pass(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import citation_validation_gate_node

        state = {
            "drafting_session_id": "sess-009",
            "citation_pack": {
                "citations": [
                    {"citation_text": "Good Case", "confidence": 0.90, "verification_hash": "h1"},
                ],
            },
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation") as mock_val, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase"), \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            # Mock DB to return the hash
            mock_db = _mock_db_context()
            mock_db.exec = MagicMock(return_value=MagicMock(all=MagicMock(return_value=["h1"])))
            mock_gs.return_value = mock_db

            result = await citation_validation_gate_node(state)

            assert result["citation_validation_result"]["passed"] is True
            # Should save two validations: confidence + hash
            assert mock_val.call_count == 2
            gate_names = [c[0][1] for c in mock_val.call_args_list]
            assert "citation_confidence" in gate_names
            assert "citation_hash_verification" in gate_names

    @pytest.mark.asyncio
    async def test_confidence_fails_hash_passes(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import citation_validation_gate_node

        state = {
            "drafting_session_id": "sess-010",
            "citation_pack": {
                "citations": [
                    {"citation_text": "Low Conf", "confidence": 0.30, "verification_hash": "h1"},
                ],
            },
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase"), \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_db = _mock_db_context()
            mock_db.exec = MagicMock(return_value=MagicMock(all=MagicMock(return_value=["h1"])))
            mock_gs.return_value = mock_db

            result = await citation_validation_gate_node(state)

            combined = result["citation_validation_result"]
            assert combined["passed"] is False  # confidence failed
            assert combined["confidence_check"]["passed"] is False
            assert combined["hash_verification"]["passed"] is True

    @pytest.mark.asyncio
    async def test_confidence_passes_hash_fails(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import citation_validation_gate_node

        state = {
            "drafting_session_id": "sess-011",
            "citation_pack": {
                "citations": [
                    {"citation_text": "High Conf", "confidence": 0.90, "verification_hash": "unknown"},
                ],
            },
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase"), \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_db = _mock_db_context()
            mock_db.exec = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            mock_gs.return_value = mock_db

            result = await citation_validation_gate_node(state)

            combined = result["citation_validation_result"]
            assert combined["passed"] is False
            assert combined["confidence_check"]["passed"] is True
            assert combined["hash_verification"]["passed"] is False

    @pytest.mark.asyncio
    async def test_empty_citations_both_pass(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import citation_validation_gate_node

        state = {
            "drafting_session_id": "sess-012",
            "citation_pack": {"citations": []},
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase"), \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.return_value = _mock_db_context()

            result = await citation_validation_gate_node(state)

            assert result["citation_validation_result"]["passed"] is True

    @pytest.mark.asyncio
    async def test_updates_phase_to_citation_validation(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import citation_validation_gate_node

        state = {"drafting_session_id": "sess-013", "citation_pack": {"citations": []}}

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase") as mock_phase, \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.return_value = _mock_db_context()

            result = await citation_validation_gate_node(state)

            assert result["drafting_phase"] == "CITATION_VALIDATION"
            mock_phase.assert_called_once_with("sess-013", "CITATION_VALIDATION")


class TestPromotionGateAuditTrail:
    """Tests for promotion_gate_node audit trail + DB interaction."""

    @pytest.mark.asyncio
    async def test_saves_audit_trail(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import promotion_gate_node

        state = {"drafting_session_id": "sess-014", "document_type": "motion"}

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation") as mock_val, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output") as mock_out, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase") as mock_phase, \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_db = _mock_db_context()
            # Mock staging repo to return no ready rules
            mock_gs.return_value = mock_db

            result = await promotion_gate_node(state)

            mock_val.assert_called_once()
            assert mock_val.call_args[0][1] == "promotion_gate"
            mock_out.assert_called_once()
            mock_phase.assert_called_once_with("sess-014", "PROMOTION")

    @pytest.mark.asyncio
    async def test_sets_phase_to_promotion(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import promotion_gate_node

        state = {"drafting_session_id": "sess-015"}

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase"), \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.return_value = _mock_db_context()

            result = await promotion_gate_node(state)

            assert result["drafting_phase"] == "PROMOTION"
            assert "promotion_result" in result


class TestExportGateAuditTrail:
    """Tests for export_gate_node audit trail + draft persistence."""

    @pytest.mark.asyncio
    async def test_saves_validation_and_output(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import export_gate_node

        state = {
            "drafting_session_id": "sess-016",
            "final_draft": {
                "title": "Test Draft",
                "sections": [{"title": "Body", "content": "Content here " * 20}],
            },
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_validation") as mock_val, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output") as mock_out, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase") as mock_phase, \
             patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.return_value = _mock_db_context()

            result = await export_gate_node(state)

            mock_val.assert_called_once()
            assert mock_val.call_args[0][1] == "export_engine"
            mock_out.assert_called_once()
            mock_phase.assert_called_once_with("sess-016", "EXPORT")
            assert result["drafting_phase"] == "EXPORT"


class TestStagingRulesNodeAuditTrail:
    """Tests for staging_rules_node audit trail."""

    @pytest.mark.asyncio
    async def test_saves_agent_output(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import staging_rules_node

        state = {
            "drafting_session_id": "sess-017",
            "error_report": {"candidate_rules": []},
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output") as mock_out, \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase") as mock_phase:
            result = await staging_rules_node(state)

            mock_out.assert_called_once()
            assert mock_out.call_args[0][1] == "staging_rules"
            mock_phase.assert_called_once_with("sess-017", "STAGING_RULES")

    @pytest.mark.asyncio
    async def test_empty_rules_no_db_call(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import staging_rules_node

        state = {
            "drafting_session_id": "sess-018",
            "error_report": {"candidate_rules": []},
        }

        with patch("app.agents.drafting_agents.nodes.pipeline_gates._save_agent_output"), \
             patch("app.agents.drafting_agents.nodes.pipeline_gates._update_session_phase"):
            result = await staging_rules_node(state)

            assert result["candidate_rules"] == []
            assert result["drafting_phase"] == "STAGING_RULES"


# =========================================================================
# 4. Audit trail helper unit tests
# =========================================================================

class TestAuditTrailHelpers:
    """Tests for the _save_* helper functions."""

    def test_save_validation_skips_on_none_session(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _save_validation

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            _save_validation(None, "test_gate", True, {"detail": "test"})
            mock_gs.assert_not_called()

    def test_save_validation_skips_on_empty_session(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _save_validation

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            _save_validation("", "test_gate", True, {"detail": "test"})
            mock_gs.assert_not_called()

    def test_save_agent_output_skips_on_none_session(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _save_agent_output

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            _save_agent_output(None, "agent", "type", {"data": 1})
            mock_gs.assert_not_called()

    def test_update_session_phase_skips_on_none_session(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _update_session_phase

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            _update_session_phase(None, "SECURITY")
            mock_gs.assert_not_called()

    def test_pause_session_skips_on_none_session(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _pause_session

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            _pause_session(None, "reason")
            mock_gs.assert_not_called()

    def test_save_clarification_questions_skips_on_none_session(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _save_clarification_questions

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            _save_clarification_questions(None, [{"field": "jurisdiction"}])
            mock_gs.assert_not_called()

    def test_save_clarification_questions_skips_on_empty_questions(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _save_clarification_questions

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            _save_clarification_questions("sess-100", [])
            mock_gs.assert_not_called()

    def test_save_clarification_questions_skips_on_none_questions(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _save_clarification_questions

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            _save_clarification_questions("sess-100", None)
            mock_gs.assert_not_called()

    def test_save_validation_handles_db_error(self):
        """DB errors should be caught, not raised."""
        from app.agents.drafting_agents.nodes.pipeline_gates import _save_validation

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.side_effect = Exception("DB connection failed")
            # Should NOT raise
            _save_validation("sess-err", "gate", True, {})

    def test_save_agent_output_handles_db_error(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _save_agent_output

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.side_effect = Exception("DB connection failed")
            _save_agent_output("sess-err", "agent", "type", {})

    def test_update_session_phase_handles_db_error(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _update_session_phase

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.side_effect = Exception("DB connection failed")
            _update_session_phase("sess-err", "SECURITY")

    def test_pause_session_handles_db_error(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import _pause_session

        with patch("app.database.postgresql.postgresql_connection.get_session") as mock_gs:
            mock_gs.side_effect = Exception("DB connection failed")
            _pause_session("sess-err", "reason")


# =========================================================================
# 5. Combined confidence + hash tests (end-to-end gate function)
# =========================================================================

class TestCombinedCitationValidation:
    """Tests combining check_citation_confidence + verify_citation_hashes
    as used in the citation_validation_gate_node."""

    def test_both_pass(self):
        citations = [
            {"citation_text": "Good", "confidence": 0.90, "verification_hash": "h1"},
        ]
        conf = check_citation_confidence(citations)
        hashes = verify_citation_hashes(citations, {"h1"})
        assert conf["passed"] is True
        assert hashes["passed"] is True

    def test_confidence_only_fails(self):
        citations = [
            {"citation_text": "Low", "confidence": 0.30, "verification_hash": "h1"},
        ]
        conf = check_citation_confidence(citations)
        hashes = verify_citation_hashes(citations, {"h1"})
        assert conf["passed"] is False
        assert hashes["passed"] is True

    def test_hash_only_fails(self):
        citations = [
            {"citation_text": "No Hash", "confidence": 0.90},
        ]
        conf = check_citation_confidence(citations)
        hashes = verify_citation_hashes(citations, set())
        assert conf["passed"] is True
        assert hashes["passed"] is False

    def test_both_fail(self):
        citations = [
            {"citation_text": "Bad", "confidence": 0.30},
        ]
        conf = check_citation_confidence(citations)
        hashes = verify_citation_hashes(citations, set())
        assert conf["passed"] is False
        assert hashes["passed"] is False

    def test_source_doc_id_saves_confidence_but_not_hash(self):
        """source_doc_id passes confidence check but doesn't help hash check."""
        citations = [
            {"citation_text": "With Doc", "confidence": 0.30, "source_doc_id": "DOC-1"},
        ]
        conf = check_citation_confidence(citations)
        hashes = verify_citation_hashes(citations, set())
        assert conf["passed"] is True  # source_doc_id saves it
        assert hashes["passed"] is False  # no hash -> discarded

    def test_mixed_batch(self):
        """Batch with good, confidence-only-bad, and hash-only-bad citations."""
        citations = [
            {"citation_text": "Perfect", "confidence": 0.95, "verification_hash": "h1"},
            {"citation_text": "Low Conf", "confidence": 0.30, "verification_hash": "h2"},
            {"citation_text": "No Hash", "confidence": 0.90},
        ]
        verified = {"h1", "h2"}

        conf = check_citation_confidence(citations)
        hashes = verify_citation_hashes(citations, verified)

        assert conf["passed"] is False  # Low Conf fails
        assert hashes["passed"] is False  # No Hash fails
        assert conf["details"]["failing_citations"] == 1
        assert hashes["details"]["discarded"] == 1


# =========================================================================
# 6. should_clarify routing tests (expanded)
# =========================================================================

class TestShouldClarifyRouting:
    """should_clarify always continues — missing info becomes placeholders."""

    def test_always_continues_even_when_clarification_needed(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import should_clarify
        assert should_clarify({"needs_clarification": True, "clarification_questions": []}) == "mistake_rules_fetch"

    def test_continues_on_false(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import should_clarify
        assert should_clarify({"needs_clarification": False}) == "mistake_rules_fetch"

    def test_continues_on_missing_key(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import should_clarify
        assert should_clarify({}) == "mistake_rules_fetch"

    def test_continues_on_none(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import should_clarify
        assert should_clarify({"needs_clarification": None}) == "mistake_rules_fetch"

    def test_continues_on_zero(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import should_clarify
        assert should_clarify({"needs_clarification": 0}) == "mistake_rules_fetch"

    def test_continues_on_truthy(self):
        from app.agents.drafting_agents.nodes.pipeline_gates import should_clarify
        assert should_clarify({"needs_clarification": 1, "clarification_questions": []}) == "mistake_rules_fetch"
        assert should_clarify({"needs_clarification": "yes", "clarification_questions": []}) == "mistake_rules_fetch"
