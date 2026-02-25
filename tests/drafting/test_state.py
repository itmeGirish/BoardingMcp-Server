"""Tests for LegalDraftingState definition."""
import sys
import types
import typing
import json as _json
import pytest
from operator import add

# Compatibility shim for environments where copilotkit expects
# `langgraph.graph.graph.CompiledGraph`.
if "langgraph.graph.graph" not in sys.modules:
    try:
        from langgraph.graph.state import CompiledStateGraph

        compat_mod = types.ModuleType("langgraph.graph.graph")
        compat_mod.CompiledGraph = CompiledStateGraph
        sys.modules["langgraph.graph.graph"] = compat_mod
    except Exception:
        pass

# Compatibility shim for environments without full `langchain` package.
try:
    from langchain.load.dump import dumps as _lc_dumps  # type: ignore # noqa: F401
except Exception:
    langchain_pkg = sys.modules.get("langchain")
    if langchain_pkg is None:
        langchain_pkg = types.ModuleType("langchain")
        sys.modules["langchain"] = langchain_pkg

    load_pkg = sys.modules.get("langchain.load")
    if load_pkg is None:
        load_pkg = types.ModuleType("langchain.load")
        sys.modules["langchain.load"] = load_pkg

    dump_mod = types.ModuleType("langchain.load.dump")

    def _shim_dumps(value):
        try:
            return _json.dumps(value, default=str)
        except Exception:
            return str(value)

    dump_mod.dumps = _shim_dumps
    sys.modules["langchain.load.dump"] = dump_mod

try:
    from langchain.schema import BaseMessage as _LCBaseMessage  # type: ignore # noqa: F401
except Exception:
    schema_mod = types.ModuleType("langchain.schema")
    from langchain_core.messages import BaseMessage, SystemMessage

    schema_mod.BaseMessage = BaseMessage
    schema_mod.SystemMessage = SystemMessage
    sys.modules["langchain.schema"] = schema_mod

from app.agents.drafting_agents.states.legal_drafting import LegalDraftingState, DraftingPhase


class TestDraftingPhase:
    def test_valid_phases(self):
        """Current + retained legacy phases should be valid."""
        valid_phases = [
            "INITIALIZED", "INTAKE", "CLASSIFICATION", "PARALLEL_AGENTS",
            "CONTEXT_MERGE", "DRAFTING", "REVIEW",
            "SECURITY", "ROUTE_RESOLUTION", "CLARIFICATION",
            "TEMPLATE_PACK", "OPTIONAL_AGENTS", "STAGING_RULES",
            "PROMOTION", "EXPORT",
            "COMPLETED", "PAUSED", "FAILED",
        ]
        # Verify all phases exist in the Literal type
        for phase in valid_phases:
            assert phase in DraftingPhase.__args__, f"Missing phase: {phase}"

    def test_phase_count(self):
        """DraftingPhase should have exactly 18 literal values."""
        assert len(DraftingPhase.__args__) == 18

    def test_no_duplicate_phases(self):
        """All phase names must be unique."""
        assert len(DraftingPhase.__args__) == len(set(DraftingPhase.__args__))


class TestLegalDraftingState:
    def test_state_has_session_fields(self):
        """State must have session tracking fields."""
        annotations = LegalDraftingState.__annotations__
        assert "drafting_session_id" in annotations
        assert "user_id" in annotations
        assert "drafting_phase" in annotations

    def test_state_has_pipeline_fields(self):
        """State must have all pipeline step output fields."""
        annotations = LegalDraftingState.__annotations__
        required_fields = [
            "sanitized_input", "document_type", "jurisdiction",
            "rule_classification",
            "llm_classification", "resolved_route",
            "needs_clarification", "template_pack",
            "parallel_outputs", "citation_pack",
            "draft_context", "draft_v1", "final_draft",
            "export_output", "error_message",
        ]
        for field in required_fields:
            assert field in annotations, f"Missing field: {field}"

    def test_parallel_outputs_uses_add_reducer(self):
        """parallel_outputs must use Annotated[list, add] reducer for fan-out/fan-in."""
        annotations = LegalDraftingState.__annotations__
        parallel_type = annotations["parallel_outputs"]
        # Should be Annotated type with the add reducer in its metadata
        assert hasattr(parallel_type, "__metadata__") or "Annotated" in str(parallel_type), \
            "parallel_outputs should be an Annotated type"

    def test_parallel_outputs_reducer_is_add(self):
        """The reducer for parallel_outputs must be operator.add."""
        annotations = LegalDraftingState.__annotations__
        parallel_type = annotations["parallel_outputs"]
        # Annotated[list, add] stores add in __metadata__
        if hasattr(parallel_type, "__metadata__"):
            assert add in parallel_type.__metadata__, \
                "parallel_outputs reducer must be operator.add"

    def test_parallel_outputs_base_is_list(self):
        """parallel_outputs base type should be list."""
        annotations = LegalDraftingState.__annotations__
        parallel_type = annotations["parallel_outputs"]
        origin = typing.get_origin(parallel_type)
        if origin is not None:
            # For Annotated types, get_origin returns Annotated
            args = typing.get_args(parallel_type)
            # First arg of Annotated is the base type
            assert typing.get_origin(args[0]) is list, "parallel_outputs base type should be list"

    def test_optional_fields_are_optional(self):
        """Most state fields should be Optional to allow incremental pipeline execution."""
        annotations = LegalDraftingState.__annotations__
        optional_fields = [
            "drafting_phase", "drafting_session_id", "user_id",
            "sanitized_input", "document_type", "jurisdiction",
            "error_message",
        ]
        for field in optional_fields:
            field_type = annotations[field]
            # Check it's Optional (Union[X, None]) or has None in args
            origin = typing.get_origin(field_type)
            if origin is typing.Union:
                args = typing.get_args(field_type)
                assert type(None) in args, f"{field} should be Optional"

    def test_state_has_clarification_fields(self):
        """State must have clarification step fields."""
        annotations = LegalDraftingState.__annotations__
        assert "needs_clarification" in annotations
        assert "clarification_questions" in annotations

    def test_state_has_mistake_checklist(self):
        """State must have mistake checklist for Step 6."""
        annotations = LegalDraftingState.__annotations__
        assert "mistake_checklist" in annotations

    def test_state_has_staging_promotion_fields(self):
        """State must have staging and promotion fields."""
        annotations = LegalDraftingState.__annotations__
        assert "candidate_rules" in annotations
        assert "promotion_result" in annotations

    def test_state_has_error_report(self):
        """State must have error_report from review step."""
        annotations = LegalDraftingState.__annotations__
        assert "error_report" in annotations

    def test_state_has_hard_blocks(self):
        """State must have hard_blocks list."""
        annotations = LegalDraftingState.__annotations__
        assert "hard_blocks" in annotations

    def test_state_has_workflow_state(self):
        """State must carry canonical workflow_state payload."""
        annotations = LegalDraftingState.__annotations__
        assert "workflow_state" in annotations
