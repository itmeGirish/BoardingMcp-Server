"""
Backend tools for the Compliance Agent — limitation periods, annexures, and statutory compliance.
"""
import json
import uuid
import concurrent.futures
from langchain.tools import tool
from ....config import logger

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


# ============================================
# TOOL 1: get_classification
# ============================================

def _run_get_classification_sync(drafting_session_id: str):
    """Fetch classification (doc_type, court_type, jurisdiction) from AgentOutputRepository."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        latest = repo.get_latest_by_type(drafting_session_id, "classification")
        if latest and latest.get("output_data"):
            classification = json.loads(latest["output_data"])
            return {"status": "success", "classification": classification}
        return {"status": "success", "classification": {}, "message": "No classification found."}


@tool
def get_classification(drafting_session_id: str) -> str:
    """
    Fetch the document classification for a drafting session.

    Retrieves doc_type, court_type, jurisdiction, and other classification
    data produced by the earlier classification step.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with classification data (doc_type, court_type, jurisdiction, etc.)
    """
    logger.info("[COMPLIANCE] get_classification for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_classification_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[COMPLIANCE] get_classification error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# TOOL 2: get_session_facts
# ============================================

def _run_get_session_facts_sync(drafting_session_id: str):
    """Fetch all facts for the drafting session."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import DraftingFactRepository

    with get_session() as session:
        repo = DraftingFactRepository(session=session)
        facts = repo.get_by_session(drafting_session_id)
        return {"status": "success", "facts": facts, "count": len(facts)}


@tool
def get_session_facts(drafting_session_id: str) -> str:
    """
    Retrieve all facts gathered for a drafting session.

    Returns the complete set of facts including party names, dates,
    claims, jurisdiction info, and other case-specific data.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with list of facts and count
    """
    logger.info("[COMPLIANCE] get_session_facts for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_session_facts_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[COMPLIANCE] get_session_facts error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# TOOL 3: save_compliance_report
# ============================================

def _run_save_compliance_report_sync(drafting_session_id: str, report_data: dict):
    """Save compliance report to AgentOutputRepository as output_type='compliance_report'."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="compliance",
            output_type="compliance_report",
            output_data=json.dumps(report_data, ensure_ascii=False),
        )
        return {
            "status": "success",
            "message": "Compliance report saved successfully.",
            "report_keys": list(report_data.keys()),
        }


@tool
def save_compliance_report(drafting_session_id: str, report_data: dict) -> str:
    """
    Save the compliance validation report for a drafting session.

    The report should include:
    - limitation_check: {expired: bool, days_remaining: int, needs_clarification: bool}
    - mandatory_annexures: list of required annexures for the doc_type
    - affidavit_required: bool
    - mandatory_sections: list of sections that must appear in the document
    - risk_areas: list of flagged risks (approaching limitation, missing annexures, etc.)
    - overall_status: "compliant" | "non_compliant" | "needs_clarification"

    Args:
        drafting_session_id: The drafting session ID
        report_data: Dict containing the full compliance report

    Returns:
        JSON confirmation of save
    """
    logger.info("[COMPLIANCE] save_compliance_report for session %s", drafting_session_id)
    try:
        future = _executor.submit(
            _run_save_compliance_report_sync, drafting_session_id, report_data,
        )
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[COMPLIANCE] save_compliance_report error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# EXPORTS
# ============================================

BACKEND_TOOLS = [get_classification, get_session_facts, save_compliance_report]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
