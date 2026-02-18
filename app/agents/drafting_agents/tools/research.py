"""
Backend tools for the Research Agent — Deep Search with web search, RAG, and citation validation.

Deep Search Strategy:
1. web_search_legal() — Brave API search for recent case law and legal information
2. rag_search_legal() — Qdrant vector DB search for indexed legal documents
3. save_research_citations() — Persist citations with confidence scores
4. run_citation_confidence_check() — Validate citations meet threshold
"""
import json
import uuid
import concurrent.futures
from html.parser import HTMLParser
from langchain.tools import tool
from ....config import logger, settings

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)


# ============================================
# DEEP SEARCH: WEB SEARCH (Brave API)
# ============================================

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return "".join(self.fed)


def _strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    return s.get_data()


def _run_web_search_sync(query: str, count: int = 5):
    """Search the web using Brave API for legal information."""
    import requests

    brave_api_key = getattr(settings, "BRAVE_API_KEY", None)
    if not brave_api_key:
        return {"status": "failed", "error": "Brave API key not configured", "results": []}

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "x-subscription-token": brave_api_key,
    }
    params = {"q": query, "count": count}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        results = response.json().get("web", {}).get("results", [])

        formatted = []
        for item in results:
            content = item.get("description", "")
            clean_content = _strip_html(content)
            formatted.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": clean_content,
                "date": item.get("published", ""),
            })

        return {"status": "success", "results": formatted, "count": len(formatted)}
    except Exception as e:
        return {"status": "failed", "error": str(e), "results": []}


@tool
def web_search_legal(query: str, count: int = 5) -> str:
    """
    Search the web for legal information using Brave API (Deep Search).

    Use this to find recent case law, statutory updates, legal analysis,
    and jurisdiction-specific legal information.

    Args:
        query: Legal search query (e.g., "California breach of contract statute of limitations")
        count: Number of results to return (default 5)

    Returns:
        JSON with search results (title, url, content, date)
    """
    logger.info("[RESEARCH] web_search_legal: %s", query)
    try:
        future = _executor.submit(_run_web_search_sync, query, count)
        result = future.result(timeout=20)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[RESEARCH] web_search_legal error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# DEEP SEARCH: RAG (Qdrant Vector DB)
# ============================================

def _run_rag_search_sync(query: str, collection_name: str = "legal_documents", top_k: int = 5):
    """Search Qdrant vector DB for relevant legal documents."""
    try:
        from qdrant_client import QdrantClient
        from openai import AzureOpenAI

        qdrant_url = getattr(settings, "QUADRANT_CLIENT_URL", None)
        qdrant_key = getattr(settings, "QUADRANT_API_KEY", None)

        if not qdrant_url:
            return {"status": "skipped", "message": "Qdrant not configured", "results": []}

        # Initialize clients
        qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_key)

        # Check if collection exists
        try:
            qdrant_client.get_collection(collection_name)
        except Exception:
            return {"status": "skipped", "message": f"Collection '{collection_name}' not found", "results": []}

        # Get embedding
        azure_api_key = getattr(settings, "azure_openai_api_key", None)
        azure_endpoint = getattr(settings, "azure_openai_endpoint", None)
        deployment = getattr(settings, "azure_openai_deployment_name_embedding", None)

        if not azure_api_key or not azure_endpoint:
            return {"status": "skipped", "message": "Azure OpenAI not configured for embeddings", "results": []}

        api_key_val = azure_api_key.get_secret_value() if hasattr(azure_api_key, "get_secret_value") else str(azure_api_key)
        endpoint_val = azure_endpoint.get_secret_value() if hasattr(azure_endpoint, "get_secret_value") else str(azure_endpoint)

        azure_client = AzureOpenAI(
            api_key=api_key_val,
            api_version="2024-02-01",
            azure_endpoint=endpoint_val,
        )

        response = azure_client.embeddings.create(input=[query], model=deployment)
        query_embedding = response.data[0].embedding

        # Search
        search_results = qdrant_client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=top_k,
        ).points

        formatted = []
        for point in search_results:
            payload = point.payload or {}
            formatted.append({
                "document": payload.get("document", ""),
                "source": payload.get("source", ""),
                "topic": payload.get("topic", ""),
                "score": point.score,
            })

        return {"status": "success", "results": formatted, "count": len(formatted)}

    except ImportError:
        return {"status": "skipped", "message": "qdrant_client not installed", "results": []}
    except Exception as e:
        return {"status": "failed", "error": str(e), "results": []}


@tool
def rag_search_legal(query: str, collection_name: str = "legal_documents", top_k: int = 5) -> str:
    """
    Search the legal knowledge base using RAG (Qdrant vector DB) for Deep Search.

    Use this to find relevant passages from indexed legal documents,
    case summaries, and legal reference materials.

    Args:
        query: Semantic search query (e.g., "breach of contract damages California")
        collection_name: Qdrant collection to search (default: "legal_documents")
        top_k: Number of results to return (default 5)

    Returns:
        JSON with matching documents and relevance scores
    """
    logger.info("[RESEARCH] rag_search_legal: %s (collection=%s)", query, collection_name)
    try:
        future = _executor.submit(_run_rag_search_sync, query, collection_name, top_k)
        result = future.result(timeout=20)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[RESEARCH] rag_search_legal error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# CITATION PERSISTENCE & VALIDATION
# ============================================

def _run_save_citations_sync(drafting_session_id: str, citations: list):
    """Save research citations to audit trail."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        repo.create(
            output_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            agent_name="research",
            output_type="citations",
            output_data=json.dumps(citations),
        )
        return {
            "status": "success",
            "citations_saved": len(citations),
            "message": f"Saved {len(citations)} citations.",
        }


@tool
def save_research_citations(drafting_session_id: str, citations: list[dict]) -> str:
    """
    Save legal citations generated by the research agent.

    Each citation should have: citation_text, citation_type (statute/case/regulation/secondary),
    confidence (0.0-1.0), relevance_description, source (web_search/rag/llm_knowledge).

    Args:
        drafting_session_id: The drafting session ID
        citations: List of citation dicts

    Returns:
        JSON with save results
    """
    logger.info("[RESEARCH] save_citations: %d citations for session %s", len(citations), drafting_session_id)
    try:
        future = _executor.submit(_run_save_citations_sync, drafting_session_id, citations)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[RESEARCH] save_citations error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_citation_confidence_sync(drafting_session_id: str):
    """Run citation confidence gate."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import (
        AgentOutputRepository, ValidationRepository,
    )
    from app.agents.drafting_agents.gates import check_citation_confidence

    with get_session() as session:
        output_repo = AgentOutputRepository(session=session)
        latest = output_repo.get_latest_by_type(drafting_session_id, "citations")

        citations = []
        if latest and latest.get("output_data"):
            citations = json.loads(latest["output_data"])

        gate_result = check_citation_confidence(citations)

        # Record gate result
        val_repo = ValidationRepository(session=session)
        val_repo.create(
            validation_id=str(uuid.uuid4()),
            session_id=drafting_session_id,
            gate_name="citation_confidence",
            passed=gate_result["passed"],
            details=json.dumps(gate_result["details"]),
        )

        return gate_result


@tool
def run_citation_confidence_check(drafting_session_id: str) -> str:
    """
    Run the citation confidence validation gate.

    Checks that all citations have confidence >= 0.75 or a source_doc_id.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with gate result
    """
    logger.info("[RESEARCH] run_citation_confidence_check for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_citation_confidence_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[RESEARCH] citation_confidence_check error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


def _run_get_citations_sync(drafting_session_id: str):
    """Get saved citations for a session."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.drafting import AgentOutputRepository

    with get_session() as session:
        repo = AgentOutputRepository(session=session)
        latest = repo.get_latest_by_type(drafting_session_id, "citations")
        if latest and latest.get("output_data"):
            citations = json.loads(latest["output_data"])
            return {"status": "success", "citations": citations, "count": len(citations)}
        return {"status": "success", "citations": [], "count": 0}


@tool
def get_research_citations(drafting_session_id: str) -> str:
    """
    Retrieve saved citations for a drafting session.

    Args:
        drafting_session_id: The drafting session ID

    Returns:
        JSON with list of citations
    """
    logger.info("[RESEARCH] get_citations for session %s", drafting_session_id)
    try:
        future = _executor.submit(_run_get_citations_sync, drafting_session_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[RESEARCH] get_citations error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"})


# ============================================
# EXPORTS
# ============================================

BACKEND_TOOLS = [
    web_search_legal,
    rag_search_legal,
    save_research_citations,
    run_citation_confidence_check,
    get_research_citations,
]
BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
