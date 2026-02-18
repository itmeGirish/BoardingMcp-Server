"""
State definitions for legal drafting workflow.

Defines the main agent state and phase types for the 18-step drafting pipeline.
"""
from typing import Optional, Literal, Annotated
from operator import add
from copilotkit import CopilotKitState


def _last_value(existing, new):
    """Reducer: keep the last non-None value. Safe for parallel fan-in."""
    if isinstance(new, list):
        return new[-1] if new else existing
    return new if new is not None else existing


DraftingPhase = Literal[
    "INITIALIZED",
    "SECURITY",
    "INTAKE",
    "FACT_VALIDATION",
    "CLASSIFICATION",
    "ROUTE_RESOLUTION",
    "CLARIFICATION",
    "TEMPLATE_PACK",
    "PARALLEL_AGENTS",
    "OPTIONAL_AGENTS",
    "CITATION_VALIDATION",
    "CONTEXT_MERGE",
    "DRAFTING",
    "REVIEW",
    "STAGING_RULES",
    "PROMOTION",
    "EXPORT",
    "COMPLETED",
    "PAUSED",
    "FAILED",
]


class LegalDraftingState(CopilotKitState):
    """
    Main agent state for the 18-step Legal Drafting pipeline.

    Inherits from CopilotKitState which provides:
    - messages: List of conversation messages
    - Additional CopilotKit-specific fields

    Pipeline state fields track each step's output.

    All Optional fields use _last_value reducer so parallel fan-out/fan-in
    (Steps 8.1-8.3: compliance, localization, prayer) does not conflict.
    Annotated[list, add] fields accumulate values across parallel branches.
    """
    # ── Session tracking ──
    drafting_phase: Annotated[Optional[DraftingPhase], _last_value]
    drafting_session_id: Annotated[Optional[str], _last_value]
    user_id: Annotated[Optional[str], _last_value]

    # ── Step 1: Security gate output ──
    sanitized_input: Annotated[Optional[dict], _last_value]

    # ── Step 2: Intake / Fact Extraction ──
    document_type: Annotated[Optional[str], _last_value]
    jurisdiction: Annotated[Optional[str], _last_value]

    # ── Step 3: Fact validation gate output ──
    fact_validation_result: Annotated[Optional[dict], _last_value]

    # ── Steps 4A-4C: Classification + routing ──
    rule_classification: Annotated[Optional[dict], _last_value]
    llm_classification: Annotated[Optional[dict], _last_value]
    resolved_route: Annotated[Optional[dict], _last_value]

    # ── Step 5: Clarification ──
    needs_clarification: Annotated[Optional[bool], _last_value]
    clarification_questions: Annotated[Optional[list], _last_value]

    # ── Step 6: Mistake rules ──
    mistake_checklist: Annotated[Optional[dict], _last_value]

    # ── Step 7: Template pack ──
    template_pack: Annotated[Optional[dict], _last_value]

    # ── Steps 8.1-8.3: Parallel agent outputs (fan-out/fan-in) ──
    parallel_outputs: Annotated[list, add]

    # ── Steps 9.1-9.2: Optional agents ──
    research_bundle: Annotated[Optional[dict], _last_value]
    citation_pack: Annotated[Optional[dict], _last_value]

    # ── Step 10: Citation validation ──
    citation_validation_result: Annotated[Optional[dict], _last_value]

    # ── Step 11: Merged context ──
    draft_context: Annotated[Optional[dict], _last_value]

    # ── Step 12: Draft ──
    draft_v1: Annotated[Optional[dict], _last_value]

    # ── Step 13: Quality review ──
    final_draft: Annotated[Optional[dict], _last_value]
    error_report: Annotated[Optional[dict], _last_value]

    # ── Steps 14-17: Staging + promotion ──
    candidate_rules: Annotated[Optional[list], _last_value]
    promotion_result: Annotated[Optional[dict], _last_value]

    # ── Step 18: Export ──
    export_output: Annotated[Optional[dict], _last_value]

    # ── Error tracking ──
    error_message: Annotated[Optional[str], _last_value]
    hard_blocks: Annotated[Optional[list], _last_value]


__all__ = ["DraftingPhase", "LegalDraftingState"]
