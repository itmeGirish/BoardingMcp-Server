from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from typing import Any, Optional

from qdrant_client.models import FieldCondition, Filter, MatchValue

try:
    from ...config import logger
except ImportError:  # pragma: no cover - fallback for direct execution contexts
    from app.config import logger


@dataclass(frozen=True)
class DraftingQdrantProfile:
    """Infrastructure-only configuration — no legal domain knowledge."""

    name: str
    collection_name: str

    top_k: int = 8
    fetch_k: int = 48
    score_threshold: float = 0.12
    hnsw_ef: int = 128
    min_doc_length: int = 60

    # Payload field names — configurable per collection schema.
    act_name_field: str = "act_name"
    source_type_field: str = "source_type"
    section_field: str = "section"
    order_field: str = "order"
    rule_field: str = "rule"
    anchor_field: str = "anchor"

    content_fields: tuple[str, ...] = ("document", "text")
    book_fields: tuple[str, ...] = ("book", "book_title", "source")
    page_start_fields: tuple[str, ...] = ("page_start", "page_number")
    page_end_fields: tuple[str, ...] = ("page_end", "page_number")


@dataclass(frozen=True)
class RetrievalIntent:
    """Structural hints extracted from the query — no domain-specific mappings."""

    section: Optional[str]
    order: Optional[int]
    rule: Optional[int]
    legal_terms: tuple[str, ...]


# Profile registry — collection config only, no legal term mappings.
CIVIL_PROFILE = DraftingQdrantProfile(
    name="civil",
    collection_name="civil",
)

PROFILE_REGISTRY: dict[str, DraftingQdrantProfile] = {
    "civil": CIVIL_PROFILE,
}


def register_qdrant_profile(profile: DraftingQdrantProfile) -> None:
    """Register or replace a drafting Qdrant retrieval profile."""
    PROFILE_REGISTRY[profile.name.lower()] = profile


def get_active_qdrant_profile() -> DraftingQdrantProfile:
    """
    Resolve active RAG collection/profile from env:
    - DRAFTING_RAG_PROFILE: logical profile name (default: civil)
    - DRAFTING_RAG_COLLECTION: explicit collection override
    """
    profile_name = os.getenv("DRAFTING_RAG_PROFILE", "civil").strip().lower()
    collection_override = os.getenv("DRAFTING_RAG_COLLECTION", "").strip()

    profile = PROFILE_REGISTRY.get(profile_name)
    if profile is None:
        inferred_collection = collection_override or profile_name or "civil"
        profile = replace(
            CIVIL_PROFILE,
            name=profile_name or inferred_collection,
            collection_name=inferred_collection,
        )

    if collection_override:
        profile = replace(profile, collection_name=collection_override)
    return profile


# ---------------------------------------------------------------------------
# Structural query parsers — generic parsing, no legal domain knowledge.
# ---------------------------------------------------------------------------

def _roman_to_int(text: str) -> Optional[int]:
    if not text:
        return None
    value = text.upper()
    if value.isdigit():
        return int(value)

    roman = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(value):
        if ch not in roman:
            return None
        current = roman[ch]
        if current < prev:
            total -= current
        else:
            total += current
            prev = current
    return total if total > 0 else None


def _extract_section(query: str) -> Optional[str]:
    match = re.search(r"\bsection\s+(\d+[a-z]?)\b", query, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper()


def _extract_order_rule(query: str) -> tuple[Optional[int], Optional[int]]:
    full_match = re.search(
        r"\border\s+([ivxlcdm]+|\d+)\s+rule\s+(\d+)\b",
        query,
        flags=re.IGNORECASE,
    )
    if full_match:
        return _roman_to_int(full_match.group(1)), int(full_match.group(2))

    order_match = re.search(r"\border\s+([ivxlcdm]+|\d+)\b", query, flags=re.IGNORECASE)
    rule_match = re.search(r"\brule\s+(\d+)\b", query, flags=re.IGNORECASE)
    order = _roman_to_int(order_match.group(1)) if order_match else None
    rule = int(rule_match.group(1)) if rule_match else None
    return order, rule


def _extract_legal_terms(query: str) -> tuple[str, ...]:
    stopwords = {
        # common English function words
        "the", "and", "for", "with", "from", "what", "when", "where", "which", "that",
        "this", "your", "draft", "drafting", "under", "into", "about", "have", "will",
        "would", "should", "could", "are", "is", "was", "were", "how", "why", "can",
        "not", "but", "all", "any", "its", "has", "had", "been", "may", "also", "such",
        "than", "then", "only", "both", "each", "more", "must", "some", "upon",
        "our", "their", "these", "those", "very", "just", "even", "other", "same",
        "per", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "first", "second", "third", "now", "here", "there", "else", "yet",
        "day", "days", "year", "years", "month", "months", "time", "date", "period",
        "shall", "does", "did", "being", "make", "made", "give", "given", "take",
        "taken", "apply", "applied", "include", "included", "means", "mean",
        # legal boilerplate (appear in virtually every legal document — high freq, low signal)
        "court", "case", "said", "suit", "act", "law", "code", "rule", "aforesaid",
        "therein", "thereof", "herein", "hereof", "wherein", "hereby", "thereby",
        "whereas", "above", "below", "plaintiff", "defendant", "petitioner", "respondent",
        "section", "order", "article", "clause", "sub", "provision", "proviso",
        "matter", "filing", "filed", "document", "documents", "application",
        "judgment", "decree", "appeal", "revision", "petition", "suit",
        "person", "persons", "party", "parties", "property", "right", "rights",
        "court", "high", "district", "civil", "criminal", "tribunal",
        "amount", "payment", "paid", "pay", "due", "demand", "claim", "claims",
    }
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_]+", query.lower())
    terms = [token for token in tokens if len(token) > 2 and token not in stopwords]
    return tuple(sorted(set(terms)))


def _infer_retrieval_intent(query: str) -> RetrievalIntent:
    """Extract structural hints from query text — section, order, rule numbers only."""
    section = _extract_section(query)
    order, rule = _extract_order_rule(query)
    legal_terms = _extract_legal_terms(query)
    return RetrievalIntent(section=section, order=order, rule=rule, legal_terms=legal_terms)


# ---------------------------------------------------------------------------
# Qdrant filter builder — structural filters only (section/order/rule).
# ---------------------------------------------------------------------------

def _build_structural_filter(
    *,
    intent: RetrievalIntent,
    profile: DraftingQdrantProfile,
) -> Optional[Filter]:
    """Build a metadata filter from structural query hints (section, order, rule)."""
    must_conditions = []

    if intent.section:
        must_conditions.append(
            FieldCondition(key=profile.section_field, match=MatchValue(value=intent.section))
        )
    if intent.order is not None:
        must_conditions.append(
            FieldCondition(key=profile.order_field, match=MatchValue(value=intent.order))
        )
    if intent.rule is not None:
        must_conditions.append(
            FieldCondition(key=profile.rule_field, match=MatchValue(value=intent.rule))
        )

    if not must_conditions:
        return None
    return Filter(must=must_conditions)


# ---------------------------------------------------------------------------
# Scoring and selection utilities.
# ---------------------------------------------------------------------------

def _payload_get(payload: dict[str, Any], keys: tuple[str, ...], default: Any = "") -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return default


def _page_label(page_start: Optional[int], page_end: Optional[int]) -> str:
    if page_start is None and page_end is None:
        return ""
    if page_end is None:
        return f"p.{page_start}"
    if page_start is None:
        return f"p.{page_end}"
    if page_start == page_end:
        return f"p.{page_start}"
    return f"p.{page_start}-{page_end}"


def _format_document_header(
    point: Any,
    index: int,
    profile: DraftingQdrantProfile,
) -> str:
    payload = point.payload or {}

    act_name = payload.get(profile.act_name_field, "")
    anchor = payload.get(profile.anchor_field, "")
    source_type = payload.get(profile.source_type_field, "")
    section = payload.get(profile.section_field)
    order = payload.get(profile.order_field)
    rule = payload.get(profile.rule_field)
    book = _payload_get(payload, profile.book_fields)
    page_start = _payload_get(payload, profile.page_start_fields, None)
    page_end = _payload_get(payload, profile.page_end_fields, None)
    score = getattr(point, "score", None)

    parts = []
    if act_name:
        parts.append(str(act_name))
    if anchor:
        parts.append(str(anchor))
    if source_type:
        parts.append(str(source_type))
    if book:
        parts.append(str(book))
    if section:
        parts.append(f"Section {section}")
    elif order is not None and rule is not None:
        parts.append(f"Order {order} Rule {rule}")
    elif order is not None:
        parts.append(f"Order {order}")
    elif rule is not None:
        parts.append(f"Rule {rule}")

    page = _page_label(page_start, page_end)
    if page:
        parts.append(page)
    if score is not None:
        parts.append(f"score={float(score):.3f}")

    meta = " | ".join(parts) if parts else "Unknown"
    return f"[Document {index} | {meta}]"


def _filter_signature(query_filter: Optional[Filter]) -> str:
    if query_filter is None:
        return "NONE"
    if hasattr(query_filter, "model_dump_json"):
        return query_filter.model_dump_json(exclude_none=True)
    return str(query_filter)


def _dedupe_filters(filters: list[Optional[Filter]]) -> list[Optional[Filter]]:
    seen = set()
    deduped = []
    for query_filter in filters:
        sig = _filter_signature(query_filter)
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(query_filter)
    return deduped


def _structural_match_bonus(
    payload: dict[str, Any],
    intent: RetrievalIntent,
    profile: DraftingQdrantProfile,
) -> float:
    """Score bonus for structural matches (section, order, rule) — no domain hardcoding."""
    checks = 0
    hits = 0

    if intent.section:
        checks += 1
        if str(payload.get(profile.section_field, "")).upper() == intent.section:
            hits += 1

    if intent.order is not None:
        checks += 1
        if payload.get(profile.order_field) == intent.order:
            hits += 1

    if intent.rule is not None:
        checks += 1
        if payload.get(profile.rule_field) == intent.rule:
            hits += 1

    if checks == 0:
        return 0.0
    return hits / checks


def _keyword_overlap_score(query_terms: tuple[str, ...], text: str) -> float:
    if not query_terms or not text:
        return 0.0
    doc_terms = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_]+", text.lower()))
    if not doc_terms:
        return 0.0
    overlap = len(set(query_terms) & doc_terms)
    return overlap / max(len(set(query_terms)), 1)


def _point_identity(point: Any) -> Any:
    payload = getattr(point, "payload", None) or {}
    chunk_id = payload.get("chunk_id")
    if chunk_id not in (None, ""):
        return chunk_id
    direct_id = getattr(point, "id", None)
    if direct_id not in (None, ""):
        return direct_id
    return id(point)


def _rerank_points(
    *,
    points: list[Any],
    intent: RetrievalIntent,
    profile: DraftingQdrantProfile,
) -> list[Any]:
    scored = []
    for point in points:
        payload = point.payload or {}
        text = _payload_get(payload, profile.content_fields, "")
        vector_score = float(getattr(point, "score", 0.0) or 0.0)
        keyword_score = _keyword_overlap_score(intent.legal_terms, text)
        structural_bonus = _structural_match_bonus(payload, intent, profile)
        combined = (0.60 * vector_score) + (0.25 * keyword_score) + (0.15 * structural_bonus)
        scored.append((combined, point))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [point for _, point in scored]


def _select_top_points(
    *,
    points: list[Any],
    profile: DraftingQdrantProfile,
) -> list[Any]:
    """Select top-k points by score order — no hardcoded source_type preference."""
    selected = []
    used_ids: set[Any] = set()
    for point in points:
        marker = _point_identity(point)
        if marker in used_ids:
            continue
        used_ids.add(marker)
        selected.append(point)
        if len(selected) >= profile.top_k:
            break
    return selected


# ---------------------------------------------------------------------------
# Main retrieval entry point.
# ---------------------------------------------------------------------------

async def retrieve_drafting_context(
    *,
    query: str,
    qdrant_db: Any,
    profile: DraftingQdrantProfile,
) -> str:
    query = (query or "").strip()
    if not query:
        return "No relevant documents found for the given query."

    query_embedding = (await qdrant_db.aget_embeddings_batch([query]))[0]
    intent = _infer_retrieval_intent(query)

    # Structural filter (section/order/rule from query) → fallback to semantic only.
    structural_filter = _build_structural_filter(intent=intent, profile=profile)
    filters_to_try = _dedupe_filters([structural_filter, None])

    search_results = []
    for idx, query_filter in enumerate(filters_to_try, start=1):
        label = "structural filter" if query_filter is not None else "semantic-only"
        logger.info(
            "DraftingRAGTool: attempt %s (%s) on '%s'.",
            idx, label, profile.collection_name,
        )
        search_results = await qdrant_db.aquery_by_embedding(
            collection_name=profile.collection_name,
            query_embedding=query_embedding,
            top_k=profile.fetch_k,
            hnsw_ef=profile.hnsw_ef,
            query_filter=query_filter,
            score_threshold=profile.score_threshold,
        )
        if search_results:
            break

    if not search_results:
        logger.warning(
            "DraftingRAGTool: no relevant points found in '%s' for query: %s",
            profile.collection_name,
            query[:80],
        )
        return "No relevant documents found for the given query."

    ranked = _rerank_points(points=search_results, intent=intent, profile=profile)
    ranked = qdrant_db.post_filter(ranked, min_doc_length=profile.min_doc_length)
    ranked = _select_top_points(points=ranked, profile=profile)

    if not ranked:
        logger.warning("DraftingRAGTool: all candidates removed by post_filter.")
        return "No relevant documents found for the given query."

    top_payload = ranked[0].payload or {}
    top_act = top_payload.get(profile.act_name_field, "")
    top_anchor = top_payload.get(profile.anchor_field, "")
    recommendation = ""
    if top_act or top_anchor:
        recommendation = f"[TOP_MATCH: {top_act} | {top_anchor}]"

    documents = []
    for i, point in enumerate(ranked, start=1):
        payload = point.payload or {}
        content = _payload_get(payload, profile.content_fields).strip()
        if not content:
            continue
        header = _format_document_header(point, i, profile)
        documents.append(f"{header}:\n{content}")

    if not documents:
        logger.warning("DraftingRAGTool: retrieved points had empty document/text payloads.")
        return "No relevant documents found for the given query."

    logger.info(
        "DraftingRAGTool returned %s documents from '%s' (profile=%s).",
        len(documents),
        profile.collection_name,
        profile.name,
    )
    if recommendation:
        return recommendation + "\n\n" + "\n\n".join(documents)
    return "\n\n".join(documents)
