"""
Backend tools for the Legal Drafting Supervisor.

Session management + delegation tools to sub-agents.
"""
import json
import uuid
import concurrent.futures
from langchain.tools import tool
from ....config import logger

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


# ============================================
# SESSION MANAGEMENT
# ============================================

def _run_initialize_session_sync(user_id: str, document_type: str = None):
    """Create a new drafting session."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import DraftingSessionRepository

    with get_session() as session:
        repo = DraftingSessionRepository(session=session)
        session_id = str(uuid.uuid4())
        repo.create(
            session_id=session_id,
            user_id=user_id,
            document_type=document_type,
        )
        return {
            "status": "success",
            "drafting_session_id": session_id,
            "user_id": user_id,
            "document_type": document_type,
            "phase": "INITIALIZED",
            "message": "Drafting session created. Ready for intake.",
        }


@tool
def initialize_drafting_session(user_id: str, document_type: str = None) -> str:
    """
    Initialize a new legal drafting session.

    Creates a DraftingSession record in INITIALIZED phase.

    Args:
        user_id: User's unique identifier
        document_type: Optional document type (motion, brief, contract, etc.)

    Returns:
        JSON with drafting_session_id and status
    """
    logger.info("[DRAFTING] initialize_drafting_session for user: %s", user_id)
    try:
        future = _executor.submit(_run_initialize_session_sync, user_id, document_type)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DRAFTING] initialize_drafting_session error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_update_phase_sync(drafting_session_id: str, new_phase: str, error_message: str = None):
    """Update drafting phase."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import DraftingSessionRepository

    with get_session() as session:
        repo = DraftingSessionRepository(session=session)
        success = repo.update_phase(drafting_session_id, new_phase, error_message)
        if success:
            record = repo.get_by_id(drafting_session_id)
            return {
                "status": "success",
                "phase": new_phase,
                "previous_phase": record.get("previous_phase") if record else None,
                "message": f"Phase updated to {new_phase}",
            }
        return {
            "status": "failed",
            "message": f"Invalid transition to {new_phase}",
        }


@tool
def update_drafting_phase(drafting_session_id: str, new_phase: str, error_message: str = None) -> str:
    """
    Update the drafting workflow phase (state transition).

    Validates the transition against allowed state machine transitions.

    Args:
        drafting_session_id: The drafting session ID
        new_phase: Target phase (INITIALIZED, INTAKE, FACT_EXTRACTION, RESEARCH, DRAFTING, REVIEW, REVISION, COMPLETED, FAILED)
        error_message: Optional error message (for FAILED transitions)

    Returns:
        JSON with transition result
    """
    logger.info("[DRAFTING] update_phase: %s -> %s", drafting_session_id, new_phase)
    try:
        future = _executor.submit(_run_update_phase_sync, drafting_session_id, new_phase, error_message)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DRAFTING] update_phase error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_get_status_sync(drafting_session_id: str):
    """Get current session status."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import DraftingSessionRepository

    with get_session() as session:
        repo = DraftingSessionRepository(session=session)
        record = repo.get_by_id(drafting_session_id)
        if record:
            return {"status": "success", "session": record}
        return {"status": "failed", "message": "Session not found"}


@tool
def get_drafting_status(drafting_session_id: str) -> str:
    """
    Get the current status and details of a drafting session.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with full session details
    """
    logger.info("[DRAFTING] get_status: %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_status_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DRAFTING] get_status error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# SUB-AGENT DELEGATION TOOLS
# ============================================

@tool
def start_drafting_pipeline(user_id: str, drafting_session_id: str) -> str:
    """
    Start the full 18-step drafting pipeline.

    Call this when the user has provided enough information to begin drafting.
    This triggers the deterministic pipeline: security → intake → classification →
    template → parallel agents → drafting → review → export.

    Args:
        user_id: User's unique identifier
        drafting_session_id: The drafting session ID

    Returns:
        JSON confirming pipeline start
    """
    logger.info("[DRAFTING] Starting 18-step pipeline for session: %s", drafting_session_id)
    return json.dumps({
        "status": "delegated",
        "agent": "security_gate",
        "user_id": user_id,
        "drafting_session_id": drafting_session_id,
        "message": "Starting the 18-step legal drafting pipeline.",
    })


@tool
def delegate_to_intake(user_id: str, drafting_session_id: str, document_type: str = None) -> str:
    """
    Delegate to the Intake Agent for conversational fact gathering.

    Args:
        user_id: User's unique identifier
        drafting_session_id: The drafting session ID
        document_type: Optional document type hint

    Returns:
        JSON confirming delegation
    """
    logger.info("[DRAFTING] Delegating to Intake Agent for session: %s", drafting_session_id)
    return json.dumps({
        "status": "delegated",
        "agent": "intake",
        "user_id": user_id,
        "drafting_session_id": drafting_session_id,
        "document_type": document_type,
        "message": "Handing off to Intake Agent for fact gathering.",
    })


# ============================================
# EXPORTS
# ============================================

BACKEND_TOOLS = [
    initialize_drafting_session,
    update_drafting_phase,
    get_drafting_status,
    start_drafting_pipeline,
    delegate_to_intake,
]

BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}

DELEGATION_TOOL_MAP = {
    "start_drafting_pipeline": "security_gate",
    "delegate_to_intake": "intake",
}
