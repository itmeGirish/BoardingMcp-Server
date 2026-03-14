"""LKB Compliance Gate — verifies draft followed LKB instructions.

Deterministic checks (no LLM):
1. Did the draft cite the primary Acts from LKB?
2. Did the draft use the correct limitation article?
3. Did the draft use the correct court format?
4. Did the draft include all damages categories (for damages suits)?

Issues found are added to postprocess_issues for review to act on.
This node runs AFTER assembler, BEFORE postprocess.

Pipeline position: assembler → evidence_anchoring → **lkb_compliance** → postprocess
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List

from langgraph.types import Command

from ....config import logger
from ..lkb.limitation import get_limitation_reference_details, normalize_coa_type
from ..states import DraftingState
from ._utils import _as_dict


def _check_acts_cited(draft_text: str, lkb_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check if primary Acts from LKB are cited in the draft."""
    issues = []
    primary_acts = lkb_brief.get("primary_acts", [])
    for act_info in primary_acts:
        act_name = act_info.get("act", "")
        if not act_name:
            continue
        # Check for act name (fuzzy — allow minor variations)
        act_pattern = re.escape(act_name).replace(r",\ ", r",?\s*").replace(r"\ ", r"\s+")
        if not re.search(act_pattern, draft_text, re.IGNORECASE):
            # Try shorter match (just the act name without year)
            short_name = re.sub(r",?\s*\d{4}$", "", act_name).strip()
            if short_name and not re.search(re.escape(short_name), draft_text, re.IGNORECASE):
                issues.append({
                    "type": "lkb_act_missing",
                    "severity": "legal",
                    "issue": f"LKB primary Act not cited: {act_name}",
                    "fix": f"Add reference to {act_name} with sections {act_info.get('sections', [])}",
                })
    return issues


def _check_limitation_article(draft_text: str, lkb_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check if the correct limitation citation from LKB is in the draft."""
    issues = []
    lim = lkb_brief.get("limitation", {})
    details = get_limitation_reference_details(lim)
    if not details["requires_citation"]:
        return issues

    short_ref = details["short_citation"]
    full_ref = details["citation"]
    draft_text_lower = draft_text.lower()

    if details["kind"] == "limitation_article":
        article_number = str(details["article"])
        article_pattern = rf"Article\s+{re.escape(article_number)}\b"
        if re.search(article_pattern, draft_text, re.IGNORECASE):
            return issues
        wrong_articles = re.findall(r"Article\s+(\d+[A-Za-z]?(?:\([A-Za-z0-9]+\))?)", draft_text, re.IGNORECASE)
        wrong = [a for a in wrong_articles if a.lower() != article_number.lower()]
        issue_text = f"LKB requires {short_ref} but draft"
        if wrong:
            issue_text += f" cites Article {', '.join(wrong)} instead"
        else:
            issue_text += " does not cite the required limitation article"
    else:
        if short_ref.lower() in draft_text_lower or full_ref.lower() in draft_text_lower:
            return issues
        issue_text = f"LKB requires '{full_ref}' but draft does not cite that limitation reference"

    issues.append({
        "type": "lkb_limitation_wrong",
        "severity": "legal",
        "issue": issue_text,
        "fix": f"Use {full_ref}. Period: {lim.get('period', '')}",
    })
    return issues


def _check_court_format(draft_text: str, lkb_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check if the correct court format from LKB is used."""
    issues = []
    detected_court = lkb_brief.get("detected_court", {})
    if not detected_court:
        return issues

    court_format = detected_court.get("format", "")
    court_name = detected_court.get("court", "")

    if not court_format:
        return issues

    # Check if the correct format appears
    if court_format and court_format not in draft_text:
        # Check if wrong format is used
        wrong_format = None
        if "Commercial Suit" in court_format and "O.S. No." in draft_text:
            wrong_format = "O.S. No."
        elif "O.S. No." in court_format and "Commercial Suit" in draft_text:
            wrong_format = "Commercial Suit No."

        issue_text = f"LKB requires '{court_format}' format"
        if wrong_format:
            issue_text += f" but draft uses '{wrong_format}'"

        issues.append({
            "type": "lkb_court_format_wrong",
            "severity": "legal",
            "issue": issue_text,
            "fix": f"Use {court_format} format. Court: {court_name}",
        })

    # Check for mandatory procedural requirements
    proc = detected_court.get("procedural", [])
    for req in proc:
        # Check if key terms from each requirement appear in draft
        key_terms = re.findall(r"Section\s+\d+[A-Z]?", req)
        for term in key_terms:
            if term.lower() not in draft_text.lower():
                issues.append({
                    "type": "lkb_procedural_missing",
                    "severity": "legal",
                    "issue": f"Mandatory procedural requirement not addressed: {req}",
                    "fix": f"Add compliance statement for: {req}",
                })
                break  # One issue per requirement

    return issues


def _check_damages_categories(draft_text: str, lkb_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check if damages categories from LKB are addressed in prayer."""
    issues = []
    damages = lkb_brief.get("damages_categories", [])
    if not damages:
        return issues

    # Extract prayer section (look for "PRAYER" heading)
    prayer_match = re.search(r"(?:PRAYER|prayer)(.*?)(?:AND FOR THIS|VERIFICATION|LIST OF DOCUMENTS)", draft_text, re.DOTALL | re.IGNORECASE)
    prayer_text = prayer_match.group(1) if prayer_match else draft_text[-2000:]  # fallback: last 2000 chars

    missing = []
    for d in damages:
        # Convert category to search terms
        terms = d.replace("_", " ").lower().split()
        # Check if at least one key term appears in prayer
        found = any(term in prayer_text.lower() for term in terms if len(term) > 3)
        if not found:
            missing.append(d.replace("_", " ").title())

    if missing and len(missing) > len(damages) // 2:
        issues.append({
            "type": "lkb_damages_incomplete",
            "severity": "legal",
            "issue": f"Missing damages categories in prayer: {', '.join(missing)}",
            "fix": f"Add separate prayer items for each: {', '.join(missing)}",
        })
    return issues


def _check_superseded_acts(draft_text: str) -> List[Dict[str, Any]]:
    """Check if the draft cites any superseded/repealed Acts — FATAL error."""
    from ..lkb import SUPERSEDED_ACTS, get_current_act
    issues = []
    for old_act in SUPERSEDED_ACTS:
        if "," not in old_act:
            continue  # skip duplicates without comma
        pattern = re.escape(old_act).replace(r",\ ", r",?\s*").replace(r"\ ", r"\s+")
        matches = list(re.finditer(pattern, draft_text, re.IGNORECASE))
        if matches:
            current = get_current_act(old_act)
            issues.append({
                "type": "lkb_superseded_act",
                "severity": "blocking",
                "issue": f"REPEALED Act cited: '{old_act}' — was replaced by '{current}'",
                "fix": f"Replace ALL references to '{old_act}' with '{current}' or remove if not applicable",
            })
    return issues


def _check_coa_type(draft_text: str, lkb_brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check if cause of action matches the LKB-specified type."""
    issues = []
    coa_type = normalize_coa_type(lkb_brief.get("coa_type", ""))
    if not coa_type:
        return issues

    section_text = draft_text
    match = re.search(
        r"(?is)\bCAUSE OF ACTION\b(.*?)(?:\n[A-Z][A-Z\s/&(),.-]{2,}\n|\Z)",
        draft_text,
    )
    if match:
        section_text = match.group(1)

    t = section_text.lower()
    if coa_type == "single_event":
        # Single event breach should NOT have "continuing cause" / "continuing breach"
        continuing_patterns = [
            r"continuing\s+(?:cause\s+of\s+action|breach|to\s+breach)",
            r"cause\s+of\s+action\s+is\s+(?:a\s+)?continuing",
            r"continues\s+to\s+(?:this\s+day|date|wrongfully)",
        ]
        for pat in continuing_patterns:
            if re.search(pat, t):
                issues.append({
                    "type": "lkb_coa_type_wrong",
                    "severity": "legal",
                    "issue": "Draft incorrectly pleads 'continuing cause of action' for a SINGLE EVENT breach",
                    "fix": "Remove 'continuing' language. The breach was a single event. Write: 'The cause of action arose on [DATE] when the Defendant [breached/terminated].' The LOSS continues, not the breach.",
                })
                break
    return issues


def _fix_superseded_acts_in_text(draft_text: str) -> tuple:
    """Deterministic text replacement: replace superseded act names with current ones.

    Returns (fixed_text, replacements_count).
    """
    from ..lkb import SUPERSEDED_ACTS, get_current_act
    fixed = draft_text
    count = 0
    for old_act in SUPERSEDED_ACTS:
        if "," not in old_act:
            continue
        pattern = re.compile(
            re.escape(old_act).replace(r",\ ", r",?\s*").replace(r"\ ", r"\s+"),
            re.IGNORECASE,
        )
        if pattern.search(fixed):
            current = get_current_act(old_act)
            fixed = pattern.sub(current, fixed)
            count += 1
    return fixed, count


async def lkb_compliance_node(state: DraftingState) -> Command:
    """Verify draft compliance with LKB brief. Deterministic — no LLM.

    ENFORCEMENT ACTIONS (not just detection):
    - Superseded acts → deterministic text replacement (fix in-place)
    - CoA type / acts / limitation / damages → flagged for review
    """
    logger.info("[LKB_COMPLIANCE] ▶ start")
    t0 = time.perf_counter()

    lkb_brief = _as_dict(state.get("lkb_brief"))
    if not lkb_brief:
        logger.info("[LKB_COMPLIANCE] no LKB brief — skipping")
        return Command(update={}, goto="postprocess")

    # Get draft text
    draft = _as_dict(state.get("draft"))
    artifacts = draft.get("draft_artifacts") or []
    draft_text = ""
    if artifacts:
        first = artifacts[0] if isinstance(artifacts[0], dict) else _as_dict(artifacts[0])
        draft_text = first.get("text", "")

    if not draft_text:
        logger.info("[LKB_COMPLIANCE] no draft text — skipping")
        return Command(update={}, goto="postprocess")

    # === ENFORCEMENT: Fix superseded acts in-place ===
    fixed_text, replacements = _fix_superseded_acts_in_text(draft_text)
    draft_update = None
    if replacements > 0:
        logger.info("[LKB_COMPLIANCE] FIXED %d superseded act reference(s) in draft text", replacements)
        corrected_artifact = {**artifacts[0], "text": fixed_text}
        draft_update = {"draft_artifacts": [corrected_artifact]}
        draft_text = fixed_text  # use fixed text for remaining checks

    # Run all compliance checks
    all_issues: List[Dict[str, Any]] = []
    all_issues.extend(_check_acts_cited(draft_text, lkb_brief))
    all_issues.extend(_check_limitation_article(draft_text, lkb_brief))
    all_issues.extend(_check_court_format(draft_text, lkb_brief))
    all_issues.extend(_check_damages_categories(draft_text, lkb_brief))
    all_issues.extend(_check_superseded_acts(draft_text))  # should be 0 after fix
    all_issues.extend(_check_coa_type(draft_text, lkb_brief))

    elapsed = time.perf_counter() - t0
    legal_issues = [i for i in all_issues if i.get("severity") in ("legal", "blocking")]

    logger.info(
        "[LKB_COMPLIANCE] ✓ done (%.3fs) | issues=%d | legal=%d | superseded_fixed=%d",
        elapsed, len(all_issues), len(legal_issues), replacements,
    )

    for issue in all_issues:
        logger.info(
            "[LKB_COMPLIANCE] [%s] %s → %s",
            issue.get("type", ""), issue.get("issue", ""), issue.get("fix", ""),
        )

    # Build update dict
    existing_issues = state.get("postprocess_issues") or []
    update: Dict[str, Any] = {"postprocess_issues": existing_issues + all_issues}
    if draft_update:
        update["draft"] = draft_update

    return Command(update=update, goto="postprocess")
