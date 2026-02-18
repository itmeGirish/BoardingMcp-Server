"""
Backend tools for the Drafting Agent — draft generation, rules, and quality checks.
"""
import json
import uuid
import concurrent.futures
from langchain.tools import tool
from ....config import logger

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


def _run_get_applicable_rules_sync(drafting_session_id: str):
    """Get applicable promoted rules for the session's document type."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        DraftingSessionRepository, MainRuleRepository,
    )

    with get_session() as session:
        session_repo = DraftingSessionRepository(session=session)
        record = session_repo.get_by_id(drafting_session_id)
        if not record:
            return {"status": "failed", "message": "Session not found"}

        rule_repo = MainRuleRepository(session=session)
        rules = rule_repo.get_rules_for_document(
            document_type=record.get("document_type", "other"),
            jurisdiction=record.get("jurisdiction"),
            court_type=record.get("court_type"),
            case_category=record.get("case_category"),
        )
        if not rules:
            return {
                "status": "success",
                "rules": [],
                "count": 0,
                "message": "No promoted rules found. Proceed with drafting using template pack and context only.",
            }
        return {"status": "success", "rules": rules, "count": len(rules)}


@tool
def get_applicable_rules(drafting_session_id: str) -> str:
    """
    Get promoted rules/patterns applicable to this drafting session.

    Returns rules matched by document type, jurisdiction, and court.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with list of applicable rules
    """
    logger.info("[DRAFTING] get_applicable_rules for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_applicable_rules_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DRAFTING] get_applicable_rules error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_save_draft_sync(drafting_session_id: str, draft_content: str):
    """Save generated draft content."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        DraftingSessionRepository, AgentOutputRepository,
    )

    with get_session() as session:
        session_repo = DraftingSessionRepository(session=session)
        session_repo.save_draft(drafting_session_id, draft_content)

        output_repo = AgentOutputRepository(session=session)
        output_repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="drafting",
            output_type="draft",
            output_data=draft_content,
        )
        return {
            "status": "success",
            "content_length": len(draft_content),
            "message": "Draft saved successfully.",
        }


@tool
def save_draft(drafting_session_id: str, draft_content: str) -> str:
    """
    Save the generated draft document.

    Args:
        drafting_session_id: The drafting session ID
        draft_content: The full draft text content

    Returns:
        JSON with save confirmation
    """
    logger.info("[DRAFTING] save_draft for session %s (%d chars)", drafting_session_id, len(draft_content))
    try:
        future = _executor.submit(_run_save_draft_sync, drafting_session_id, draft_content)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DRAFTING] save_draft error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_save_to_staging_sync(drafting_session_id: str, patterns: list):
    """Save new patterns to staging rules (anti-pollution pipeline)."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        DraftingSessionRepository, StagingRuleRepository,
    )

    with get_session() as session:
        session_repo = DraftingSessionRepository(session=session)
        record = session_repo.get_by_id(drafting_session_id)
        if not record:
            return {"status": "failed", "message": "Session not found"}

        staging_repo = StagingRuleRepository(session=session)
        results = []
        for p in patterns:
            result = staging_repo.add_or_increment(
                rule_type=p.get("rule_type", "template_pattern"),
                document_type=record.get("document_type", "other"),
                rule_content=p.get("rule_content", ""),
                jurisdiction=record.get("jurisdiction"),
                court_type=record.get("court_type"),
                case_category=record.get("case_category"),
            )
            results.append(result)

        return {
            "status": "success",
            "patterns_processed": len(results),
            "results": results,
        }


@tool
def save_to_staging_rules(drafting_session_id: str, patterns: list[dict]) -> str:
    """
    Save new structural patterns to staging rules for future promotion.

    Patterns must NOT contain case-specific content (names, addresses, case numbers).
    Only structural patterns are saved.

    Args:
        drafting_session_id: The drafting session ID
        patterns: List of pattern dicts [{rule_type, rule_content}]

    Returns:
        JSON with staging results
    """
    logger.info("[DRAFTING] save_to_staging_rules: %d patterns", len(patterns))
    try:
        future = _executor.submit(_run_save_to_staging_sync, drafting_session_id, patterns)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DRAFTING] save_to_staging_rules error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_draft_quality_sync(drafting_session_id: str):
    """Run draft quality gate."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        DraftingSessionRepository, ValidationRepository,
    )
    from app.agents.drafting_agents.gates import check_draft_quality

    with get_session() as session:
        session_repo = DraftingSessionRepository(session=session)
        record = session_repo.get_by_id(drafting_session_id)
        if not record:
            return {"status": "failed", "message": "Session not found"}

        draft_content = record.get("draft_content", "")
        document_type = record.get("document_type", "other")

        gate_result = check_draft_quality(draft_content, document_type)

        # Record gate result
        val_repo = ValidationRepository(session=session)
        val_repo.create(
            validation_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            gate_name="draft_quality",
            passed=gate_result["passed"],
            details=json.dumps(gate_result["details"]),
        )

        return gate_result


@tool
def run_draft_quality_check(drafting_session_id: str) -> str:
    """
    Run the draft quality validation gate.

    Checks structural quality: required sections, no placeholders, minimum length.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with gate result
    """
    logger.info("[DRAFTING] run_draft_quality_check for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_draft_quality_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DRAFTING] draft_quality_check error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


BACKEND_TOOLS = [get_applicable_rules, save_draft, save_to_staging_rules, run_draft_quality_check]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
