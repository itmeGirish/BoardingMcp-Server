"""
Backend tools for the Review Agent — quality check, finalization, and delivery.
"""
import json
import uuid
import concurrent.futures
from langchain.tools import tool
from ....config import logger

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


def _run_get_draft_sync(drafting_session_id: str):
    """Get the saved draft content."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import DraftingSessionRepository

    with get_session() as session:
        repo = DraftingSessionRepository(session=session)
        record = repo.get_by_id(drafting_session_id)
        if not record:
            return {"status": "failed", "message": "Session not found"}
        return {
            "status": "success",
            "draft_content": record.get("draft_content", ""),
            "document_type": record.get("document_type"),
            "jurisdiction": record.get("jurisdiction"),
            "phase": record.get("phase"),
        }


@tool
def get_draft_content(drafting_session_id: str) -> str:
    """
    Retrieve the generated draft content for review.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with draft content and metadata
    """
    logger.info("[REVIEW] get_draft_content for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_draft_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[REVIEW] get_draft_content error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_get_validations_sync(drafting_session_id: str):
    """Get all validation results."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import ValidationRepository

    with get_session() as session:
        repo = ValidationRepository(session=session)
        validations = repo.get_by_session(drafting_session_id)
        all_passed = repo.all_gates_passed(drafting_session_id)
        return {
            "status": "success",
            "validations": validations,
            "all_gates_passed": all_passed,
        }


@tool
def get_validation_results(drafting_session_id: str) -> str:
    """
    Get all validation gate results for a drafting session.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with all gate results and overall pass/fail
    """
    logger.info("[REVIEW] get_validation_results for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_validations_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[REVIEW] get_validation_results error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_finalize_sync(drafting_session_id: str):
    """Finalize the draft and mark session as complete."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        DraftingSessionRepository, AgentOutputRepository,
    )

    with get_session() as session:
        session_repo = DraftingSessionRepository(session=session)
        record = session_repo.get_by_id(drafting_session_id)
        if not record:
            return {"status": "failed", "message": "Session not found"}

        # Save review output
        output_repo = AgentOutputRepository(session=session)
        output_repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="review",
            output_type="review_notes",
            output_data=json.dumps({"action": "finalized", "phase": "COMPLETED"}),
        )

        return {
            "status": "success",
            "draft_content": record.get("draft_content", ""),
            "document_type": record.get("document_type"),
            "jurisdiction": record.get("jurisdiction"),
            "message": "Draft finalized and ready for delivery.",
        }


@tool
def finalize_and_deliver(drafting_session_id: str) -> str:
    """
    Finalize the draft and prepare for delivery to the user.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with final draft content
    """
    logger.info("[REVIEW] finalize_and_deliver for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_finalize_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[REVIEW] finalize_and_deliver error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_flag_issues_sync(drafting_session_id: str, issues: list):
    """Flag review issues for audit trail."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="review",
            output_type="review_issues",
            output_data=json.dumps(issues),
        )
        return {
            "status": "success",
            "issues_count": len(issues),
            "message": f"Flagged {len(issues)} review issues.",
        }


@tool
def flag_review_issues(drafting_session_id: str, issues: list[dict]) -> str:
    """
    Flag issues found during review for audit trail.

    Each issue should have: severity (minor/major/critical), description, recommendation.

    Args:
        drafting_session_id: The drafting session ID
        issues: List of issue dicts

    Returns:
        JSON confirmation
    """
    logger.info("[REVIEW] flag_review_issues: %d issues for session %s", len(issues), drafting_session_id)
    try:
        future = _executor.submit(_run_flag_issues_sync, drafting_session_id, issues)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[REVIEW] flag_review_issues error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


BACKEND_TOOLS = [get_draft_content, get_validation_results, finalize_and_deliver, flag_review_issues]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
