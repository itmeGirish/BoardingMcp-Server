"""RAG Gap Enrichment Node — with LLM limitation selector.

Scans ALL RAG chunks for limitation article candidates and user-cited
provisions. Uses ONE small LLM call to select the correct limitation article
from candidates (replaces regex keyword scoring). For gaps: runs targeted
web search via Brave API. Stores structured results in
``mandatory_provisions`` state field.

Pipeline position: rag → **enrichment** → court_fee
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from ....config import logger, settings
from ....services import glm_model
from ..tools import CourtFeeWebSearchTool, LegalResearchWebSearchTool
from ..lkb import (
    filter_superseded_provisions,
    lookup,
    apply_specificity_rule,
    infer_cause_type,
)
from ..lkb.limitation import build_limitation_verified_provision, normalize_coa_type
from ..states import DraftingState
from ..tools.websearch import _fetch_one, _strip_html, _is_legal_relevant, ProceduralWebSearchTool
from ._utils import _as_dict, extract_json_from_text


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Limitation Act Schedule entry: "47. For money paid ... Three years. The date ..."
_RE_SCHEDULE_ENTRY = re.compile(
    r"(?:^|\n)\s*(\d{1,3})\.\s+"                          # article number
    r"((?:For|To|By|Of|A|An|In|On|Against|Under|When|Where|Any|Every|Suit|Application|Appeal)"
    r"[^.]{10,250}\.)"                                     # description (ends with period)
    r"\s*((?:Three|Two|One|Six|Twelve|Thirty|Sixty|Ninety|\d+)"
    r"\s+(?:year|month|day)s?\.?)"                          # limitation period
    r"(?:\s*((?:The\s+date|When|From)[^.\n]{5,200}\.?))?",  # accrual (optional)
    re.IGNORECASE | re.MULTILINE,
)

# "Article X of the Limitation Act"
_RE_ARTICLE_REF = re.compile(
    r"Article\s+(\d{1,3})\s+(?:of\s+)?(?:the\s+)?(?:Schedule\s+(?:to\s+)?)?(?:the\s+)?"
    r"Limitation\s+Act",
    re.IGNORECASE,
)

# Simple limitation period mention
_RE_PERIOD_SIMPLE = re.compile(
    r"limitation\s+(?:period\s+)?(?:of\s+|is\s+)?"
    r"((?:three|two|one|six|twelve|\d+)\s+(?:year|month|day)s?)",
    re.IGNORECASE,
)

# User request: "Section 65 of Indian Contract Act"
_RE_SECTION = re.compile(
    r"(?:Section|S\.?)\s+(\d+[A-Z]?)"
    r"(?:\s+(?:of|under)\s+(?:the\s+)?"
    r"([A-Za-z][A-Za-z\s,]+?(?:Act|Code)[,\s]*(?:\d{4})?))?",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# RAG Provision Scanner
# ---------------------------------------------------------------------------

# Regex for "Section X of [Act Name]" in RAG chunks
_RE_RAG_PROVISION = re.compile(
    r"(?:Section|S\.?)\s+(\d+[A-Z]?)"
    r"(?:\s+(?:of|under|,)\s+(?:the\s+)?"
    r"([A-Za-z][A-Za-z\s,]+?(?:Act|Code)[,\s]*(?:\d{4})?))?",
    re.IGNORECASE,
)


def _scan_rag_provisions(chunk_texts: List[str]) -> List[Dict[str, str]]:
    """Extract ALL 'Section X of Act' patterns from RAG chunks.

    Returns deduplicated list of {section, act, text, source} dicts.
    These are RAG-sourced provisions available for the draft LLM to cite.
    """
    provisions: List[Dict[str, str]] = []
    seen: set = set()
    for text in chunk_texts:
        for m in _RE_RAG_PROVISION.finditer(text):
            sec_num = m.group(1)
            act_name = (m.group(2) or "").strip()
            key = f"Section {sec_num}"
            dedup_key = f"{key} {act_name}".lower().strip()
            if dedup_key not in seen:
                seen.add(dedup_key)
                # Extract surrounding context (up to 300 chars)
                start = max(0, m.start() - 20)
                end = min(len(text), m.end() + 300)
                context = text[start:end].strip()
                provisions.append({
                    "section": key,
                    "act": act_name,
                    "text": context[:500],
                    "source": "rag",
                })
    return provisions


# ---------------------------------------------------------------------------
# Procedural Provisions — helpers for Step 6.7
# ---------------------------------------------------------------------------

def _extract_facts_keywords(
    facts: Dict[str, Any], user_request: str, topics: List[str],
) -> List[str]:
    """Tokenize facts summary + user request + topics into lowercase keywords.

    Used for query construction only — no legal judgment, just signal extraction.
    """
    parts: List[str] = []
    summary = facts.get("summary", "")
    if summary:
        parts.extend(summary.lower().split())
    if user_request:
        parts.extend(user_request.lower().split())
    for topic in topics:
        if isinstance(topic, str):
            parts.extend(topic.lower().split())
    return parts


def _extract_procedural_provisions(
    web_results: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Extract 'Section X of Act' patterns from procedural web search snippets.

    Reuses _RE_RAG_PROVISION regex. Returns deduplicated provisions with
    source="websearch_procedural". Same format as _scan_rag_provisions output.
    """
    provisions: List[Dict[str, str]] = []
    seen: set = set()
    for item in web_results:
        snippet = item.get("snippet", "")
        if not snippet:
            continue
        for m in _RE_RAG_PROVISION.finditer(snippet):
            sec_num = m.group(1)
            act_name = (m.group(2) or "").strip()
            key = f"Section {sec_num}"
            dedup_key = f"{key} {act_name}".lower().strip()
            if dedup_key not in seen:
                seen.add(dedup_key)
                start = max(0, m.start() - 20)
                end = min(len(snippet), m.end() + 300)
                context = snippet[start:end].strip()
                provisions.append({
                    "section": key,
                    "act": act_name,
                    "text": context[:500],
                    "source": "websearch_procedural",
                })
    return provisions


# ---------------------------------------------------------------------------
# LLM Limitation Selector — prompt
# ---------------------------------------------------------------------------

_LIM_SELECTOR_SYSTEM = """You are a legal limitation period expert for Indian law.

Select the MOST APPLICABLE Limitation Act 1963 article for the described suit.
Choose ONLY from the provided candidate articles. If none of the candidates fit
the described suit, or if the facts are insufficient to decide, output UNKNOWN.

Output ONLY valid JSON — no explanation, no markdown:
{"selected_article_id": "55", "period": "Three years", "reason": "breach of contract under Section 73 ICA"}
OR:
{"selected_article_id": "UNKNOWN", "period": "", "reason": "insufficient facts to determine applicable article"}
"""


# ---------------------------------------------------------------------------
# Common Limitation Articles — public statute data (Limitation Act 1963 Schedule)
# Used ONLY as fallback candidates when RAG + web search both fail.
# LLM still has final say — this only provides candidates, not legal advice.
# ---------------------------------------------------------------------------

_COMMON_ARTICLES: List[Dict[str, Any]] = [
    # Contract
    {"article": "54", "description": "For specific performance of a contract", "period": "Three years", "accrual": "The date fixed for performance, or if no date is fixed, when the plaintiff has notice that performance is refused", "source": "schedule_fallback"},
    {"article": "55", "description": "For compensation for breach of any contract, express or implied, not herein specially provided for", "period": "Three years", "accrual": "When the contract is broken", "source": "schedule_fallback"},
    # Money / loan / deposit
    {"article": "19", "description": "For money lent under an agreement that it shall be payable on demand", "period": "Three years", "accrual": "When the loan is made", "source": "schedule_fallback"},
    {"article": "22", "description": "For money deposited under an agreement that it shall be payable on demand including money of a customer in the hand of his banker", "period": "Three years", "accrual": "When the money is payable (on demand)", "source": "schedule_fallback"},
    # Goods / supply
    {"article": "14", "description": "For the price of goods sold and delivered where no fixed period of credit is agreed upon", "period": "Three years", "accrual": "When the goods are delivered", "source": "schedule_fallback"},
    {"article": "15", "description": "For the price of goods sold and delivered where a fixed period of credit is agreed upon", "period": "Three years", "accrual": "When the period of credit expires", "source": "schedule_fallback"},
    {"article": "47", "description": "For money paid upon an existing consideration which afterwards fails", "period": "Three years", "accrual": "When the consideration fails", "source": "schedule_fallback"},
    # Instruments
    {"article": "35", "description": "On a promissory note or bill of exchange payable at sight or after a certain period", "period": "Three years", "accrual": "When the note or bill is presented for payment", "source": "schedule_fallback"},
    {"article": "36", "description": "On a promissory note or bond payable by instalments", "period": "Three years", "accrual": "The expiration of the first term of payment", "source": "schedule_fallback"},
    # Property
    {"article": "65", "description": "For possession of immovable property based on title", "period": "Twelve years", "accrual": "When the possession of the defendant becomes adverse to the plaintiff", "source": "schedule_fallback"},
    {"article": "69", "description": "For recovery of specific movable property", "period": "Three years", "accrual": "When the property is wrongfully taken", "source": "schedule_fallback"},
    # Residual / general
    {"article": "113", "description": "Any suit for which no period of limitation is provided elsewhere in this Schedule", "period": "Three years", "accrual": "When the right to sue accrues", "source": "schedule_fallback"},
    {"article": "1", "description": "For compensation for loss or damage caused by tort", "period": "One year", "accrual": "When the loss or damage occurs", "source": "schedule_fallback"},
]


async def _websearch_limitation_retry(
    coa: str, doc_type: str, facts_summary: str, user_request: str,
) -> List[Dict[str, Any]]:
    """Targeted retry search with more specific query."""
    api_key = (getattr(settings, "BRAVE_API_KEY", "") or "").strip()
    if not api_key:
        return []

    coa_label = coa.replace("_", " ")
    query = (
        f'"Article" "Limitation Act 1963" "{coa_label}" '
        f"schedule period years India"
    )
    logger.info("[ENRICHMENT] limitation retry websearch: %r", query)

    try:
        items = _fetch_one(api_key, query)
    except Exception as exc:
        logger.warning("[ENRICHMENT] limitation retry websearch failed: %s", exc)
        return []

    candidates: List[Dict[str, Any]] = []
    seen: set = set()
    for item in items:
        snippet = _strip_html(item.get("description", ""))
        # Try to extract Schedule-format entries
        for entry in _RE_SCHEDULE_ENTRY.finditer(snippet):
            art_id = entry.group(1)
            if art_id not in seen:
                seen.add(art_id)
                candidates.append({
                    "article": art_id,
                    "description": (entry.group(2) or "").strip(),
                    "period": (entry.group(3) or "").strip(),
                    "accrual": (entry.group(4) or "").strip(),
                    "source": "websearch_retry",
                })
        # Also grab Article X references
        for art_match in re.finditer(r"Article\s+(\d{1,3})", snippet, re.IGNORECASE):
            art_id = art_match.group(1)
            if art_id not in seen:
                seen.add(art_id)
                per = _RE_PERIOD_SIMPLE.search(snippet)
                candidates.append({
                    "article": art_id,
                    "description": snippet[:300],
                    "period": per.group(1) if per else "",
                    "accrual": "",
                    "source": "websearch_retry",
                })
    return candidates


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

async def enrichment_node(state: DraftingState) -> Command:
    """Deterministic enrichment — LKB only, zero LLM calls, zero API calls.

    RAG and websearch disconnected (code preserved in tools/, nodes/ragDomain.py).
    All enrichment now comes from the LKB (92 cause types, fully deterministic):
      1. Limitation article from LKB
      2. User-cited provisions parsed from user_request (marked unverified)
      3. LKB brief (acts, reliefs, court rules, court detection)
      4. Verified provisions built from LKB primary_acts + alternative_acts
    """
    logger.info("[ENRICHMENT] ▶ start (deterministic, LKB-only)")
    t0 = time.perf_counter()

    classify = _as_dict(state.get("classify"))
    civil_decision = _as_dict(state.get("civil_decision"))
    intake = _as_dict(state.get("intake"))
    user_request = (state.get("user_request") or "").strip()

    doc_type = (classify.get("doc_type") or "").lower()
    classification = _as_dict(classify.get("classification"))
    facts = _as_dict(intake.get("facts"))
    topics = classification.get("topics") or []
    resolved_cause_type = normalize_coa_type(
        str(civil_decision.get("resolved_cause_type") or classify.get("cause_type") or "")
    )
    topic_hint = normalize_coa_type((topics[0] if topics else "").lower().replace(" ", "_"))
    coa = resolved_cause_type or topic_hint

    log: List[str] = []
    result: Dict[str, Any] = {
        "limitation": None,
        "user_cited_provisions": [],
        "verified_provisions": [],
        "procedural_provisions": [],
        "procedural_context": "",
        "enrichment_log": log,
    }

    # ── Step 1: Limitation from LKB (deterministic) ───────────────────
    cause_type = coa or ""
    law_domain = classify.get("law_domain", "Civil")

    if not cause_type:
        _pre_cause_type = (classify.get("cause_type") or "").lower().replace(" ", "_").replace("-", "_")
        if not _pre_cause_type and law_domain == "Civil":
            _inferred = infer_cause_type(doc_type, user_request, (classification.get("topics") or []))
            _pre_cause_type = _inferred[0] if isinstance(_inferred, tuple) else _inferred
        cause_type = normalize_coa_type(_pre_cause_type)

    if cause_type:
        cause_type = normalize_coa_type(cause_type)

    lkb_entry = lookup(law_domain, cause_type) if cause_type else None

    if lkb_entry:
        lkb_lim = lkb_entry.get("limitation", {})
        lkb_art = str(lkb_lim.get("article", ""))
        lkb_ref = str(lkb_lim.get("reference", ""))

        if lkb_art == "NONE":
            result["limitation"] = {
                "article": "NONE",
                "reference": "",
                "act": "",
                "description": lkb_lim.get("description", "No limitation applies"),
                "period": lkb_lim.get("period", ""),
                "reason": f"LKB: {cause_type} — {lkb_lim.get('from', '')}",
                "source": "lkb",
            }
            log.append(f"limitation: LKB says NONE for {cause_type}")
        elif lkb_art == "UNKNOWN" and not lkb_ref:
            log.append(f"limitation: LKB says UNKNOWN for {cause_type} — placeholder")
        elif lkb_art or lkb_ref:
            result["limitation"] = {
                "article": lkb_art or "N/A",
                "reference": lkb_ref,
                "act": lkb_lim.get("act", ""),
                "description": lkb_lim.get("description", ""),
                "period": lkb_lim.get("period", ""),
                "from": lkb_lim.get("from", ""),
                "reason": f"LKB: {cause_type} — {lkb_lim.get('description', '')}",
                "source": "lkb",
            }
            log.append(f"limitation: LKB Article {lkb_art or lkb_ref} for {cause_type}")
        else:
            log.append(f"limitation: LKB has no limitation data for {cause_type} — placeholder")

        logger.info(
            "[ENRICHMENT] limitation: %s for %s",
            result["limitation"]["article"] if result["limitation"] else "placeholder",
            cause_type,
        )
    else:
        if cause_type:
            log.append(f"limitation: no LKB entry for {cause_type} — placeholder")
        else:
            log.append("limitation: no cause_type — placeholder")

    # ── Step 2: Build verified_provisions from limitation ─────────────
    limitation_provision = build_limitation_verified_provision(result["limitation"])
    if limitation_provision:
        result["verified_provisions"].append(limitation_provision)

    # ── Step 3: User-cited sections (parsed, marked unverified) ───────
    user_secs = _parse_user_sections(user_request)
    for sec in user_secs:
        key = sec["section"]
        act = sec.get("act", "")
        prov = {"section": key, "act": act, "text": "", "source": "user_cited"}
        result["user_cited_provisions"].append(prov)
        result["verified_provisions"].append(prov)
        log.append(f"{key} {act}: user-cited (unverified)")

    # ── Step 4: Build verified_provisions from LKB primary/alt acts ───
    if lkb_entry:
        for act_entry in lkb_entry.get("primary_acts", []):
            act_name = act_entry.get("act", "")
            for section in act_entry.get("sections", []):
                prov = {"section": section, "act": act_name, "text": "", "source": "lkb"}
                result["verified_provisions"].append(prov)
        for act_entry in lkb_entry.get("alternative_acts", []):
            act_name = act_entry.get("act", "")
            for section in act_entry.get("sections", []):
                prov = {"section": section, "act": act_name, "text": "", "source": "lkb"}
                result["verified_provisions"].append(prov)
        log.append(f"provisions: {len(result['verified_provisions'])} from LKB primary+alternative acts")

    # ── Step 5: LKB brief + court detection ───────────────────────────
    lkb_brief = None
    if not cause_type and law_domain == "Civil":
        _inferred = infer_cause_type(doc_type, user_request, topics)
        cause_type = _inferred[0] if isinstance(_inferred, tuple) else _inferred
        log.append(f"lkb: cause_type inferred as '{cause_type}' from doc_type+request")

    if cause_type and lkb_entry:
        lkb_brief = lkb_entry.copy()
        if lkb_brief.get("coa_type"):
            lkb_brief["coa_type"] = normalize_coa_type(lkb_brief.get("coa_type", ""))
        log.append(f"lkb: found entry for {cause_type}")

        # Apply supersession filter
        before_count = len(result["verified_provisions"])
        result["verified_provisions"] = filter_superseded_provisions(
            result["verified_provisions"],
        )
        filtered = before_count - len(result["verified_provisions"])
        if filtered:
            log.append(f"lkb: filtered {filtered} superseded provisions")

        # Court detection — Commercial Court requires amount > threshold + commercial nature
        court_rules = lkb_entry.get("court_rules", {})
        amounts = _as_dict(facts.get("amounts"))
        suit_value = amounts.get("principal") or amounts.get("damages") or 0
        _has_commercial_rules = "commercial" in court_rules
        _threshold = court_rules.get("commercial", {}).get("threshold", 300000) if _has_commercial_rules else 0
        _amount_exceeds = suit_value and float(suit_value) > _threshold

        _user_says_commercial = False
        if _has_commercial_rules and not _amount_exceeds:
            _check_text_comm = (
                (user_request or "") + " "
                + (facts.get("summary", "") if isinstance(facts, dict) else "") + " "
                + " ".join(topics)
            ).lower()
            nature_keywords_check = court_rules["commercial"].get("nature_keywords")
            _inherently_commercial = nature_keywords_check is not None and len(nature_keywords_check) == 0
            if _inherently_commercial and "commercial" in _check_text_comm:
                _user_says_commercial = True

        if _has_commercial_rules and (_amount_exceeds or _user_says_commercial):
            nature_keywords = court_rules["commercial"].get("nature_keywords")
            if nature_keywords is None or len(nature_keywords) == 0:
                lkb_brief["detected_court"] = court_rules["commercial"]
                reason = f"value={suit_value} > threshold" if _amount_exceeds else "user request says commercial"
                log.append(f"lkb: commercial court ({reason})")
            else:
                _check_text = (
                    (user_request or "") + " "
                    + (facts.get("summary", "") if isinstance(facts, dict) else "") + " "
                    + " ".join(topics)
                ).lower()
                is_commercial = any(kw in _check_text for kw in nature_keywords)
                if is_commercial:
                    lkb_brief["detected_court"] = court_rules["commercial"]
                    log.append(f"lkb: commercial court (value + nature confirmed)")
                else:
                    lkb_brief["detected_court"] = court_rules.get("default", {})
                    log.append(f"lkb: value > threshold but no commercial indicators — default court")
        else:
            lkb_brief["detected_court"] = court_rules.get("default", {})

        logger.info("[ENRICHMENT] LKB brief ready: cause_type=%s court=%s", cause_type, lkb_brief.get("detected_court", {}).get("court", "default"))
    elif cause_type:
        log.append(f"lkb: no entry found for cause_type={cause_type}")
    else:
        log.append("lkb: no cause_type available — LKB skipped")

    update_dict: Dict[str, Any] = {"mandatory_provisions": result, "lkb_brief": lkb_brief}

    elapsed = time.perf_counter() - t0
    logger.info(
        "[ENRICHMENT] ✓ done (%.1fs) | limitation=%s | verified=%d | lkb=%s",
        elapsed,
        result["limitation"]["article"] if result["limitation"] else "none",
        len(result["verified_provisions"]),
        cause_type or "none",
    )
    return Command(update=update_dict, goto="domain_plan_compiler")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_limitation_candidates(
    chunk_texts: List[str],
) -> List[Dict[str, Any]]:
    """Regex-extract ALL candidate limitation articles from RAG chunks.

    Aggressive extraction — grabs every Article mention. No scoring or filtering.
    The LLM selector picks the right one.
    """
    candidates: List[Dict[str, Any]] = []
    seen_articles: set = set()

    for text in chunk_texts:
        # Schedule entries: "47. For money paid ... Three years. The date ..."
        for m in _RE_SCHEDULE_ENTRY.finditer(text):
            art_id = m.group(1)
            if art_id not in seen_articles:
                seen_articles.add(art_id)
                candidates.append({
                    "article": art_id,
                    "description": (m.group(2) or "").strip(),
                    "period": (m.group(3) or "").strip(),
                    "accrual": (m.group(4) or "").strip(),
                    "source": "rag",
                })

        # "Article X of the Limitation Act" references
        for m in _RE_ARTICLE_REF.finditer(text):
            art_id = m.group(1)
            if art_id not in seen_articles:
                seen_articles.add(art_id)
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 200)
                context = text[start:end].strip()
                pm = _RE_PERIOD_SIMPLE.search(context)
                candidates.append({
                    "article": art_id,
                    "description": context[:250],
                    "period": pm.group(1) if pm else "",
                    "accrual": "",
                    "source": "rag",
                })

    return candidates


async def _websearch_limitation_candidates(
    coa: str, doc_type: str,
) -> List[Dict[str, Any]]:
    """Targeted Brave search — returns candidate articles (not a final selection)."""
    api_key = (getattr(settings, "BRAVE_API_KEY", "") or "").strip()
    if not api_key:
        return []

    coa_label = coa.replace("_", " ")
    doc_label = doc_type.replace("_", " ")
    query = (
        f"Limitation Act 1963 Schedule article {coa_label} {doc_label} "
        f"India limitation period years"
    )
    logger.info("[ENRICHMENT] limitation websearch: %r", query)

    try:
        items = _fetch_one(api_key, query)
    except Exception as exc:
        logger.warning("[ENRICHMENT] limitation websearch failed: %s", exc)
        return []

    candidates: List[Dict[str, Any]] = []
    seen: set = set()
    for item in items:
        snippet = _strip_html(item.get("description", ""))
        for art_match in re.finditer(r"Article\s+(\d{1,3})", snippet, re.IGNORECASE):
            art_id = art_match.group(1)
            if art_id not in seen:
                seen.add(art_id)
                per = _RE_PERIOD_SIMPLE.search(snippet)
                candidates.append({
                    "article": art_id,
                    "description": snippet[:300],
                    "period": per.group(1) if per else "",
                    "accrual": "",
                    "source": "websearch",
                })
    return candidates


async def _llm_select_limitation(
    candidates: List[Dict[str, Any]],
    facts: Dict[str, Any],
    doc_type: str,
    coa: str,
    user_request: str,
) -> Optional[Dict[str, Any]]:
    """ONE LLM call to select the right limitation article from candidates.

    Returns the selected candidate dict with added 'reason' field,
    or None if LLM returns UNKNOWN or call fails.
    """
    llm_enabled = getattr(settings, "DRAFTING_ENRICHMENT_LLM_ENABLED", True)
    if not llm_enabled:
        logger.info("[ENRICHMENT] LLM limitation selector disabled — using first candidate")
        for c in candidates:
            if c.get("period"):
                return c
        return candidates[0] if candidates else None

    # Build candidate list for prompt
    candidate_lines = []
    for c in candidates:
        line = f"Article {c['article']}: {c['description']}"
        if c.get("period"):
            line += f" — Period: {c['period']}"
        if c.get("accrual"):
            line += f" — Accrual: {c['accrual']}"
        candidate_lines.append(line)

    facts_summary = facts.get("summary", "")
    user_prompt = (
        f"SUIT TYPE: {doc_type}\n"
        f"CAUSE OF ACTION: {coa.replace('_', ' ')}\n"
        f"FACTS SUMMARY: {facts_summary[:500]}\n"
        f"USER REQUEST (excerpt): {user_request[:300]}\n\n"
        f"CANDIDATE LIMITATION ARTICLES:\n"
        + "\n".join(candidate_lines)
        + "\n\nSelect the most applicable article. Output JSON only."
    )

    try:
        model = glm_model.resolve_model() if hasattr(glm_model, "resolve_model") else glm_model
        if model is None:
            logger.warning("[ENRICHMENT] glm_model unavailable — falling back to first candidate")
            return candidates[0] if candidates else None

        response = model.invoke([
            SystemMessage(content=_LIM_SELECTOR_SYSTEM),
            HumanMessage(content=user_prompt),
        ])
        raw_text = getattr(response, "content", "") or ""
        logger.info("[ENRICHMENT] LLM limitation selector raw: %s", raw_text[:200])

        parsed = extract_json_from_text(raw_text)
        if not parsed:
            # Try direct JSON parse
            try:
                parsed = json.loads(raw_text.strip())
            except (json.JSONDecodeError, ValueError):
                pass

        if not parsed:
            logger.warning("[ENRICHMENT] LLM limitation selector — could not parse response")
            return None

        selected_id = str(parsed.get("selected_article_id", "")).strip()
        reason = parsed.get("reason", "")

        if selected_id == "UNKNOWN" or not selected_id:
            logger.info("[ENRICHMENT] LLM returned UNKNOWN for limitation")
            return None

        # Find the matching candidate
        for c in candidates:
            if c["article"] == selected_id:
                c["reason"] = reason
                return c

        # Selected ID not in candidates — LLM hallucinated an article number
        logger.warning(
            "[ENRICHMENT] LLM selected Article %s but not in candidates — ignoring",
            selected_id,
        )
        return None

    except Exception as exc:
        logger.warning("[ENRICHMENT] LLM limitation selector failed: %s — falling back", exc)
        # Safe fallback: return first candidate with a period
        for c in candidates:
            if c.get("period"):
                return c
        return candidates[0] if candidates else None


def _parse_user_sections(user_request: str) -> List[Dict[str, str]]:
    """Extract explicit section citations from user request."""
    results: List[Dict[str, str]] = []
    seen: set = set()
    for m in _RE_SECTION.finditer(user_request):
        key = f"Section {m.group(1)}"
        if key not in seen:
            seen.add(key)
            results.append({"section": key, "act": (m.group(2) or "").strip()})
    return results


def _find_in_chunks(section_key: str, chunk_texts: List[str]) -> Optional[str]:
    """Search ALL chunks for the text of a specific section."""
    sec_match = re.match(r"Section\s+(.*)", section_key)
    if not sec_match:
        return None
    sec_id = sec_match.group(1).strip()
    pat = re.compile(
        r"(?:Section|S\.?)\s+" + re.escape(sec_id) + r"\b"
        r"|(?:^|\n)\s*" + re.escape(sec_id) + r"\.\s+",
        re.IGNORECASE | re.MULTILINE,
    )
    for text in chunk_texts:
        m = pat.search(text)
        if m:
            start = max(0, m.start() - 20)
            end = min(len(text), m.end() + 500)
            return text[start:end].strip()
    return None


async def _websearch_provision(
    section_key: str, act_name: str,
) -> Optional[Dict[str, Any]]:
    """Web search for a specific statutory provision text."""
    api_key = (getattr(settings, "BRAVE_API_KEY", "") or "").strip()
    if not api_key:
        return None
    query = f"{section_key} {act_name} India text provision".strip()
    logger.info("[ENRICHMENT] provision websearch: %r", query)
    try:
        items = _fetch_one(api_key, query)
    except Exception as exc:
        logger.warning("[ENRICHMENT] provision websearch failed: %s", exc)
        return None
    sec_num = section_key.split()[-1]
    for item in items:
        snippet = _strip_html(item.get("description", ""))
        if re.search(re.escape(sec_num), snippet, re.IGNORECASE):
            return {
                "section": section_key,
                "act": act_name or _infer_act(snippet),
                "text": snippet[:500],
                "source": "websearch",
            }
    return None


def _infer_act(snippet: str) -> str:
    """Try to infer act name from a snippet."""
    for pat in (
        r"(Indian\s+Contract\s+Act[,\s]*\d{4})",
        r"(Indian\s+Evidence\s+Act[,\s]*\d{4})",
        r"(Limitation\s+Act[,\s]*\d{4})",
        r"(Code\s+of\s+Civil\s+Procedure[,\s]*\d{4})",
        r"(Specific\s+Relief\s+Act[,\s]*\d{4})",
    ):
        m = re.search(pat, snippet, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""
