"""
Backend tools for the LLM Classifier Agent — fact retrieval and classification persistence.
"""
import json
import uuid
import concurrent.futures
from langchain.tools import tool
from ....config import logger

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


def _run_get_session_facts_sync(drafting_session_id: str):
    """Fetch all facts from DraftingFactRepository for this session."""
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

    Fetches every fact record from the database for the given session
    so the classifier can analyze them before producing a classification.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with list of facts
    """
    logger.info("[LLM_CLASSIFIER] get_session_facts for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_session_facts_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[LLM_CLASSIFIER] get_session_facts error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_save_classification_sync(drafting_session_id: str, classification_data: dict):
    """Save classification to AgentOutputRepository and update DraftingSession metadata."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        AgentOutputRepository, DraftingSessionRepository,
    )

    with get_session() as session:
        # Save classification as agent output (audit trail)
        output_repo = AgentOutputRepository(session=session)
        output_repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="llm_classifier",
            output_type="classification",
            output_data=json.dumps(classification_data, ensure_ascii=False),
        )

        # Update DraftingSession metadata from classification
        session_repo = DraftingSessionRepository(session=session)
        update_kwargs = {}

        doc_type = classification_data.get("doc_type")
        if doc_type:
            update_kwargs["document_type"] = doc_type

        court_type = classification_data.get("court_type")
        if court_type:
            update_kwargs["court_type"] = court_type

        jurisdiction_state = classification_data.get("jurisdiction_state")
        if jurisdiction_state and jurisdiction_state != "unspecified":
            update_kwargs["jurisdiction"] = jurisdiction_state

        legal_domain = classification_data.get("legal_domain")
        if legal_domain:
            update_kwargs["case_category"] = legal_domain

        if update_kwargs:
            session_repo.update_metadata(drafting_session_id, **update_kwargs)

        return {
            "status": "success",
            "message": f"Classification saved for session {drafting_session_id}.",
            "doc_type": doc_type,
            "confidence_score": classification_data.get("confidence_score"),
        }


@tool
def save_classification(drafting_session_id: str, classification_data: dict) -> str:
    """
    Save the document classification to the database.

    Persists the classification as an agent output (output_type="classification")
    and updates the DraftingSession metadata with document_type, court_type,
    jurisdiction, and case_category extracted from the classification.

    Args:
        drafting_session_id: The drafting session ID
        classification_data: Dict with keys: legal_domain, proceeding_type, doc_type,
            court_type, draft_goal, jurisdiction_state, jurisdiction_city, language,
            draft_style, confidence_score, reasoning

    Returns:
        JSON with save confirmation
    """
    logger.info(
        "[LLM_CLASSIFIER] save_classification for session %s — doc_type=%s",
        drafting_session_id,
        classification_data.get("doc_type", "unknown"),
    )
    try:
        future = _executor.submit(
            _run_save_classification_sync, drafting_session_id, classification_data,
        )
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[LLM_CLASSIFIER] save_classification error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


BACKEND_TOOLS = [get_session_facts, save_classification]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
