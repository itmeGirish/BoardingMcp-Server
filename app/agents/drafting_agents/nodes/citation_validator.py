"""Citation Validator Node — deterministic (NO LLM).

Verifies all statutory citations in the draft against
enrichment.verified_provisions. Flags fabricated case citations.

Pipeline position: assembler → postprocess → **citation_validator** → review
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List

from langgraph.graph import END
from langgraph.types import Command

from ....config import logger, settings
from ..states import DraftingState
from ._utils import _as_dict


# Well-known procedural provisions that don't need enrichment verification
_ALWAYS_ALLOWED = {
    # CPC
    "Section 26", "Section 34", "Section 151", "Section 9",
    "Order VI Rule 15", "Order VII Rule 1", "Order VII Rule 10",
    "Order VII Rule 11", "Order XXXIX Rule 1", "Order XXXIX Rule 2",
    # CrPC / BNSS
    "Section 439", "Section 482", "Section 438",
    "Section 437", "Section 167", "Section 154",
    # Constitution
    "Article 14", "Article 19", "Article 21", "Article 226", "Article 32",
    "Article 136", "Article 227", "Article 300A",
    # Evidence Act / BSA
    "Section 65B",
}

# Case citation patterns (AIR, SCC, ILR, etc.)
_RE_CASE_CITATION = re.compile(
    r"\b(?:AIR|SCC|ILR|SCR|Bom\.?\s*LR|All\.?\s*LR|MLJ|KLT|CrLJ)"
    r"\s+\d{4}\s+\w+\s+\d+",
    re.IGNORECASE,
)

# Statutory section pattern: "Section 65 of the Indian Contract Act"
_RE_STATUTE_CITATION = re.compile(
    r"(?:Section|S\.?)\s+(\d+[A-Z]?)"
    r"(?:\s+(?:of|under|read\s+with)\s+(?:the\s+)?"
    r"([A-Za-z][A-Za-z\s,]+?(?:Act|Code)[,\s]*(?:\d{4})?))?",
    re.IGNORECASE,
)

# Limitation article pattern: "Article 55 of the ... Limitation Act"
_RE_LIM_ARTICLE = re.compile(
    r"Article\s+(\d{1,3})\s+(?:of\s+)?(?:the\s+)?(?:Schedule\s+(?:to\s+)?)?"
    r"(?:the\s+)?Limitation\s+Act",
    re.IGNORECASE,
)


def citation_validator_node(state: DraftingState) -> Command:
    """Verify all statutory citations in draft against enrichment."""
    logger.info("[CITATION_VALIDATOR] ▶ start")
    t0 = time.perf_counter()

    skip_review = getattr(settings, "DRAFTING_SKIP_REVIEW", False)
    _next_node = END if skip_review else "review"

    enabled = getattr(settings, "DRAFTING_CITATION_VALIDATOR_ENABLED", True)
    if not enabled:
        logger.info("[CITATION_VALIDATOR] disabled — skipping")
        update = {"citation_issues": []}
        if skip_review:
            update["final_draft"] = _as_dict(state.get("draft"))
        return Command(update=update, goto=_next_node)

    draft = _as_dict(state.get("draft"))
    mandatory_provisions = _as_dict(state.get("mandatory_provisions"))

    # Get draft text
    artifacts = draft.get("draft_artifacts") or []
    draft_text = ""
    if artifacts and isinstance(artifacts[0], dict):
        draft_text = artifacts[0].get("text", "")

    if not draft_text:
        logger.info("[CITATION_VALIDATOR] no draft text — skipping")
        update = {"citation_issues": []}
        if skip_review:
            update["final_draft"] = _as_dict(state.get("draft"))
        return Command(update=update, goto=_next_node)

    # Build verified set from enrichment
    verified_provisions = mandatory_provisions.get("verified_provisions") or []
    verified_set = set()
    for p in verified_provisions:
        if isinstance(p, dict):
            sec = (p.get("section") or "").strip()
            if sec:
                verified_set.add(sec)

    # Add limitation article if present
    lim = mandatory_provisions.get("limitation")
    if lim and isinstance(lim, dict) and lim.get("article"):
        verified_set.add(f"Article {lim['article']}")

    issues: List[Dict[str, Any]] = []

    # Check 1: Case citations (AIR/SCC/ILR)
    for m in _RE_CASE_CITATION.finditer(draft_text):
        issues.append({
            "type": "fabricated_case_citation",
            "severity": "ERROR",
            "citation": m.group(0),
            "message": f"Case citation '{m.group(0)}' found — case citations are disallowed unless user requested them",
        })

    # Check 2: Statutory section citations
    for m in _RE_STATUTE_CITATION.finditer(draft_text):
        sec_num = m.group(1)
        act_name = (m.group(2) or "").strip()
        full_ref = f"Section {sec_num}"

        # Skip well-known procedural provisions
        if full_ref in _ALWAYS_ALLOWED:
            continue

        # Check Order/Rule patterns (always allowed)
        context_start = max(0, m.start() - 10)
        context = draft_text[context_start:m.start()].strip()
        if re.search(r"Order\s+[IVXLCDM]+\s+Rule$", context, re.IGNORECASE):
            continue

        # Check against verified provisions
        if full_ref not in verified_set:
            # Check with act name too
            full_with_act = f"{full_ref} {act_name}".strip()
            found_in_verified = False
            for v in verified_set:
                if sec_num in v:
                    found_in_verified = True
                    break
            if not found_in_verified:
                issues.append({
                    "type": "unverified_statute",
                    "severity": "WARN",
                    "citation": full_with_act or full_ref,
                    "message": f"'{full_with_act or full_ref}' not in verified_provisions — may be correct but unverified",
                })

    # Check 3: Limitation article citations
    for m in _RE_LIM_ARTICLE.finditer(draft_text):
        art_id = m.group(1)
        full_ref = f"Article {art_id}"
        if full_ref not in verified_set:
            issues.append({
                "type": "unverified_limitation_article",
                "severity": "WARN",
                "citation": full_ref,
                "message": f"Limitation '{full_ref}' not in enrichment — may be hallucinated",
            })

    elapsed = time.perf_counter() - t0
    error_count = sum(1 for i in issues if i["severity"] == "ERROR")
    warn_count = sum(1 for i in issues if i["severity"] == "WARN")

    # Skip review for speed — promote draft directly to final_draft
    skip_review = getattr(settings, "DRAFTING_SKIP_REVIEW", False)
    if skip_review:
        current_draft = _as_dict(state.get("draft"))
        logger.info(
            "[CITATION_VALIDATOR] ✓ done (%.1fs) | verified_set=%d | errors=%d | warns=%d | → END (review skipped)",
            elapsed, len(verified_set), error_count, warn_count,
        )
        return Command(
            update={"citation_issues": issues, "final_draft": current_draft},
            goto=END,
        )

    logger.info(
        "[CITATION_VALIDATOR] ✓ done (%.1fs) | verified_set=%d | errors=%d | warns=%d | → review",
        elapsed, len(verified_set), error_count, warn_count,
    )
    return Command(update={"citation_issues": issues}, goto="review")
