"""Citation Validator Node — deterministic (NO LLM).

Verifies statutory citations using simple string containment against
enrichment.verified_provisions. No regex extraction from draft text.
Flags fabricated case citations (AIR/SCC/ILR).

Pipeline position: assembler → postprocess → **citation_validator** → review
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List

from langgraph.graph import END
from langgraph.types import Command

from ....config import logger, settings
from ..lkb.limitation import limitation_short_citation
from ..states import DraftingState
from ._utils import _as_dict


# Well-known procedural provisions that don't need enrichment verification
_ALWAYS_ALLOWED = {
    # CPC
    "Section 26", "Section 34", "Section 151", "Section 9",
    "Section 16", "Section 17", "Section 20",
    "Order VI Rule 15", "Order VII Rule 1", "Order VII Rule 10",
    "Order VII Rule 11", "Order XXXIX Rule 1", "Order XXXIX Rule 2",
    "Order XX Rule 18", "Order XXI Rule 90",
    # CrPC / BNSS
    "Section 439", "Section 482", "Section 438",
    "Section 437", "Section 167", "Section 154",
    # Constitution
    "Article 14", "Article 19", "Article 21", "Article 226", "Article 32",
    "Article 136", "Article 227", "Article 300A",
    # Evidence Act / BSA
    "Section 65B",
    # Common substantive sections (ICA, SRA, TPA, CPC)
    "Section 10", "Section 37", "Section 39", "Section 55",
    "Section 65", "Section 73", "Section 74",
}

# Case citation patterns (AIR, SCC, ILR, etc.) — only check for hallucinated case law
_RE_CASE_CITATION = re.compile(
    r"\b(?:AIR|SCC|ILR|SCR|Bom\.?\s*LR|All\.?\s*LR|MLJ|KLT|CrLJ)"
    r"\s+\d{4}\s+\w+\s+\d+",
    re.IGNORECASE,
)


_RE_SECTION_CITATION = re.compile(
    r"(?:Section|S\.?)\s+(\d+[A-Za-z]?(?:\(\d+\))?)"
    r"|(?:Order\s+[IVXLC]+\s+Rule\s+\d+[A-Za-z]?)"
    r"|(?:Article\s+\d+[A-Za-z]?)",
    re.IGNORECASE,
)


def _check_draft_citations_against_allowlist(
    draft_text: str,
    verified_set: set,
    issues: List[Dict[str, Any]],
):
    """Extract citations FROM draft and verify against allowlist.

    This is the reverse check (v10.0 Critical Gap #32):
    - Existing check: "is each ALLOWLIST provision in draft?"
    - This check: "is each DRAFT citation in ALLOWLIST?"
    """
    always_allowed_lower = {p.lower() for p in _ALWAYS_ALLOWED}
    verified_lower = {p.lower() for p in verified_set}
    combined = always_allowed_lower | verified_lower

    for m in _RE_SECTION_CITATION.finditer(draft_text):
        citation = m.group(0).strip()
        citation_lower = citation.lower()

        # Check if citation matches any verified provision
        if any(citation_lower in v or v in citation_lower for v in combined):
            continue

        # Skip common false positives from amounts/dates
        if re.match(r"Section\s+\d+\s*,\s*\d{2}", citation):
            continue  # Likely "Section 15,00,000" (currency)

        issues.append({
            "type": "unverified_draft_citation",
            "severity": "WARN",
            "citation": citation,
            "message": f"'{citation}' in draft not found in verified provisions — may be hallucinated",
        })


def _has_blocking_deterministic_findings(state: DraftingState, citation_issues: List[Dict[str, Any]]) -> bool:
    """Return True if deterministic checks still leave legal risk for review."""
    gate_issues = (
        (state.get("domain_gate_issues") or [])
        + (state.get("civil_gate_issues") or [])
        + (state.get("accuracy_gate_issues") or [])
    )
    for issue in gate_issues:
        if not isinstance(issue, dict):
            return True
        if (issue.get("severity") or "").lower() in {"blocking", "legal", "error", "warn"}:
            return True

    for issue in citation_issues:
        if not isinstance(issue, dict):
            return True
        if (issue.get("severity") or "").upper() in {"ERROR", "WARN"}:
            return True

    for issue in state.get("postprocess_issues") or []:
        if not isinstance(issue, dict):
            continue
        if (issue.get("severity") or "").lower() == "blocking":
            return True
        if issue.get("type") in {"drafting_note_language", "incomplete_sentence"}:
            return True

    return False


def citation_validator_node(state: DraftingState) -> Command:
    """Verify citations using string containment — no regex extraction from draft.

    Approach (v5.1 — no regex for statute extraction):
    1. Case citations (AIR/SCC/ILR) → regex detect → ERROR (hallucination risk)
    2. Verified provisions → simple `in` check → confirm each verified provision
       appears in draft text. Missing = WARN (provision not used).
    3. Limitation article → simple `in` check → confirm article cited in draft.

    No regex extraction of "Section X" from draft text. This eliminates false
    positives from currency amounts like "Rs. 15,00,000" being parsed as "Section 15".
    """
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
    limitation_ref = limitation_short_citation(lim if isinstance(lim, dict) else {})
    if limitation_ref:
        verified_set.add(limitation_ref)

    issues: List[Dict[str, Any]] = []
    draft_text_lower = draft_text.lower()
    always_allowed_lower = {p.lower() for p in _ALWAYS_ALLOWED}

    # ── Check 1: Case citations (AIR/SCC/ILR) — still use regex (specific pattern) ──
    for m in _RE_CASE_CITATION.finditer(draft_text):
        issues.append({
            "type": "fabricated_case_citation",
            "severity": "ERROR",
            "citation": m.group(0),
            "message": f"Case citation '{m.group(0)}' found — case citations are disallowed unless user requested them",
        })

    # ── Check 2: Verified provisions — simple string containment ──
    # Check that each verified provision appears in the draft text.
    # This flips the logic: instead of "extract citations from text → verify",
    # we check "verified provisions → present in text?"
    provisions_used = 0
    provisions_missing = 0
    for provision in verified_set:
        provision_lower = provision.lower()
        if provision_lower in always_allowed_lower:
            # Always-allowed provisions don't need to be in the draft
            if provision_lower in draft_text_lower:
                provisions_used += 1
            continue
        if provision_lower in draft_text_lower:
            provisions_used += 1
        else:
            provisions_missing += 1
            issues.append({
                "type": "verified_provision_not_cited",
                "severity": "INFO",
                "citation": provision,
                "message": f"Verified provision '{provision}' from enrichment not found in draft — may be acceptable",
            })

    # ── Check 3: Draft citations against allowlist (v10.0 — both directions) ──
    _check_draft_citations_against_allowlist(draft_text, verified_set, issues)

    # ── Check 4: Limitation article — simple string containment ──
    if limitation_ref and limitation_ref.lower() not in draft_text_lower:
        issues.append({
            "type": "limitation_reference_missing",
            "severity": "WARN",
            "citation": limitation_ref,
            "message": f"Limitation reference '{limitation_ref}' from enrichment not cited in draft",
        })

    elapsed = time.perf_counter() - t0
    error_count = sum(1 for i in issues if i["severity"] == "ERROR")
    warn_count = sum(1 for i in issues if i["severity"] == "WARN")
    info_count = sum(1 for i in issues if i["severity"] == "INFO")

    # Skip review for speed — promote draft directly to final_draft
    skip_review = getattr(settings, "DRAFTING_SKIP_REVIEW", False)
    if skip_review:
        current_draft = _as_dict(state.get("draft"))
        logger.info(
        "[CITATION_VALIDATOR] ✓ done (%.1fs) | verified=%d | used=%d | missing=%d | errors=%d | warns=%d | → END (review skipped)",
        elapsed, len(verified_set), provisions_used, provisions_missing, error_count, warn_count,
        )
        return Command(
            update={"citation_issues": issues, "final_draft": current_draft},
            goto=END,
        )

    skip_if_clean = getattr(settings, "DRAFTING_SKIP_REVIEW_AFTER_VALIDATION_IF_CLEAN", False)
    if skip_if_clean and not _has_blocking_deterministic_findings(state, issues):
        current_draft = _as_dict(state.get("draft"))
        logger.info(
            "[CITATION_VALIDATOR] ✓ done (%.1fs) | verified=%d | used=%d | missing=%d | errors=%d | warns=%d | → END (clean deterministic pass)",
            elapsed, len(verified_set), provisions_used, provisions_missing, error_count, warn_count,
        )
        return Command(
            update={"citation_issues": issues, "final_draft": current_draft},
            goto=END,
        )

    logger.info(
        "[CITATION_VALIDATOR] ✓ done (%.1fs) | verified=%d | used=%d | missing=%d | errors=%d | warns=%d | → review",
        elapsed, len(verified_set), provisions_used, provisions_missing, error_count, warn_count,
    )
    return Command(update={"citation_issues": issues}, goto="review")
