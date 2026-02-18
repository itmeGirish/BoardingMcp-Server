"""
Backend tools for the Localization Agent — court-specific and state-specific formatting rules.
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
    """Fetch classification (doc_type, court_type, jurisdiction, state) from AgentOutputRepository."""
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

    Retrieves jurisdiction, court_type, state, and other classification
    data needed to determine court-specific formatting rules.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with classification data (jurisdiction, court_type, state, etc.)
    """
    logger.info("[LOCALIZATION] get_classification for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_classification_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[LOCALIZATION] get_classification error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# TOOL 2: save_local_rules
# ============================================

def _run_save_local_rules_sync(drafting_session_id: str, rules_data: dict):
    """Save localization rules to AgentOutputRepository as output_type='local_rules'."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="localization",
            output_type="local_rules",
            output_data=json.dumps(rules_data, ensure_ascii=False),
        )
        return {
            "status": "success",
            "message": "Local formatting rules saved successfully.",
            "rules_keys": list(rules_data.keys()),
        }


@tool
def save_local_rules(drafting_session_id: str, rules_data: dict) -> str:
    """
    Save court-specific and state-specific formatting rules for a drafting session.

    The rules should include:
    - heading_format: Court heading template string
    - cause_title_format: How parties are listed in the cause title
    - case_numbering_style: Style for case numbering
    - verification_clause_format: State-specific oath/verification format
    - annexure_style: Marking scheme (Annexure-A, P-1, Exhibit-1, etc.)
    - date_format: Date formatting convention for the jurisdiction
    - language_rules: Primary language, bilingual requirements
    - numbering_style: Roman numerals vs Arabic for sections
    - hard_block: True if state/city info is missing (cannot proceed)

    Args:
        drafting_session_id: The drafting session ID
        rules_data: Dict containing the formatting rules

    Returns:
        JSON confirmation of save
    """
    logger.info("[LOCALIZATION] save_local_rules for session %s", drafting_session_id)
    try:
        future = _executor.submit(
            _run_save_local_rules_sync, drafting_session_id, rules_data,
        )
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[LOCALIZATION] save_local_rules error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# EXPORTS
# ============================================

BACKEND_TOOLS = [get_classification, save_local_rules]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
