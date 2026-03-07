from __future__ import annotations

import re
import time
from typing import Any, Dict

from langgraph.types import Command

from ....config import logger
from ....database import qdrant_db
from ....utils.draftingAgent import get_active_qdrant_profile
from ..states import DraftingState
from ..tools import DraftingRAGTool
from ._utils import _as_dict


# Maximum classify queries to run against Qdrant — caps total latency.
_MAX_QUERIES = 4


def _parse_rag_chunks(raw_context: str, collection_name: str) -> list[Dict[str, Any]]:
    chunks: list[Dict[str, Any]] = []
    if not raw_context:
        return chunks

    sections = raw_context.split("[Document ")
    for idx, section in enumerate(sections[1:], start=1):
        section = "[Document " + section
        header, _, body = section.partition("]:")
        body = body.strip()
        if not body:
            continue

        score_match = re.search(r"score=([0-9.]+)", header)
        score = float(score_match.group(1)) if score_match else 0.0

        chunks.append({
            "chunk_id": f"rag-doc-{idx}",
            "text": body,
            "score": score,
            "source": {"collection": collection_name},
        })
    return chunks


def _is_empty_result(raw: str) -> bool:
    return not raw or raw.startswith("No relevant") or raw.startswith("Error:")


def _collection_exists(collection_name: str) -> bool:
    if not collection_name:
        return False
    try:
        client = qdrant_db.client
        if hasattr(client, "collection_exists"):
            return bool(client.collection_exists(collection_name=collection_name))
        client.get_collection(collection_name=collection_name)
        return True
    except Exception:
        return False


def _resolve_collection_name(classify: Dict[str, Any]) -> str:
    default_collection = get_active_qdrant_profile().collection_name
    rag_plan = _as_dict(classify.get("rag_plan"))
    collections = rag_plan.get("collections")
    candidate = ""
    if isinstance(collections, list) and collections:
        candidate = str(collections[0] or "").strip()

    if candidate and _collection_exists(candidate):
        return candidate

    if candidate and candidate != default_collection:
        logger.warning("[RAG] collection '%s' not found, falling back to '%s'", candidate, default_collection)
    return default_collection


async def rag_domain_node(state: DraftingState) -> Dict[str, Any]:
    """Fetch retrieval context from Qdrant for drafting.

    Runs exactly once per pipeline execution.
    Executes ALL queries from classify.rag_plan.queries (up to _MAX_QUERIES),
    merging and deduplicating results across queries so the LLM receives
    diverse, relevant chunks from each specific legal angle the classifier identified.
    """
    existing_rag = _as_dict(state.get("rag"))
    if existing_rag.get("chunks") or existing_rag.get("raw_context"):
        logger.info("[RAG] ↩ skipped — results already in state (%d chunks)", len(existing_rag.get("chunks") or []))
        return Command(update={}, goto="enrichment")

    logger.info("[RAG] ▶ start")
    t0 = time.perf_counter()

    classify = _as_dict(state.get("classify"))
    intake = _as_dict(state.get("intake"))
    rag_plan = _as_dict(classify.get("rag_plan"))
    collection_name = _resolve_collection_name(classify)

    doc_type = classify.get("doc_type", "general")
    law_domain = classify.get("law_domain", "Other")
    facts_summary = _as_dict(intake.get("facts")).get("summary", "")

    # Use ALL queries from classify output — classifier knows what legal angles to cover.
    requested_queries = rag_plan.get("queries") or []
    queries = [str(q).strip() for q in requested_queries if q and str(q).strip()]
    if not queries:
        queries = [
            f"{state.get('user_request', '')}\n"
            f"DocType: {doc_type}\nLawDomain: {law_domain}\nFacts: {facts_summary}"
        ]
    queries = queries[:_MAX_QUERIES]

    logger.info("[RAG] collection='%s' | running %d queries", collection_name, len(queries))

    # Run each classify query separately and merge, deduplicating by text content.
    seen_text_keys: set[str] = set()
    all_chunks: list[Dict[str, Any]] = []
    raw_parts: list[str] = []
    errors: list[str] = []

    for i, query_text in enumerate(queries, start=1):
        logger.info("[RAG] query %d/%d: %r", i, len(queries), query_text[:80])
        try:
            raw = await DraftingRAGTool(query=query_text, collection_name=collection_name)
            if _is_empty_result(raw):
                logger.info("[RAG] query %d returned no results", i)
                continue
            raw_parts.append(raw)
            for chunk in _parse_rag_chunks(raw, collection_name=collection_name):
                key = chunk["text"][:120]
                if key not in seen_text_keys:
                    seen_text_keys.add(key)
                    all_chunks.append(chunk)
        except Exception as exc:
            logger.warning("[RAG] query %d failed: %s", i, exc)
            errors.append(f"query_{i}: {exc}")

    raw_context = "\n\n".join(raw_parts)
    logger.info(
        "[RAG] ✓ done (%.1fs) | queries=%d | unique_chunks=%d",
        time.perf_counter() - t0, len(queries), len(all_chunks),
    )

    rag_payload = {
        "domain": law_domain,
        "queries": queries,
        "chunks": all_chunks,
        "authority_map": {},
        "rules": [],
        "errors": errors,
        "raw_context": raw_context,
    }
    return Command(update={"rag": rag_payload}, goto="enrichment")
