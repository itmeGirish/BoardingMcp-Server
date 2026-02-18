"""
Backend tools for the Template Pack Agent — classification retrieval, mistake rules, and template persistence.
"""
import json
import uuid
import concurrent.futures
from langchain.tools import tool
from ....config import logger

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


# ============================================
# TOOL 1: GET CLASSIFICATION
# ============================================

def _run_get_classification_sync(drafting_session_id: str):
    """Fetch classification output from AgentOutputRepository."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        latest = repo.get_latest_by_type(drafting_session_id, "classification")

        if latest and latest.get("output_data"):
            classification = json.loads(latest["output_data"])
            return {
                "status": "success",
                "classification": classification,
            }
        return {
            "status": "not_found",
            "message": "No classification output found for this session.",
        }


@tool
def get_classification(drafting_session_id: str) -> str:
    """
    Retrieve the classification output for a drafting session.

    Fetches doc_type, court_type, jurisdiction, and proceeding_type
    from the most recent classification agent output.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with classification data (doc_type, court_type, jurisdiction, proceeding_type)
    """
    logger.info("[TEMPLATE_PACK] get_classification for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_classification_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[TEMPLATE_PACK] get_classification error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# TOOL 2: GET MISTAKE RULES
# ============================================

def _run_get_mistake_rules_sync(drafting_session_id: str):
    """Fetch applicable rules from MainRuleRepository based on session metadata."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        DraftingSessionRepository, MainRuleRepository,
    )

    with get_session() as session:
        # Get session metadata to determine document_type, jurisdiction, court_type
        session_repo = DraftingSessionRepository(session=session)
        record = session_repo.get_by_id(drafting_session_id)
        if not record:
            return {"status": "failed", "message": "Session not found", "rules": []}

        document_type = record.get("document_type")
        jurisdiction = record.get("jurisdiction")
        court_type = record.get("court_type")

        if not document_type:
            return {
                "status": "skipped",
                "message": "No document_type set on session. Cannot query rules.",
                "rules": [],
            }

        rule_repo = MainRuleRepository(session=session)
        rules = rule_repo.get_rules_for_document(
            document_type=document_type,
            jurisdiction=jurisdiction,
            court_type=court_type,
        )

        return {
            "status": "success",
            "rules": rules,
            "count": len(rules),
            "context": {
                "document_type": document_type,
                "jurisdiction": jurisdiction,
                "court_type": court_type,
            },
        }


@tool
def get_mistake_rules(drafting_session_id: str) -> str:
    """
    Retrieve applicable mistake rules/patterns for the current document type and jurisdiction.

    Queries the MainRuleRepository for promoted rules that match the session's
    document_type, jurisdiction, and court_type.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with list of applicable rules and their content
    """
    logger.info("[TEMPLATE_PACK] get_mistake_rules for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_mistake_rules_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[TEMPLATE_PACK] get_mistake_rules error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# TOOL 3: SAVE TEMPLATE PACK
# ============================================

def _run_save_template_pack_sync(drafting_session_id: str, template_data: dict):
    """Save template pack to AgentOutputRepository."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="template_pack",
            output_type="template_pack",
            output_data=json.dumps(template_data, ensure_ascii=False),
        )
        return {
            "status": "success",
            "message": "Template pack saved successfully.",
            "sections_count": len(template_data.get("required_sections", [])),
            "clauses_count": len(template_data.get("mandatory_clauses", [])),
        }


@tool
def save_template_pack(drafting_session_id: str, template_data: dict) -> str:
    """
    Save the generated template pack to the database.

    The template_data should contain:
    - doc_type: document type
    - court_type: court type
    - jurisdiction: state/jurisdiction
    - required_sections: list of mandatory sections
    - optional_sections: list of optional sections
    - mandatory_clauses: list of required legal clauses
    - formatting_rules: court-specific formatting rules
    - section_order: ordered list of section names

    Args:
        drafting_session_id: The drafting session ID
        template_data: Complete template pack dictionary

    Returns:
        JSON confirmation with counts
    """
    logger.info(
        "[TEMPLATE_PACK] save_template_pack for session %s (%d required sections, %d clauses)",
        drafting_session_id,
        len(template_data.get("required_sections", [])),
        len(template_data.get("mandatory_clauses", [])),
    )
    try:
        future = _executor.submit(_run_save_template_pack_sync, drafting_session_id, template_data)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[TEMPLATE_PACK] save_template_pack error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# EXPORTS
# ============================================

BACKEND_TOOLS = [get_classification, get_mistake_rules, save_template_pack]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
