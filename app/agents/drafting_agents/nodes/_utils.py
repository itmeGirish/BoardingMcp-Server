from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, List

from ..lkb.limitation import get_limitation_reference_details


def _as_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return {}


def _as_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=True, indent=2)
    except Exception:
        return json.dumps(_as_dict(value), ensure_ascii=True, indent=2)


def build_court_fee_context(court_fee: Dict[str, Any], url_limit: int) -> str:
    """Build a formatted court fee context string from a web search result dict."""
    summary = (court_fee.get("summary") or "").strip()
    if not summary:
        return ""
    query = (court_fee.get("query") or "").strip()
    urls = " | ".join(
        r.get("url", "")
        for r in (court_fee.get("results") or [])[:url_limit]
        if r.get("url")
    )
    ctx = f"Search query: {query}\n{summary}"
    if urls:
        ctx += f"\nSources: {urls}"
    return ctx


def build_legal_research_context(legal_research: Dict[str, Any], url_limit: int) -> str:
    """Build a formatted legal research context string from a web search result dict."""
    summary = (legal_research.get("summary") or "").strip()
    if not summary:
        return ""
    queries: List[str] = legal_research.get("queries") or []
    urls = " | ".join(
        r.get("url", "")
        for r in (legal_research.get("results") or [])[:url_limit]
        if r.get("url")
    )
    ctx = f"Search queries: {', '.join(queries)}\n{summary}"
    if urls:
        ctx += f"\nSources: {urls}"
    return ctx


def build_mandatory_provisions_context(mandatory_provisions: Dict[str, Any]) -> str:
    """Build a formatted context string from enrichment node output.

    Returns a structured block the draft prompt can consume directly.
    """
    if not mandatory_provisions:
        return ""

    parts: List[str] = []

    # Limitation article
    lim = mandatory_provisions.get("limitation")
    if lim and isinstance(lim, dict):
        details = get_limitation_reference_details(lim)
        desc = lim.get("description", "")
        period = lim.get("period", "")
        accrual = lim.get("accrual", lim.get("from", ""))
        source = lim.get("source", "")
        if details["kind"] == "none":
            parts.append(
                f"LIMITATION (source: {source}):\n"
                f"  No limitation article applies.\n"
                f"  Description: {desc}\n"
                f"  Period: {period}\n"
                + (f"  Accrual: {accrual}\n" if accrual else "")
            )
        elif details["kind"] == "unknown":
            parts.append(
                f"LIMITATION (source: {source}):\n"
                f"  Citation could not be determined.\n"
                f"  Period: {period}\n"
                + (f"  Accrual: {accrual}\n" if accrual else "")
            )
        elif details["kind"] == "not_applicable":
            parts.append(
                f"LIMITATION (source: {source}):\n"
                f"  Governed by special statute / forum-specific rule.\n"
                f"  Description: {desc}\n"
                f"  Period: {period}\n"
                + (f"  Accrual: {accrual}\n" if accrual else "")
            )
        else:
            parts.append(
                f"LIMITATION (source: {source}):\n"
                f"  {details['citation']}\n"
                f"  Description: {desc}\n"
                f"  Period: {period}\n"
                + (f"  Accrual: {accrual}\n" if accrual else "")
            )

    # User-cited provisions
    provisions = mandatory_provisions.get("user_cited_provisions") or []
    if provisions:
        parts.append("USER-CITED STATUTORY PROVISIONS:")
        for p in provisions:
            if isinstance(p, dict):
                sec = p.get("section", "")
                act = p.get("act", "")
                text = p.get("text", "")
                source = p.get("source", "")
                parts.append(f"  {sec} {act} (source: {source}):\n    {text[:500]}")

    # Enrichment log (for transparency)
    log = mandatory_provisions.get("enrichment_log") or []
    if log:
        parts.append("ENRICHMENT LOG: " + " | ".join(log))

    return "\n".join(parts)


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse a JSON object from raw LLM text output.

    Handles cases where the model wraps JSON in markdown code fences
    or adds explanatory text before/after the JSON object.
    Returns parsed dict or None if no valid JSON object is found.
    """
    if not text:
        return None

    # 1. Strip markdown code fences (```json ... ``` or ``` ... ```)
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Find the outermost JSON object by balanced brace scanning
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    break
    return None
