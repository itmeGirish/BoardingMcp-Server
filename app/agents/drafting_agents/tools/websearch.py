"""
Court Fee Web Search Tool — fetches current court fee rates using Brave Search.

Court fees are jurisdiction-specific and change with government orders/amendments.
This tool fetches fresh information at draft time rather than relying on static RAG.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

import requests

try:
    from ....config import logger, settings
except ImportError:  # pragma: no cover - direct execution
    from app.config import logger, settings


_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_REQUEST_TIMEOUT = 12
_RESULT_COUNT = 5

# Keywords that indicate a snippet contains fee rate information.
_FEE_SIGNAL_WORDS = (
    "%", "per cent", "percent", "ad valorem", "per rupee",
    "schedule", "fee payable", "court fee", "stamp fee",
)

# Keywords that indicate a snippet contains actionable legal doctrine.
_LEGAL_SIGNAL_WORDS = (
    "limitation", "years", "accrues", "accrual", "right to sue",
    "mandatory", "rule", "order", "section", "article", "prescribed",
    "particulars", "cause of action", "procedure",
)


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []

    def handle_data(self, d: str) -> None:
        self._parts.append(d)

    def get_data(self) -> str:
        return " ".join(self._parts)


def _strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    text = s.get_data()
    # Replace Unicode replacement char, non-breaking spaces, zero-width chars
    text = (
        text.replace("\ufffd", " ")
            .replace("\u00a0", " ")
            .replace("\u200b", "")
            .replace("\u200c", "")
    )
    return re.sub(r"\s+", " ", text).strip()


def _build_court_fee_queries(
    *,
    state: str,
    court_type: str,
    doc_type: str,
    suit_value: Optional[float],
) -> List[str]:
    """Build two complementary queries for court fee rates.

    Query 1 — rate formula focus: targets calculator/FAQ pages that show the
    ad valorem percentage rather than garbled schedule table headers.

    Query 2 — act/schedule focus: targets the state court fees act schedule
    directly, useful when Q1 returns blog posts without the exact rate.
    """
    doc_label = doc_type.replace("_", " ")
    lakhs_str = f"Rs {suit_value / 100_000:.0f} lakh" if suit_value else ""

    # Q1: ad valorem percentage rate — surfaces fee calculators and FAQs.
    q1_parts = [state, "court fee ad valorem percentage", doc_label, "civil suit"]
    if court_type:
        q1_parts.insert(2, court_type)
    if lakhs_str:
        q1_parts.append(lakhs_str)

    # Q2: act/schedule — surfaces the actual fee schedule or government page.
    q2_parts = [state, "court fees act schedule", doc_label, "plaint valuation rate"]
    if lakhs_str:
        q2_parts.append(lakhs_str)

    return [" ".join(q1_parts), " ".join(q2_parts)]


def _is_fee_relevant(snippet: str) -> bool:
    """Return True if the snippet contains actual fee rate information."""
    low = snippet.lower()
    return any(signal in low for signal in _FEE_SIGNAL_WORDS)


def _fetch_one(api_key: str, query: str) -> List[Dict[str, Any]]:
    """Run a single Brave search and return raw result items."""
    response = requests.get(
        _BRAVE_SEARCH_URL,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "x-subscription-token": api_key,
        },
        params={"q": query, "count": _RESULT_COUNT},
        timeout=_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("web", {}).get("results", [])


async def CourtFeeWebSearchTool(
    *,
    state: str,
    court_type: str = "",
    doc_type: str = "",
    suit_value: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Fetch current court fee rates via Brave Search for the given jurisdiction.

    Runs two complementary queries and merges results:
    - Q1: ad valorem percentage rate (targets calculators/FAQs with the formula)
    - Q2: act/schedule (targets the fee schedule or government page directly)

    Deduplicates by URL and filters to snippets that contain actual fee signals
    (%, per cent, ad valorem, schedule, etc.) so the draft model gets clean context.

    Returns dict with keys:
        query:    str  — primary query used
        results:  list — deduplicated results [{title, url, snippet, date}]
        summary:  str  — fee-relevant snippets only, formatted for prompt injection
        error:    str|None
    """
    api_key = (settings.BRAVE_API_KEY or "").strip()
    if not api_key:
        logger.warning("[CourtFee] BRAVE_API_KEY not set — skipping web search")
        return {"query": "", "results": [], "summary": "", "error": "BRAVE_API_KEY not configured"}

    queries = _build_court_fee_queries(
        state=state, court_type=court_type, doc_type=doc_type, suit_value=suit_value
    )
    primary_query = queries[0]
    logger.info("[CourtFee] queries: %s", queries)

    # Run both queries; second is best-effort (failure is non-fatal).
    seen_urls: set[str] = set()
    results: List[Dict[str, Any]] = []

    for i, query in enumerate(queries, start=1):
        try:
            raw = _fetch_one(api_key, query)
        except Exception as exc:
            logger.warning("[CourtFee] query %d/%d failed: %s", i, len(queries), exc)
            if i == 1:
                # Primary query failed — return error immediately.
                return {"query": primary_query, "results": [], "summary": "", "error": str(exc)}
            continue  # Secondary failure is non-fatal.

        for item in raw:
            url = item.get("url", "")
            if url in seen_urls:
                continue  # Deduplicate across queries.
            seen_urls.add(url)
            snippet = _strip_html(item.get("description", ""))
            results.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": snippet,
                "date": item.get("published", ""),
            })

    # Build summary from fee-relevant snippets first, then fall back to all snippets
    # so the draft model always gets some context even if no snippet is rate-specific.
    fee_lines = [
        f"[{r['title']}] {r['snippet']}"
        for r in results
        if _is_fee_relevant(r["snippet"])
    ]
    all_lines = [
        f"[{r['title']}] {r['snippet']}"
        for r in results
        if r["snippet"]
    ]
    summary = "\n".join(fee_lines) if fee_lines else "\n".join(all_lines)

    logger.info(
        "[CourtFee] %d total results (%d fee-relevant) for state=%r doc_type=%r",
        len(results), len(fee_lines), state, doc_type,
    )
    return {"query": primary_query, "results": results, "summary": summary, "error": None}


def _build_legal_research_queries(
    *,
    doc_type: str,
    cause_of_action: str,
    jurisdiction: str,
) -> List[str]:
    """Build two queries for legal doctrine: limitation period + procedural requirements.

    Queries are driven entirely by doc_type, cause_of_action, and jurisdiction.
    No legal content is hardcoded — the web search result drives what the model applies.
    """
    doc_label = doc_type.replace("_", " ")
    coa_label = cause_of_action.replace("_", " ") if cause_of_action else doc_label

    # Q1: limitation period — surfaces the correct accrual date rule for this cause of action.
    q1_parts = [coa_label, "limitation period India years accrual date right to sue"]
    if jurisdiction:
        q1_parts.append(jurisdiction)

    # Q2: procedural requirements — surfaces mandatory elements for this doc_type in this court.
    q2_parts = [doc_label, "mandatory procedural requirements India"]
    if jurisdiction:
        q2_parts.append(jurisdiction)

    return [" ".join(q1_parts), " ".join(q2_parts)]


def _is_legal_relevant(snippet: str) -> bool:
    """Return True if the snippet contains actionable legal doctrine."""
    low = snippet.lower()
    return any(signal in low for signal in _LEGAL_SIGNAL_WORDS)


# ---------------------------------------------------------------------------
# Procedural Provisions Web Search — surfaces special procedural acts
# (e.g., Commercial Courts Act, MSMED Act, arbitration clause requirements)
# that are NOT in RAG but affect filing requirements.
# ---------------------------------------------------------------------------

# Factual indicators (NOT legal rules) that hint the dispute may need
# special procedural handling. Used only for query construction.
_COMMERCIAL_INDICATORS = frozenset({
    "commercial", "business", "trade", "supply", "vendor",
    "contract", "agreement", "partnership", "company", "firm",
    "franchise", "dealership", "license", "arbitration",
    "construction", "manufacturer", "distributor", "agency",
    "joint venture", "consortium", "export", "import",
})


def _build_procedural_queries(
    *,
    doc_type: str,
    cause_of_action: str,
    jurisdiction: str,
    suit_value: Optional[float],
    facts_keywords: Optional[List[str]],
) -> List[str]:
    """Build 1-2 targeted queries for procedural requirements.

    Q1 (always): mandatory procedural requirements for this filing type.
    Q2 (conditional): commercial dispute–specific requirements — only when
    facts_keywords contain commercial indicators.

    No legal content is hardcoded — queries surface whatever procedural acts
    are relevant. The web search results determine what provisions are found.
    """
    doc_label = doc_type.replace("_", " ")
    coa_label = cause_of_action.replace("_", " ") if cause_of_action else doc_label

    # Q1: generic procedural requirements for this filing type
    q1_parts = [doc_label, "mandatory procedural requirements filing India"]
    if jurisdiction:
        q1_parts.append(jurisdiction)
    queries = [" ".join(q1_parts)]

    # Q2: commercial-specific — only when facts suggest a commercial dispute
    kw_set = set(w.lower() for w in (facts_keywords or []))
    has_commercial = bool(kw_set & _COMMERCIAL_INDICATORS)
    if has_commercial:
        q2_parts = [
            coa_label,
            "commercial dispute",
            "pre-institution mediation Section 12A",
            "Commercial Courts Act",
            "statement of truth",
            "India",
        ]
        queries.append(" ".join(q2_parts))

    return queries


async def ProceduralWebSearchTool(
    *,
    doc_type: str,
    cause_of_action: str = "",
    jurisdiction: str = "",
    suit_value: Optional[float] = None,
    facts_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Fetch procedural requirements via Brave Search.

    Surfaces special procedural acts (Commercial Courts Act, MSMED Act, etc.)
    that are not in RAG but affect filing requirements for this dispute type.

    Returns dict with keys:
        queries:  list — queries used
        results:  list — deduplicated results [{title, url, snippet, date}]
        summary:  str  — legal-relevant snippets for prompt injection
        error:    str|None
    """
    api_key = (settings.BRAVE_API_KEY or "").strip()
    if not api_key:
        logger.warning("[Procedural] BRAVE_API_KEY not set — skipping")
        return {"queries": [], "results": [], "summary": "", "error": "BRAVE_API_KEY not configured"}

    queries = _build_procedural_queries(
        doc_type=doc_type,
        cause_of_action=cause_of_action,
        jurisdiction=jurisdiction,
        suit_value=suit_value,
        facts_keywords=facts_keywords,
    )
    logger.info("[Procedural] queries: %s", queries)

    seen_urls: set[str] = set()
    results: List[Dict[str, Any]] = []

    for i, query in enumerate(queries, start=1):
        try:
            raw = _fetch_one(api_key, query)
        except Exception as exc:
            logger.warning("[Procedural] query %d/%d failed: %s", i, len(queries), exc)
            continue  # Both queries are best-effort.

        for item in raw:
            url = item.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            snippet = _strip_html(item.get("description", ""))
            results.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": snippet,
                "date": item.get("published", ""),
            })

    legal_lines = [
        f"[{r['title']}] {r['snippet']}"
        for r in results
        if _is_legal_relevant(r["snippet"])
    ]
    all_lines = [
        f"[{r['title']}] {r['snippet']}"
        for r in results
        if r["snippet"]
    ]
    summary = "\n".join(legal_lines) if legal_lines else "\n".join(all_lines)

    logger.info(
        "[Procedural] %d total results (%d legal-relevant) for doc_type=%r",
        len(results), len(legal_lines), doc_type,
    )
    return {"queries": queries, "results": results, "summary": summary, "error": None}


async def LegalResearchWebSearchTool(
    *,
    doc_type: str,
    cause_of_action: str = "",
    jurisdiction: str = "",
) -> Dict[str, Any]:
    """
    Fetch legal doctrine context via Brave Search: limitation period + procedural requirements.

    Runs two complementary queries driven by doc_type and cause_of_action.
    No legal content is hardcoded — everything comes from web search results.

    Returns dict with keys:
        queries:  list — queries used
        results:  list — deduplicated results [{title, url, snippet, date}]
        summary:  str  — doctrine-relevant snippets for prompt injection
        error:    str|None
    """
    api_key = (settings.BRAVE_API_KEY or "").strip()
    if not api_key:
        logger.warning("[LegalResearch] BRAVE_API_KEY not set — skipping")
        return {"queries": [], "results": [], "summary": "", "error": "BRAVE_API_KEY not configured"}

    queries = _build_legal_research_queries(
        doc_type=doc_type,
        cause_of_action=cause_of_action,
        jurisdiction=jurisdiction,
    )
    logger.info("[LegalResearch] queries: %s", queries)

    seen_urls: set[str] = set()
    results: List[Dict[str, Any]] = []

    for i, query in enumerate(queries, start=1):
        try:
            raw = _fetch_one(api_key, query)
        except Exception as exc:
            logger.warning("[LegalResearch] query %d/%d failed: %s", i, len(queries), exc)
            continue  # Both queries are best-effort.

        for item in raw:
            url = item.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            snippet = _strip_html(item.get("description", ""))
            results.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": snippet,
                "date": item.get("published", ""),
            })

    doctrine_lines = [
        f"[{r['title']}] {r['snippet']}"
        for r in results
        if _is_legal_relevant(r["snippet"])
    ]
    all_lines = [
        f"[{r['title']}] {r['snippet']}"
        for r in results
        if r["snippet"]
    ]
    summary = "\n".join(doctrine_lines) if doctrine_lines else "\n".join(all_lines)

    logger.info(
        "[LegalResearch] %d total results (%d doctrine-relevant) for doc_type=%r",
        len(results), len(doctrine_lines), doc_type,
    )
    return {"queries": queries, "results": results, "summary": summary, "error": None}
