"""
Backend tools for the Fact Extraction Agent — structuring and validation.
"""
import json
import uuid
import concurrent.futures
from langchain.tools import tool
from ....config import logger

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


def _run_get_facts_sync(drafting_session_id: str):
    """Get all facts for a session."""
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

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with list of facts
    """
    logger.info("[FACT_EXTRACTION] get_session_facts for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_facts_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[FACT_EXTRACTION] get_session_facts error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_structure_facts_sync(drafting_session_id: str, structured_facts: list):
    """Update facts with structured classification and confidence scores."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        DraftingFactRepository, AgentOutputRepository,
    )

    with get_session() as session:
        fact_repo = DraftingFactRepository(session=session)

        # Clear existing and re-insert with structured data
        updated_count = 0
        for f in structured_facts:
            fact_id = f.get("id")
            if fact_id:
                fact_repo.mark_verified(fact_id)
                updated_count += 1

        # Save audit trail
        output_repo = AgentOutputRepository(session=session)
        output_repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="fact_extraction",
            output_type="structured_facts",
            output_data=json.dumps(structured_facts),
        )

        return {
            "status": "success",
            "updated_count": updated_count,
            "message": f"Structured {updated_count} facts.",
        }


@tool
def structure_facts(drafting_session_id: str, structured_facts: list[dict]) -> str:
    """
    Save structured and classified facts after extraction.

    Each fact should include: id, fact_type, fact_key, fact_value, confidence.

    Args:
        drafting_session_id: The drafting session ID
        structured_facts: List of structured fact dicts

    Returns:
        JSON with update results
    """
    logger.info("[FACT_EXTRACTION] structure_facts: %d facts", len(structured_facts))
    try:
        future = _executor.submit(_run_structure_facts_sync, drafting_session_id, structured_facts)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[FACT_EXTRACTION] structure_facts error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_jurisdiction_check_sync(drafting_session_id: str):
    """Run jurisdiction validation gate."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        DraftingFactRepository, DraftingSessionRepository, ValidationRepository,
    )
    from app.agents.drafting_agents.gates import check_jurisdiction

    with get_session() as session:
        session_repo = DraftingSessionRepository(session=session)
        record = session_repo.get_by_id(drafting_session_id)
        if not record:
            return {"status": "failed", "message": "Session not found"}

        document_type = record.get("document_type", "other")

        fact_repo = DraftingFactRepository(session=session)
        facts = fact_repo.get_by_session(drafting_session_id)

        gate_result = check_jurisdiction(facts, document_type)

        # Record gate result
        val_repo = ValidationRepository(session=session)
        val_repo.create(
            validation_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            gate_name="jurisdiction",
            passed=gate_result["passed"],
            details=json.dumps(gate_result["details"]),
        )

        # Update session metadata with jurisdiction if found
        if gate_result["passed"]:
            fact_map = {f["fact_key"]: f["fact_value"] for f in facts}
            jurisdiction = fact_map.get("jurisdiction") or fact_map.get("state") or fact_map.get("governing_law")
            court_type = fact_map.get("court_name") or fact_map.get("court_type")
            if jurisdiction or court_type:
                session_repo.update_metadata(
                    drafting_session_id,
                    jurisdiction=jurisdiction,
                    court_type=court_type,
                )

        return gate_result


@tool
def run_jurisdiction_check(drafting_session_id: str) -> str:
    """
    Run the jurisdiction validation gate.

    Checks that jurisdiction/state/court information is present.
    If missing, the workflow must STOP and ask the user.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with gate result
    """
    logger.info("[FACT_EXTRACTION] run_jurisdiction_check for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_jurisdiction_check_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[FACT_EXTRACTION] jurisdiction_check error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_save_extraction_output_sync(drafting_session_id: str, output_data: str):
    """Save extraction output for audit trail."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="fact_extraction",
            output_type="extraction_report",
            output_data=output_data,
        )
        return {"status": "success", "message": "Extraction output saved."}


@tool
def save_extraction_output(drafting_session_id: str, output_data: str) -> str:
    """
    Save fact extraction results for audit trail.

    Args:
        drafting_session_id: The drafting session ID
        output_data: JSON string with extraction results

    Returns:
        JSON confirmation
    """
    logger.info("[FACT_EXTRACTION] save_extraction_output for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_save_extraction_output_sync, drafting_session_id, output_data)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[FACT_EXTRACTION] save_extraction_output error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


BACKEND_TOOLS = [get_session_facts, structure_facts, run_jurisdiction_check, save_extraction_output]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
