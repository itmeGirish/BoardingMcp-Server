"""
Backend tools for the Citation Agent — verified citation retrieval only.

Tools:
1. get_research_bundle()         — fetch research output from AgentOutputRepository
2. get_classification()          — fetch classification from AgentOutputRepository
3. search_verified_citations()   — search VerifiedCitationRepository (text match, verified only)
4. save_citation_pack()          — persist citation pack to AgentOutputRepository
"""
import json
import uuid
import concurrent.futures
from langchain.tools import tool
from ....config import logger

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


# ============================================
# RETRIEVE RESEARCH BUNDLE
# ============================================

def _run_get_research_bundle_sync(drafting_session_id: str):
    """Fetch the latest research_bundle output for a session."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        latest = repo.get_latest_by_type(drafting_session_id, "research_bundle")
        if latest and latest.get("output_data"):
            return {
                "status": "success",
                "research_bundle": json.loads(latest["output_data"]),
            }
        return {"status": "success", "research_bundle": None, "message": "No research bundle found."}


@tool
def get_research_bundle(drafting_session_id: str) -> str:
    """
    Retrieve the research bundle produced by the Research Agent.

    Returns legal principles, statute framework, and argument structure
    that were identified during the research phase.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with the research bundle data
    """
    logger.info("[CITATION] get_research_bundle for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_research_bundle_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CITATION] get_research_bundle error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# RETRIEVE CLASSIFICATION
# ============================================

def _run_get_classification_sync(drafting_session_id: str):
    """Fetch the latest classification output for a session."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        latest = repo.get_latest_by_type(drafting_session_id, "classification")
        if latest and latest.get("output_data"):
            return {
                "status": "success",
                "classification": json.loads(latest["output_data"]),
            }
        return {"status": "success", "classification": None, "message": "No classification found."}


@tool
def get_classification(drafting_session_id: str) -> str:
    """
    Retrieve the document classification (doc_type, legal_domain, court_type, jurisdiction).

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with classification data
    """
    logger.info("[CITATION] get_classification for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_classification_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CITATION] get_classification error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# SEARCH VERIFIED CITATIONS
# ============================================

def _run_search_verified_citations_sync(drafting_session_id: str, search_terms: list):
    """Search VerifiedCitationRepository for citations matching search terms (verified only)."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import VerifiedCitationRepository
    from sqlmodel import select
    from app.database.postgresql.models.drafting import VerifiedCitation

    with get_session() as session:
        repo = VerifiedCitationRepository(session=session)

        # Get all verified citations (verified_at IS NOT NULL)
        statement = select(VerifiedCitation).where(
            VerifiedCitation.verified_at.isnot(None),
        )
        all_verified = session.exec(statement).all()

        # Basic text matching: keep citations whose citation_text contains any search term
        matched = []
        for record in all_verified:
            citation_lower = (record.citation_text or "").lower()
            case_lower = (record.case_name or "").lower()
            holding_lower = (record.holding or "").lower()
            searchable = f"{citation_lower} {case_lower} {holding_lower}"

            for term in search_terms:
                if term.lower() in searchable:
                    matched.append({
                        "id": record.id,
                        "citation_text": record.citation_text,
                        "case_name": record.case_name,
                        "year": record.year,
                        "court": record.court,
                        "holding": record.holding,
                        "verification_hash": record.citation_hash,
                        "source_db": record.source_db,
                        "source_url": record.source_url,
                        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
                        "verified": True,
                    })
                    break  # avoid duplicates per record

        return {"status": "success", "citations": matched, "count": len(matched)}


@tool
def search_verified_citations(drafting_session_id: str, search_terms: list[str]) -> str:
    """
    Search for verified legal citations matching the given search terms.

    Performs basic text matching against citation_text, case_name, and holding.
    Only returns citations with verified=True (verified_at is not null).

    Args:
        drafting_session_id: The drafting session ID
        search_terms: List of search terms derived from research output

    Returns:
        JSON list of verified citations matching the search terms
    """
    logger.info(
        "[CITATION] search_verified_citations for session %s with %d terms",
        drafting_session_id, len(search_terms),
    )
    try:
        future = _executor.submit(
            _run_search_verified_citations_sync, drafting_session_id, search_terms,
        )
        result = future.result(timeout=20)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CITATION] search_verified_citations error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# SAVE CITATION PACK
# ============================================

def _run_save_citation_pack_sync(drafting_session_id: str, citations: list):
    """Save citation pack to AgentOutputRepository."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="citation",
            output_type="citation_pack",
            output_data=json.dumps(citations),
        )
        return {
            "status": "success",
            "citations_saved": len(citations),
            "message": f"Citation pack saved with {len(citations)} verified citations.",
        }


@tool
def save_citation_pack(drafting_session_id: str, citations: list[dict]) -> str:
    """
    Save the verified citation pack for use by the Drafting Agent.

    Each citation should include: citation_text, verification_hash, source_type,
    relevance_score, applicable_to.

    Args:
        drafting_session_id: The drafting session ID
        citations: List of verified citation dicts

    Returns:
        JSON confirmation of save
    """
    logger.info(
        "[CITATION] save_citation_pack: %d citations for session %s",
        len(citations), drafting_session_id,
    )
    try:
        future = _executor.submit(_run_save_citation_pack_sync, drafting_session_id, citations)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[CITATION] save_citation_pack error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# EXPORTS
# ============================================

BACKEND_TOOLS = [
    get_research_bundle,
    get_classification,
    search_verified_citations,
    save_citation_pack,
]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
