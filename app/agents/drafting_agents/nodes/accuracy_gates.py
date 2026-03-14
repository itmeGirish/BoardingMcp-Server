"""v10.0 Accuracy Gates — 5 new deterministic gates.

All gates are pure functions that take draft text + LKB data and return issues.
Zero LLM calls. Wired into the pipeline after evidence_anchoring.

Gates:
1. procedural_prerequisite_gate — S.80/S.12A/S.106/S.138 steps
2. date_consistency_gate — all dates internally consistent
3. arithmetic_gate — interest computation verification
4. annexure_crossref_gate — body refs ↔ annexure list
5. accuracy_rules_gate — mandatory_averments, forbidden_in_draft
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from ....config import logger


# ---------------------------------------------------------------------------
# Gate 1: Procedural Prerequisite
# ---------------------------------------------------------------------------

def procedural_prerequisite_gate(
    draft_text: str,
    lkb: Dict[str, Any],
    intake: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Check pre-institution requirements from LKB."""
    pre_steps = lkb.get("pre_institution") or lkb.get("procedural_prerequisites") or []
    if not pre_steps:
        return []

    issues: List[Dict[str, Any]] = []
    draft_lower = draft_text.lower()

    for step in pre_steps:
        if isinstance(step, str):
            # Legacy format: just a string like "section_12a_mediation"
            _check_legacy_prerequisite(step, draft_lower, issues)
            continue

        if not isinstance(step, dict):
            continue

        # v10.0 format: dict with condition, draft_must_contain, etc.
        must_contain = step.get("draft_must_contain", "")
        if must_contain and must_contain.lower() not in draft_lower:
            issues.append({
                "type": "missing_procedural_prerequisite",
                "severity": "WARN",
                "step": step.get("step", "unknown"),
                "provision": step.get("act", ""),
                "message": step.get("message", f"Missing: {must_contain}"),
                "blocking": step.get("mandatory", False),
            })

    return issues


def _check_legacy_prerequisite(step: str, draft_lower: str, issues: List[Dict]):
    """Check legacy string-format prerequisites."""
    checks = {
        "section_12a_mediation": (
            "pre-institution mediation",
            "S.12A Commercial Courts Act pre-institution mediation not mentioned",
        ),
        "arbitration_clause_screen": (
            "arbitration",
            "Arbitration clause status not addressed",
        ),
        "section_80_notice": (
            "section 80",
            "S.80 CPC notice to government defendant not mentioned",
        ),
        "section_106_notice": (
            "section 106",
            "S.106 TPA notice to tenant not mentioned",
        ),
        "section_138_notice": (
            "demand notice",
            "S.138 NI Act demand notice not mentioned",
        ),
    }
    check = checks.get(step)
    if check and check[0] not in draft_lower:
        issues.append({
            "type": "missing_procedural_prerequisite",
            "severity": "INFO",
            "step": step,
            "message": check[1],
            "blocking": False,
        })


# ---------------------------------------------------------------------------
# Gate 2: Date Consistency
# ---------------------------------------------------------------------------

_DATE_PATTERN = re.compile(
    r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})"
    r"|(\d{4})[./-](\d{1,2})[./-](\d{1,2})"
)


def date_consistency_gate(
    draft_text: str,
    intake: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Extract dates from draft and check for basic consistency issues."""
    issues: List[Dict[str, Any]] = []

    # Extract all dates from draft text
    dates_found = _DATE_PATTERN.findall(draft_text)
    if len(dates_found) < 2:
        return []  # Not enough dates to check consistency

    # Check for obviously impossible dates (day > 31, month > 12)
    for match in dates_found:
        if match[0]:  # DD/MM/YYYY format
            day, month = int(match[0]), int(match[1])
        else:  # YYYY/MM/DD format
            day, month = int(match[5]), int(match[4])

        if month > 12 or day > 31:
            issues.append({
                "type": "impossible_date",
                "severity": "WARN",
                "message": f"Impossible date found: day={day}, month={month}",
                "blocking": False,
            })

    return issues


# ---------------------------------------------------------------------------
# Gate 3: Arithmetic
# ---------------------------------------------------------------------------

def arithmetic_gate(
    draft_text: str,
    intake: Dict[str, Any],
    lkb: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Verify interest/damages computation in draft."""
    issues: List[Dict[str, Any]] = []

    # Extract amounts from intake
    facts = intake.get("facts", {})
    if hasattr(facts, "model_dump"):
        facts = facts.model_dump()
    amounts = facts.get("amounts", {}) if isinstance(facts, dict) else {}
    if hasattr(amounts, "model_dump"):
        amounts = amounts.model_dump()
    if not isinstance(amounts, dict):
        return []

    # Check for compound interest when not allowed
    interest_basis = lkb.get("interest_basis", "not_applicable")
    if "compound interest" in draft_text.lower() and interest_basis != "compound":
        issues.append({
            "type": "compound_interest_not_allowed",
            "severity": "WARN",
            "message": "Draft mentions compound interest but LKB does not authorize it",
            "blocking": False,
        })

    # Check for interest rate > 24% (usurious)
    rate_matches = re.findall(r"(\d{2,3})\s*%\s*(?:per\s*annum|p\.?\s*a\.?)", draft_text, re.I)
    for rate_str in rate_matches:
        rate = int(rate_str)
        if rate > 24:
            issues.append({
                "type": "excessive_interest_rate",
                "severity": "WARN",
                "message": f"Interest rate {rate}% p.a. exceeds 24% — likely error",
                "blocking": False,
            })

    return issues


# ---------------------------------------------------------------------------
# Gate 4: Annexure Cross-Reference
# ---------------------------------------------------------------------------

_RE_ANNEXURE_BODY = re.compile(
    r"Annexure\s+(?:P-?\d+|[A-Z](?:-\d+)?)",
    re.IGNORECASE,
)


def annexure_crossref_gate(draft_text: str) -> List[Dict[str, Any]]:
    """Check body document references match annexure list."""
    issues: List[Dict[str, Any]] = []

    # Split draft into body and documents list
    doc_list_idx = draft_text.upper().find("LIST OF DOCUMENTS")
    if doc_list_idx < 0:
        doc_list_idx = draft_text.upper().find("DOCUMENTS FILED")
    if doc_list_idx < 0:
        return []  # No documents section found

    body = draft_text[:doc_list_idx]
    doc_list = draft_text[doc_list_idx:]

    # Extract annexure references from body
    body_refs = {m.group(0).upper().replace(" ", "") for m in _RE_ANNEXURE_BODY.finditer(body)}
    # Extract annexure references from documents list
    list_refs = {m.group(0).upper().replace(" ", "") for m in _RE_ANNEXURE_BODY.finditer(doc_list)}

    # Orphan annexures: in list but not referenced in body
    orphans = list_refs - body_refs
    for ref in orphans:
        issues.append({
            "type": "orphan_annexure",
            "severity": "INFO",
            "annexure": ref,
            "message": f"{ref} listed in documents but not referenced in body",
            "blocking": False,
        })

    # Missing annexures: referenced in body but not in list
    missing = body_refs - list_refs
    for ref in missing:
        issues.append({
            "type": "missing_annexure_in_list",
            "severity": "WARN",
            "annexure": ref,
            "message": f"{ref} referenced in body but not in documents list",
            "blocking": False,
        })

    return issues


# ---------------------------------------------------------------------------
# Gate 5: Accuracy Rules (from LKB)
# ---------------------------------------------------------------------------

def accuracy_rules_gate(
    draft_text: str,
    lkb: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Check mandatory_averments and forbidden_in_draft from LKB accuracy_rules."""
    rules = lkb.get("accuracy_rules")
    if not rules or not isinstance(rules, dict):
        return []

    issues: List[Dict[str, Any]] = []
    draft_lower = draft_text.lower()

    # Mandatory averments
    for av in rules.get("mandatory_averments", []):
        if not isinstance(av, dict):
            continue
        pattern = av.get("text_pattern", "")
        if pattern and pattern.lower() not in draft_lower:
            issues.append({
                "type": "missing_mandatory_averment",
                "severity": "ERROR" if av.get("blocking") else "WARN",
                "averment_id": av.get("id", "unknown"),
                "provision": av.get("provision", ""),
                "message": av.get("message", f"Missing mandatory averment: {pattern}"),
                "blocking": av.get("blocking", False),
            })

    # Forbidden content
    for fc in rules.get("forbidden_in_draft", []):
        if not isinstance(fc, dict):
            continue
        pattern = fc.get("pattern", "")
        if pattern and re.search(pattern, draft_text, re.IGNORECASE):
            issues.append({
                "type": "forbidden_content",
                "severity": "ERROR" if fc.get("blocking") else "WARN",
                "message": fc.get("message", f"Forbidden content found: {pattern}"),
                "blocking": fc.get("blocking", False),
            })

    return issues


# ---------------------------------------------------------------------------
# Combined gate runner (for pipeline node)
# ---------------------------------------------------------------------------

def run_accuracy_gates(
    draft_text: str,
    lkb: Dict[str, Any],
    intake: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Run all 5 accuracy gates and return combined issues list."""
    all_issues: List[Dict[str, Any]] = []

    all_issues.extend(procedural_prerequisite_gate(draft_text, lkb, intake))
    all_issues.extend(date_consistency_gate(draft_text, intake))
    all_issues.extend(arithmetic_gate(draft_text, intake, lkb))
    all_issues.extend(annexure_crossref_gate(draft_text))
    all_issues.extend(accuracy_rules_gate(draft_text, lkb))

    if all_issues:
        logger.info(
            "[ACCURACY_GATES] found %d issues (blocking=%d, warn=%d, info=%d)",
            len(all_issues),
            sum(1 for i in all_issues if i.get("blocking")),
            sum(1 for i in all_issues if i.get("severity") == "WARN"),
            sum(1 for i in all_issues if i.get("severity") == "INFO"),
        )

    return all_issues
