"""
Backend tools for the Prayer/Relief Agent — prayer generation and persistence.
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
    """Fetch classification (doc_type, proceeding_type, court_type) from AgentOutputRepository."""
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

    Retrieves doc_type, proceeding_type, court_type, and other classification
    data needed to generate appropriate prayers and reliefs.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with classification data (doc_type, proceeding_type, court_type, etc.)
    """
    logger.info("[PRAYER] get_classification for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_classification_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[PRAYER] get_classification error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# TOOL 2: get_session_facts
# ============================================

def _run_get_session_facts_sync(drafting_session_id: str):
    """Fetch all facts (issues, claims, reliefs sought) for the drafting session."""
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

    Returns the complete set of facts including issues, claims,
    reliefs sought, and other case-specific data needed for prayer generation.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with list of facts and count
    """
    logger.info("[PRAYER] get_session_facts for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_session_facts_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[PRAYER] get_session_facts error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# TOOL 3: save_prayer_pack
# ============================================

def _run_save_prayer_pack_sync(drafting_session_id: str, prayer_data: dict):
    """Save prayer pack to AgentOutputRepository as output_type='prayer_pack'."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="prayer",
            output_type="prayer_pack",
            output_data=json.dumps(prayer_data, ensure_ascii=False),
        )
        return {
            "status": "success",
            "message": "Prayer pack saved successfully.",
            "prayer_keys": list(prayer_data.keys()),
        }


@tool
def save_prayer_pack(drafting_session_id: str, prayer_data: dict) -> str:
    """
    Save the generated prayer/relief pack for a drafting session.

    The prayer pack should include:
    - primary_relief: Main prayer text aligned with proceeding_type
    - alternative_relief: Alternative prayers if primary is not granted
    - interim_relief: Interim/urgent prayers (stay, interim bail, etc.)
    - costs_clause: Whether to include prayer for costs (bool or text)
    - any_other_relief: Standard 'any other relief' clause text
    - proceeding_type: The proceeding type these prayers are for
    - legal_provisions: Legal provisions supporting each prayer

    Args:
        drafting_session_id: The drafting session ID
        prayer_data: Dict containing the complete prayer structure

    Returns:
        JSON confirmation of save
    """
    logger.info("[PRAYER] save_prayer_pack for session %s", drafting_session_id)
    try:
        future = _executor.submit(
            _run_save_prayer_pack_sync, drafting_session_id, prayer_data,
        )
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[PRAYER] save_prayer_pack error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# EXPORTS
# ============================================

BACKEND_TOOLS = [get_classification, get_session_facts, save_prayer_pack]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
