"""
Backend tools for the Intake Agent — fact gathering and persistence.
"""
import json
import uuid
import concurrent.futures
from langchain.tools import tool
from ....config import logger

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


def _run_save_facts_sync(drafting_session_id: str, facts: list, document_type: str = None):
    """Save gathered facts and optionally update document type."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        DraftingFactRepository, DraftingSessionRepository, AgentOutputRepository,
    )

    with get_session() as session:
        fact_repo = DraftingFactRepository(session=session)
        fact_records = []
        for f in facts:
            fact_records.append({
                "id": str(uuid.uuid4()),
                "fact_type": f.get("fact_type", "other"),
                "fact_key": f.get("fact_key", "unknown"),
                "fact_value": f.get("fact_value", ""),
                "confidence": f.get("confidence", 0.9),
                "source_message_idx": f.get("source_message_idx"),
            })

        count = fact_repo.bulk_create(fact_records, drafting_session_id)

        # Update document type if provided
        if document_type:
            session_repo = DraftingSessionRepository(session=session)
            session_repo.update_metadata(
                drafting_session_id, document_type=document_type,
            )

        # Save audit trail
        output_repo = AgentOutputRepository(session=session)
        output_repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="intake",
            output_type="facts",
            output_data=json.dumps(fact_records),
        )

        return {
            "status": "success",
            "facts_saved": count,
            "message": f"Saved {count} facts for drafting session.",
        }


@tool
def save_intake_facts(
    drafting_session_id: str,
    facts: list[dict],
    document_type: str = None,
) -> str:
    """
    Save facts gathered during intake to the database.

    Each fact should have: fact_type, fact_key, fact_value, confidence (optional).

    Args:
        drafting_session_id: The drafting session ID
        facts: List of fact dicts [{fact_type, fact_key, fact_value, confidence}]
        document_type: Optional document type to set/update

    Returns:
        JSON with save results
    """
    logger.info("[INTAKE] save_intake_facts: %d facts for session %s", len(facts), drafting_session_id)
    try:
        future = _executor.submit(_run_save_facts_sync, drafting_session_id, facts, document_type)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[INTAKE] save_intake_facts error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_fact_completeness_sync(drafting_session_id: str):
    """Run fact completeness gate."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        DraftingFactRepository, DraftingSessionRepository, ValidationRepository,
    )
    from app.agents.drafting_agents.gates import check_fact_completeness

    with get_session() as session:
        session_repo = DraftingSessionRepository(session=session)
        record = session_repo.get_by_id(drafting_session_id)
        if not record:
            return {"status": "failed", "message": "Session not found"}

        document_type = record.get("document_type", "other")

        fact_repo = DraftingFactRepository(session=session)
        facts = fact_repo.get_by_session(drafting_session_id)

        gate_result = check_fact_completeness(facts, document_type)

        # Record gate result
        val_repo = ValidationRepository(session=session)
        val_repo.create(
            validation_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            gate_name="fact_completeness",
            passed=gate_result["passed"],
            details=json.dumps(gate_result["details"]),
        )

        return gate_result


@tool
def run_fact_completeness_check(drafting_session_id: str) -> str:
    """
    Run the fact completeness validation gate.

    Checks that all required facts are present for the document type.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with gate result (passed/failed, missing facts)
    """
    logger.info("[INTAKE] run_fact_completeness_check for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_fact_completeness_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[INTAKE] fact_completeness_check error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


BACKEND_TOOLS = [save_intake_facts, run_fact_completeness_check]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
