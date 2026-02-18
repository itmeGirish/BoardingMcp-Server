"""
Pipeline gate nodes — deterministic, NO LLM.

These functions run as graph nodes in the 18-step pipeline.
Each reads from state, runs a gate, and writes results back to state.

All gates persist to audit trail:
  - ValidationRepository  (gate pass/fail records)
  - AgentOutputRepository (intermediate outputs)
  - DraftingSessionRepository (phase updates, pause/resume)
  - ClarificationHistoryRepository (clarification Q&A)
"""
import json
import uuid
from ....config import logger


# ── Audit trail helpers ──────────────────────────────────────────────

def _save_validation(session_id, gate_name, passed, details_dict):
    """Persist gate result to validation_reports table."""
    if not session_id:
        return
    try:
        from app.database.postgresql.postgresql_connection import get_session
        from app.database.postgresql.postgresql_repositories.drafting import ValidationRepository
        with get_session() as db:
            repo = ValidationRepository(session=db)
            repo.create(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                gate_name=gate_name,
                passed=passed,
                details=json.dumps(details_dict, default=str),
            )
    except Exception as e:
        logger.error(f"[Pipeline] Audit validation save error ({gate_name}): {e}")


def _save_agent_output(session_id, agent_name, output_type, output_data):
    """Persist intermediate output to agent_outputs table."""
    if not session_id:
        return
    try:
        from app.database.postgresql.postgresql_connection import get_session
        from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository
        with get_session() as db:
            repo = AgentOutputRepository(session=db)
            repo.create(
                output_id=str(uuid.uuid4()),
                session_id=session_id,
                agent_name=agent_name,
                output_type=output_type,
                output_data=json.dumps(output_data, default=str),
            )
    except Exception as e:
        logger.error(f"[Pipeline] Audit output save error ({agent_name}/{output_type}): {e}")


def _update_session_phase(session_id, phase):
    """Update drafting_sessions.phase in DB."""
    if not session_id:
        return
    try:
        from app.database.postgresql.postgresql_connection import get_session
        from app.database.postgresql.postgresql_repositories.drafting import DraftingSessionRepository
        with get_session() as db:
            repo = DraftingSessionRepository(session=db)
            repo.update_phase(session_id, phase)
    except Exception as e:
        logger.error(f"[Pipeline] Session phase update error ({phase}): {e}")


def _pause_session(session_id, reason):
    """Pause a session in the DB (CLAUDE.md Section 5.3)."""
    if not session_id:
        return
    try:
        from app.database.postgresql.postgresql_connection import get_session
        from app.database.postgresql.postgresql_repositories.drafting import DraftingSessionRepository
        with get_session() as db:
            repo = DraftingSessionRepository(session=db)
            repo.pause_session(session_id, reason)
    except Exception as e:
        logger.error(f"[Pipeline] Session pause error: {e}")


def _save_clarification_questions(session_id, questions):
    """Persist clarification questions to clarification_history DB."""
    if not session_id or not questions:
        return
    try:
        from app.database.postgresql.postgresql_connection import get_session
        from app.database.postgresql.postgresql_repositories.drafting import ClarificationHistoryRepository
        with get_session() as db:
            repo = ClarificationHistoryRepository(session=db)
            for q in questions:
                repo.create(
                    clarification_id=str(uuid.uuid4()),
                    session_id=session_id,
                    question=q.get("question", q.get("text", "")),
                    field_name=q.get("field", "unknown"),
                )
    except Exception as e:
        logger.error(f"[Pipeline] Clarification save error: {e}")


# ── Gate nodes ───────────────────────────────────────────────────────

async def security_gate_node(state):
    """Step 1: Security + Normalization (NO LLM)."""
    from ..gates import sanitize_input

    session_id = state.get("drafting_session_id")
    last_msg = state.get("messages", [])[-1] if state.get("messages") else None
    query = getattr(last_msg, "content", "") if last_msg else ""

    result = sanitize_input(query)
    passed = result["passed"]
    logger.info(f"[Pipeline] Step 1 security_gate: passed={passed}")

    # Audit trail
    _save_validation(session_id, "security_normalizer", passed, result)
    _save_agent_output(session_id, "security_gate", "sanitized_input", result)
    _update_session_phase(session_id, "SECURITY")

    return {
        "sanitized_input": result,
        "drafting_phase": "SECURITY",
    }


async def fact_validation_gate_node(state):
    """Step 3: Fact Validation Gate (NO LLM)."""
    from ..gates import check_fact_completeness, check_jurisdiction

    session_id = state.get("drafting_session_id")
    doc_type = state.get("document_type", "other")

    # Fetch facts from DB
    facts = []
    if session_id:
        try:
            from app.database.postgresql.postgresql_connection import get_session
            from app.database.postgresql.postgresql_repositories.drafting import DraftingFactRepository
            with get_session() as db:
                repo = DraftingFactRepository(session=db)
                facts = repo.get_by_session(session_id)
        except Exception as e:
            logger.error(f"[Pipeline] Step 3 fact fetch error: {e}")

    completeness = check_fact_completeness(facts, doc_type)
    jurisdiction = check_jurisdiction(facts, doc_type)

    passed = completeness["passed"] and jurisdiction["passed"]
    result = {
        "fact_completeness": completeness,
        "jurisdiction": jurisdiction,
        "passed": passed,
    }

    logger.info(f"[Pipeline] Step 3 fact_validation: passed={passed}")

    # Audit trail
    _save_validation(session_id, "fact_completeness", completeness["passed"], completeness)
    _save_validation(session_id, "jurisdiction", jurisdiction["passed"], jurisdiction)
    _save_agent_output(session_id, "fact_validation_gate", "fact_validation_report", result)
    _update_session_phase(session_id, "FACT_VALIDATION")

    return {
        "fact_validation_result": result,
        "drafting_phase": "FACT_VALIDATION",
    }


async def rule_classifier_gate_node(state):
    """Step 4A: Rule Classifier (NO LLM)."""
    from ..gates import classify_by_rules

    session_id = state.get("drafting_session_id")
    sanitized = state.get("sanitized_input", {})
    query = sanitized.get("sanitized_query", "")

    facts = []
    if session_id:
        try:
            from app.database.postgresql.postgresql_connection import get_session
            from app.database.postgresql.postgresql_repositories.drafting import DraftingFactRepository
            with get_session() as db:
                repo = DraftingFactRepository(session=db)
                facts = repo.get_by_session(session_id)
        except Exception as e:
            logger.error(f"[Pipeline] Step 4A fact fetch error: {e}")

    result = classify_by_rules(facts, query)
    logger.info(
        f"[Pipeline] Step 4A rule_classifier: domain={result.get('legal_domain_guess')}, "
        f"doc_type={result.get('doc_type_guess')}"
    )

    # Audit trail
    _save_validation(session_id, "rule_classifier", True, result)
    _save_agent_output(session_id, "rule_classifier_gate", "rule_classification", result)

    return {"rule_classification": result}


async def route_resolver_gate_node(state):
    """Step 4C: Route Resolver (NO LLM)."""
    from ..gates import resolve_route

    session_id = state.get("drafting_session_id")
    rule_cls = state.get("rule_classification", {})
    llm_cls = state.get("llm_classification", {})

    result = resolve_route(rule_cls, llm_cls)
    passed = result["passed"]
    logger.info(
        f"[Pipeline] Step 4C route_resolver: passed={passed}, "
        f"doc_type={result.get('resolved_route', {}).get('doc_type')}"
    )

    # Audit trail
    _save_validation(session_id, "route_resolver", passed, result)
    _save_agent_output(session_id, "route_resolver_gate", "workflow_route", result)
    _update_session_phase(session_id, "ROUTE_RESOLUTION")

    return {
        "resolved_route": result.get("resolved_route"),
        "drafting_phase": "ROUTE_RESOLUTION",
    }


async def clarification_gate_node(state):
    """Step 5: Clarification Handler — continue with placeholders.

    Instead of pausing the pipeline, this gate:
    1. Records what info is missing (clarification_questions)
    2. Continues to drafting — missing fields become {{PLACEHOLDER}} in the draft
    3. Shows recommendations to the lawyer to fill in later

    The pipeline NEVER pauses. Lawyers get a full draft immediately.
    """
    from ..gates import check_clarification_needed

    session_id = state.get("drafting_session_id")
    classification = state.get("llm_classification", {})
    gate_results = []

    if state.get("fact_validation_result"):
        gate_results.append(state["fact_validation_result"])

    facts = []
    if session_id:
        try:
            from app.database.postgresql.postgresql_connection import get_session
            from app.database.postgresql.postgresql_repositories.drafting import DraftingFactRepository
            with get_session() as db:
                repo = DraftingFactRepository(session=db)
                facts = repo.get_by_session(session_id)
        except Exception as e:
            logger.error(f"[Pipeline] Step 5 fact fetch error: {e}")

    result = check_clarification_needed(facts, classification, gate_results)
    needs_cl = result.get("needs_clarification", False)
    questions = result.get("questions", [])
    hard_blocks = result.get("hard_blocks", [])

    logger.info(f"[Pipeline] Step 5 clarification: needs_clarification={needs_cl}")

    # Audit trail
    _save_validation(session_id, "clarification_handler", not needs_cl, result)
    _save_agent_output(session_id, "clarification_gate", "clarification_result", result)

    if needs_cl:
        # Log what's missing — but DO NOT pause
        missing_fields = [q.get("field", "?") for q in questions]
        logger.info(
            f"[Pipeline] Missing fields: {', '.join(missing_fields)} — "
            f"continuing with placeholders"
        )
        _save_clarification_questions(session_id, questions)

    # Always continue — never pause. Missing data = placeholders in draft.
    update = {
        "needs_clarification": needs_cl,
        "drafting_phase": "CLARIFICATION",
        "clarification_questions": questions,
        "hard_blocks": hard_blocks,
    }

    return update


async def mistake_rules_fetch_node(state):
    """Step 6: Fetch Mistake Rules from Main DB (NO LLM)."""
    session_id = state.get("drafting_session_id")
    doc_type = state.get("document_type")
    jurisdiction = state.get("jurisdiction")
    resolved = state.get("resolved_route", {})
    court_type = resolved.get("court_type") if resolved else None

    rules = []
    if session_id:
        try:
            from app.database.postgresql.postgresql_connection import get_session
            from app.database.postgresql.postgresql_repositories.drafting import MainRuleRepository
            with get_session() as db:
                repo = MainRuleRepository(session=db)
                rules = repo.get_rules_for_document(
                    document_type=doc_type or "",
                    jurisdiction=jurisdiction,
                    court_type=court_type,
                )
        except Exception as e:
            logger.error(f"[Pipeline] Step 6 rules fetch error: {e}")

    checklist = {"rules": rules, "count": len(rules)}
    logger.info(f"[Pipeline] Step 6 mistake_rules: {len(rules)} rules fetched")

    # Audit trail
    _save_agent_output(session_id, "mistake_rules_fetch", "mistake_checklist", checklist)

    return {"mistake_checklist": checklist}


async def citation_validation_gate_node(state):
    """Step 10: Citation Validation Gate (NO LLM).

    Two-phase validation per CLAUDE.md Section 2.2:
    1. Confidence check (>= 0.75 or source_doc_id)
    2. Hash verification against verified_citations DB
    """
    from ..gates import check_citation_confidence, verify_citation_hashes

    session_id = state.get("drafting_session_id")
    citation_pack = state.get("citation_pack", {})
    citations = citation_pack.get("citations", []) if isinstance(citation_pack, dict) else []

    # Also try fetching from DB if citation_pack is in agent_outputs
    if not citations and session_id:
        try:
            from app.database.postgresql.postgresql_connection import get_session
            from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository
            with get_session() as db:
                repo = AgentOutputRepository(session=db)
                pack = repo.get_latest_by_type(session_id, "citation_pack")
                if pack:
                    data = json.loads(pack.get("output_data", "{}"))
                    citations = data.get("citations", [])
        except Exception as e:
            logger.error(f"[Pipeline] Step 10 citation fetch error: {e}")

    # Phase 1: Confidence check
    confidence_result = check_citation_confidence(citations)

    # Phase 2: Hash verification against verified_citations DB
    verified_hashes = set()
    try:
        from app.database.postgresql.postgresql_connection import get_session
        from app.database.postgresql.models.drafting import VerifiedCitation
        from sqlmodel import select
        with get_session() as db:
            stmt = select(VerifiedCitation.citation_hash).where(
                VerifiedCitation.verified_at.isnot(None)
            )
            rows = db.exec(stmt).all()
            verified_hashes = set(rows)
    except Exception as e:
        logger.error(f"[Pipeline] Step 10 hash lookup error: {e}")

    hash_result = verify_citation_hashes(citations, verified_hashes)

    # Combined result: both checks must pass
    passed = confidence_result["passed"] and hash_result["passed"]
    combined = {
        "confidence_check": confidence_result,
        "hash_verification": hash_result,
        "passed": passed,
        "verified_citations": hash_result.get("verified_citations", []),
        "discarded_citations": hash_result.get("discarded_citations", []),
    }

    logger.info(
        f"[Pipeline] Step 10 citation_validation: passed={passed}, "
        f"confidence_ok={confidence_result['passed']}, hash_ok={hash_result['passed']}"
    )

    # Audit trail
    _save_validation(session_id, "citation_confidence", confidence_result["passed"], confidence_result)
    _save_validation(session_id, "citation_hash_verification", hash_result["passed"], hash_result)
    _save_agent_output(session_id, "citation_validation_gate", "citation_validation_report", combined)
    _update_session_phase(session_id, "CITATION_VALIDATION")

    return {
        "citation_validation_result": combined,
        "drafting_phase": "CITATION_VALIDATION",
    }


async def context_merge_gate_node(state):
    """Step 11: Context Merge + Conflict Resolver (NO LLM)."""
    from ..gates import merge_context

    session_id = state.get("drafting_session_id")

    # Collect outputs from parallel and optional agents
    template_pack = {}
    compliance_report = {}
    local_rules = {}
    prayer_pack = {}
    research_bundle = state.get("research_bundle")
    citation_pack = state.get("citation_pack")
    mistake_checklist = state.get("mistake_checklist")

    # Extract parallel outputs
    for item in state.get("parallel_outputs", []):
        out_type = item.get("type", "")
        if out_type == "compliance_report":
            compliance_report = item.get("data", {})
        elif out_type == "local_rules":
            local_rules = item.get("data", {})
        elif out_type == "prayer_pack":
            prayer_pack = item.get("data", {})

    # Fetch template_pack + facts from DB in a single session
    master_facts = {}
    if session_id:
        try:
            from app.database.postgresql.postgresql_connection import get_session
            from app.database.postgresql.postgresql_repositories.drafting import (
                AgentOutputRepository, DraftingFactRepository,
            )
            with get_session() as db:
                # Template pack
                output_repo = AgentOutputRepository(session=db)
                tp = output_repo.get_latest_by_type(session_id, "template_pack")
                if tp:
                    template_pack = json.loads(tp.get("output_data", "{}"))
                # Master facts
                fact_repo = DraftingFactRepository(session=db)
                facts = fact_repo.get_by_session(session_id)
                master_facts = {"facts": facts}
        except Exception as e:
            logger.error(f"[Pipeline] Step 11 DB fetch error: {e}")

    result = merge_context(
        template_pack=template_pack,
        compliance_report=compliance_report,
        local_rules=local_rules,
        prayer_pack=prayer_pack,
        research_bundle=research_bundle,
        citation_pack=citation_pack,
        mistake_checklist=mistake_checklist,
        master_facts=master_facts,
        clarification_questions=state.get("clarification_questions"),
    )

    passed = result["passed"]
    hard_blocks = result.get("hard_blocks", [])
    logger.info(f"[Pipeline] Step 11 context_merge: passed={passed}")

    # Audit trail
    _save_validation(session_id, "context_merger", passed, result)
    _save_agent_output(session_id, "context_merge_gate", "draft_context", result.get("draft_context", {}))
    _update_session_phase(session_id, "CONTEXT_MERGE")

    # If hard_blocks exist, pause session (CLAUDE.md Section 2.4)
    if hard_blocks:
        reasons = [b.get("reason", "unknown") for b in hard_blocks]
        _pause_session(session_id, f"Hard blocks in context merge: {'; '.join(reasons)}")

    return {
        "draft_context": result.get("draft_context"),
        "drafting_phase": "PAUSED" if hard_blocks else "CONTEXT_MERGE",
        "hard_blocks": hard_blocks,
    }


async def staging_rules_node(state):
    """Step 14: Store Candidate Rules in Staging DB (NO LLM).

    Candidate rules come from the quality agent's ERROR_REPORT.
    Each is added to staging_rules (or occurrence_count incremented).
    """
    session_id = state.get("drafting_session_id")
    error_report = state.get("error_report", {})
    candidate_rules = error_report.get("candidate_rules", []) if error_report else []

    stored = []
    if session_id and candidate_rules:
        try:
            from app.database.postgresql.postgresql_connection import get_session
            from app.database.postgresql.postgresql_repositories.drafting import StagingRuleRepository
            with get_session() as db:
                repo = StagingRuleRepository(session=db)
                for rule in candidate_rules:
                    result = repo.add_or_increment(
                        rule_type=rule.get("rule_type", "pattern"),
                        document_type=state.get("document_type", ""),
                        rule_content=json.dumps(rule.get("content", rule), default=str),
                        jurisdiction=state.get("jurisdiction"),
                        court_type=(state.get("resolved_route") or {}).get("court_type"),
                    )
                    stored.append(result)
        except Exception as e:
            logger.error(f"[Pipeline] Step 14 staging save error: {e}")

    logger.info(f"[Pipeline] Step 14 staging: {len(stored)} rules stored/incremented")

    # Audit trail
    _save_agent_output(session_id, "staging_rules", "staging_results", stored)
    _update_session_phase(session_id, "STAGING_RULES")

    return {
        "candidate_rules": stored,
        "drafting_phase": "STAGING_RULES",
    }


async def promotion_gate_node(state):
    """Steps 15-17: Promotion Gate + Update Main DB + Logging (NO LLM).

    1. Fetch all promotion-ready staging rules from DB (occurrence_count >= 3)
    2. Run check_promotion_eligibility against existing main rules
    3. Promote eligible rules: create in main_rules, mark staging, log
    """
    from ..gates import check_promotion_eligibility

    session_id = state.get("drafting_session_id")

    # Fetch, evaluate, and promote in a single DB session for atomicity
    staging_data = []
    existing_main = []
    promoted = []
    candidates = []
    try:
        from app.database.postgresql.postgresql_connection import get_session
        from app.database.postgresql.postgresql_repositories.drafting import (
            StagingRuleRepository, MainRuleRepository, PromotionLogRepository,
        )
        with get_session() as db:
            staging_repo = StagingRuleRepository(session=db)
            main_repo = MainRuleRepository(session=db)

            # Phase 1: Fetch promotion-ready staging rules + existing main rules
            ready_rules = staging_repo.get_ready_for_promotion()
            for rule in ready_rules:
                staging_data.append({
                    "id": rule.id,
                    "rule_type": rule.rule_type,
                    "document_type": rule.document_type,
                    "rule_content_raw": rule.rule_content,
                    "occurrence_count": rule.occurrence_count,
                    "jurisdiction": rule.jurisdiction,
                    "court_type": rule.court_type,
                    "case_category": rule.case_category,
                })

            existing_main = main_repo.get_rules_for_document(
                document_type=state.get("document_type", ""),
                jurisdiction=state.get("jurisdiction"),
            )

            # Build candidates for the gate function
            for sd in staging_data:
                content = {}
                try:
                    content = json.loads(sd["rule_content_raw"]) if isinstance(sd["rule_content_raw"], str) else {}
                except (json.JSONDecodeError, TypeError):
                    content = {}

                candidates.append({
                    "rule_id": sd["id"],
                    "rule_content": content.get("text", sd["rule_content_raw"]),
                    "occurrence_count": sd["occurrence_count"],
                    "severity": content.get("severity", "medium"),
                    "section_id": content.get("section_id", ""),
                    "action": content.get("action", ""),
                })

            result = check_promotion_eligibility(candidates, existing_main)
            eligible = result.get("eligible_rules", [])
            rejected = result.get("rejected_rules", [])

            # Phase 2: Promote eligible rules (same session = atomic)
            if eligible:
                promo_repo = PromotionLogRepository(session=db)

                for rule in eligible:
                    staging_id = rule.get("rule_id")
                    if not staging_id:
                        continue

                    sd = next((s for s in staging_data if s["id"] == staging_id), None)
                    if not sd:
                        continue

                    main_id = str(uuid.uuid4())

                    # Step 16: Create main rule
                    main_repo.create_from_promotion(
                        rule_id=main_id,
                        rule_type=sd["rule_type"],
                        document_type=sd["document_type"],
                        rule_content=sd["rule_content_raw"],
                        occurrence_count=sd["occurrence_count"],
                        jurisdiction=sd.get("jurisdiction"),
                        court_type=sd.get("court_type"),
                        case_category=sd.get("case_category"),
                    )

                    # Step 16: Mark staging as promoted
                    staging_repo.mark_promoted(staging_id)

                    # Step 17: Log promotion
                    promo_repo.create(
                        staging_rule_id=staging_id,
                        main_rule_id=main_id,
                        occurrence_count_at_promotion=sd["occurrence_count"],
                    )

                    promoted.append(main_id)
                    logger.info(
                        f"[Pipeline] Promoted staging rule {staging_id} -> main rule {main_id}"
                    )
    except Exception as e:
        logger.error(f"[Pipeline] Steps 15-17 promotion error: {e}")
        result = check_promotion_eligibility(candidates, existing_main)
        eligible = result.get("eligible_rules", [])
        rejected = result.get("rejected_rules", [])

    promotion_result = {
        "promoted": promoted,
        "promoted_count": len(promoted),
        "eligible_count": len(eligible),
        "rejected_count": len(rejected),
    }
    logger.info(
        f"[Pipeline] Steps 15-17: {len(promoted)} promoted, "
        f"{len(eligible)} eligible, {len(rejected)} rejected"
    )

    # Audit trail
    _save_validation(session_id, "promotion_gate", True, result)
    _save_agent_output(session_id, "promotion_gate", "promotion_result", promotion_result)
    _update_session_phase(session_id, "PROMOTION")

    return {
        "promotion_result": promotion_result,
        "drafting_phase": "PROMOTION",
    }


async def export_gate_node(state):
    """Step 18: Export Engine (NO LLM)."""
    from ..gates import prepare_export

    session_id = state.get("drafting_session_id")
    final_draft = state.get("final_draft") or {}

    # If final_draft is empty (review agent only writes to messages),
    # read draft from DB and use draft_v1 as fallback
    if not final_draft or not final_draft.get("sections"):
        # Try draft_v1 from state
        draft_v1 = state.get("draft_v1") or {}
        draft_text = draft_v1.get("draft_text", "")

        # Fallback: read from DB
        if not draft_text and session_id:
            try:
                from app.database.postgresql.postgresql_connection import get_session
                from app.database.postgresql.postgresql_repositories.drafting import DraftingSessionRepository
                with get_session() as db:
                    repo = DraftingSessionRepository(session=db)
                    record = repo.get_by_id(session_id)
                    if record:
                        draft_text = record.get("draft_content", "")
            except Exception as e:
                logger.error(f"[Pipeline] Step 18 draft fallback fetch error: {e}")

        if draft_text:
            final_draft = {
                "title": state.get("document_type", "Legal Document"),
                "sections": [{"title": "Document", "content": draft_text}],
                "text_content": draft_text,
            }

    result = prepare_export(final_draft)
    passed = result["passed"]
    logger.info(f"[Pipeline] Step 18 export: passed={passed}")

    # Save draft content to session + draft_versions table
    if session_id and passed:
        export_content = result.get("export_content", "")
        # For DOCX, save the text representation to session
        text_content = export_content if isinstance(export_content, str) else ""
        try:
            from app.database.postgresql.postgresql_connection import get_session
            from app.database.postgresql.postgresql_repositories.drafting import (
                DraftingSessionRepository, DraftVersionRepository,
            )
            with get_session() as db:
                session_repo = DraftingSessionRepository(session=db)
                session_repo.save_draft(session_id, text_content)

                # Save versioned draft
                version_repo = DraftVersionRepository(session=db)
                # Determine next version number
                latest = version_repo.get_latest(session_id)
                next_version = (latest["version_number"] + 1) if latest else 1

                version_repo.create(
                    version_id=str(uuid.uuid4()),
                    session_id=session_id,
                    version_number=next_version,
                    draft_content=text_content,
                    quality_score=result.get("metadata", {}).get("quality_score"),
                    word_count=result.get("metadata", {}).get("word_count"),
                    agent_name="export_gate",
                )
        except Exception as e:
            logger.error(f"[Pipeline] Step 18 draft save error: {e}")

    # Audit trail
    _save_validation(session_id, "export_engine", passed, result.get("metadata", {}))
    _save_agent_output(session_id, "export_gate", "export_output", result)
    _update_session_phase(session_id, "EXPORT")

    return {
        "export_output": result,
        "drafting_phase": "EXPORT",
    }


# ── Routing functions for conditional edges ──────────────────────────

def should_clarify(state) -> str:
    """Route after clarification gate: always continue to drafting.

    Missing info is handled via {{PLACEHOLDER}} in the draft.
    The lawyer fills in the blanks after seeing the full draft.
    """
    if state.get("needs_clarification"):
        missing = state.get("clarification_questions", [])
        fields = [q.get("field", "?") for q in missing if isinstance(q, dict)]
        logger.info(
            f"[Pipeline] Missing fields ({len(fields)}): {', '.join(fields)} "
            f"— continuing with placeholders"
        )
    return "mistake_rules_fetch"


def should_run_optional_agents(state) -> list[str]:
    """Route after parallel agents: check if research/citation needed."""
    resolved = state.get("resolved_route", {})
    agents_required = []

    if isinstance(resolved, dict):
        agents_required = resolved.get("agents_required", [])

    targets = []
    if "research_agent" in agents_required or "research" in agents_required:
        targets.append("research")
    if "citation_agent" in agents_required or "citation" in agents_required:
        targets.append("citation")

    if not targets:
        return ["citation_validation_gate"]

    return targets


async def fact_traceability_gate_node(state):
    """Step 12B: Fact Traceability Gate (NO LLM).

    Cross-references key entities (amounts, dates, case numbers,
    cheque numbers) in the draft against MASTER_FACTS.  Flags any
    entity that appears in the draft but has no matching fact.
    """
    from ..gates import check_fact_traceability

    session_id = state.get("drafting_session_id")
    draft_content = ""
    facts = []

    # Fetch draft + facts from DB
    if session_id:
        try:
            from app.database.postgresql.postgresql_connection import get_session
            from app.database.postgresql.postgresql_repositories.drafting import (
                DraftingSessionRepository, DraftingFactRepository,
            )
            with get_session() as db:
                session_repo = DraftingSessionRepository(session=db)
                record = session_repo.get_by_id(session_id)
                if record:
                    draft_content = record.get("draft_content", "")

                fact_repo = DraftingFactRepository(session=db)
                facts = fact_repo.get_by_session(session_id)
        except Exception as e:
            logger.error(f"[Pipeline] Step 12B DB fetch error: {e}")

    result = check_fact_traceability(draft_content, facts)
    passed = result["passed"]
    untraced = result.get("untraced_entities", [])

    logger.info(
        f"[Pipeline] Step 12B fact_traceability: passed={passed}, "
        f"untraced={len(untraced)}"
    )

    # Audit trail
    _save_validation(session_id, "fact_traceability", passed, result)
    _save_agent_output(session_id, "fact_traceability_gate", "fact_traceability_report", result)

    # Populate draft_v1 in state from DB (sub-agents only write messages)
    update = {"fact_traceability_result": result}
    if draft_content:
        update["draft_v1"] = {"draft_text": draft_content, "source": "drafting_agent"}

    return update


__all__ = [
    "security_gate_node",
    "fact_validation_gate_node",
    "rule_classifier_gate_node",
    "route_resolver_gate_node",
    "clarification_gate_node",
    "mistake_rules_fetch_node",
    "citation_validation_gate_node",
    "context_merge_gate_node",
    "fact_traceability_gate_node",
    "staging_rules_node",
    "promotion_gate_node",
    "export_gate_node",
    "should_clarify",
    "should_run_optional_agents",
]
