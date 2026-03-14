from __future__ import annotations

import re
from typing import Any, Dict, Optional


_ARTICLE_RE = re.compile(r"^\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))?$")
_SECTION_PREFIX_RE = re.compile(r"^(?:s\.|sec(?:tion)?)\s*", re.IGNORECASE)
_SECTION_REFERENCE_RE = re.compile(r"^(Section\s+\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))?)\s+(.+)$")
_ACT_ABBREVIATIONS = {
    "A&C Act": "Arbitration and Conciliation Act, 1996",
    "CPA 2019": "Consumer Protection Act, 2019",
    "SARFAESI": "Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002",
    "IBC": "Insolvency and Bankruptcy Code, 2016",
}
_COA_TYPE_ALIASES = {
    "single_accrual": "single_event",
}


def normalize_coa_type(coa_type: str) -> str:
    """Normalize LKB cause-of-action labels to the values consumers understand."""
    normalized = (coa_type or "").strip().lower().replace(" ", "_").replace("-", "_")
    return _COA_TYPE_ALIASES.get(normalized, normalized)


def _normalize_reference(raw_reference: str) -> str:
    ref = (raw_reference or "").strip()
    if not ref:
        return ""
    ref = _SECTION_PREFIX_RE.sub("Section ", ref)
    for short, full in _ACT_ABBREVIATIONS.items():
        ref = ref.replace(short, full)
    if ref.startswith("Section ") and " of the " not in ref.lower():
        match = _SECTION_REFERENCE_RE.match(ref)
        if match:
            ref = f"{match.group(1)} of the {match.group(2).strip()}"
    return ref


def get_limitation_reference_details(limitation: Dict[str, Any] | None) -> Dict[str, Any]:
    """Return normalized metadata for a limitation entry."""
    lim = limitation if isinstance(limitation, dict) else {}
    article = str(lim.get("article", "") or "").strip()
    reference = _normalize_reference(str(lim.get("reference", "") or ""))
    act = str(lim.get("act", "") or "").strip()

    if reference and act and act.lower() not in reference.lower():
        citation = f"{reference} of the {act}"
    elif reference:
        citation = reference
    else:
        citation = ""

    if article == "NONE":
        return {
            "kind": "none",
            "citation": "",
            "short_citation": "",
            "act": "",
            "requires_citation": False,
            "is_limitation_act": False,
            "article": article,
        }

    if article.upper() in ("UNKNOWN", "RELATIONSHIP_DEPENDENT") and not reference:
        return {
            "kind": "unknown",
            "citation": "",
            "short_citation": "",
            "act": "",
            "requires_citation": False,
            "is_limitation_act": False,
            "article": article,
        }

    if reference:
        short_citation = reference.split(" of the ", 1)[0].strip()
        return {
            "kind": "statutory_reference",
            "citation": citation,
            "short_citation": short_citation,
            "act": act,
            "requires_citation": True,
            "is_limitation_act": False,
            "article": article,
        }

    if article == "N/A" or not article:
        return {
            "kind": "not_applicable",
            "citation": "",
            "short_citation": "",
            "act": "",
            "requires_citation": False,
            "is_limitation_act": False,
            "article": article,
        }

    if _ARTICLE_RE.fullmatch(article):
        short_citation = f"Article {article}"
        return {
            "kind": "limitation_article",
            "citation": f"{short_citation} of the Schedule to the Limitation Act, 1963",
            "short_citation": short_citation,
            "act": "Limitation Act, 1963",
            "requires_citation": True,
            "is_limitation_act": True,
            "article": article,
        }

    cleaned = _normalize_reference(article)
    short_citation = cleaned.split(" of the ", 1)[0].strip()
    return {
        "kind": "statutory_reference",
        "citation": cleaned,
        "short_citation": short_citation,
        "act": act,
        "requires_citation": True,
        "is_limitation_act": False,
        "article": article,
    }


def limitation_requires_citation(limitation: Dict[str, Any] | None) -> bool:
    return bool(get_limitation_reference_details(limitation).get("requires_citation"))


def limitation_short_citation(limitation: Dict[str, Any] | None) -> str:
    return str(get_limitation_reference_details(limitation).get("short_citation", ""))


def limitation_full_citation(limitation: Dict[str, Any] | None) -> str:
    return str(get_limitation_reference_details(limitation).get("citation", ""))


def build_limitation_verified_provision(
    limitation: Dict[str, Any] | None,
    *,
    source: str = "",
) -> Optional[Dict[str, str]]:
    details = get_limitation_reference_details(limitation)
    if not details["requires_citation"]:
        return None

    lim = limitation if isinstance(limitation, dict) else {}
    act = details["act"] or str(lim.get("act", "") or "").strip()
    if details["is_limitation_act"]:
        act = "Limitation Act, 1963"

    return {
        "section": details["short_citation"],
        "act": act,
        "text": str(lim.get("description", "") or ""),
        "source": source or str(lim.get("source", "") or ""),
    }
