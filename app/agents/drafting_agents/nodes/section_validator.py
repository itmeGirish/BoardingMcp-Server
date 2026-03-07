"""Section Validator Node — deterministic (NO LLM).

3-layer validation per section:
  Layer A: Entity Extractor (dates, amounts, references, names)
  Layer B: Evidence Anchoring Gate (2-tier: token replacement + claim flagging)
  Layer C: Claim Ledger Cross-Check

Pipeline position: section_drafter → **section_validator** → assembler
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from langgraph.types import Command

from ....config import logger
from ..states import DraftingState
from ._utils import _as_dict

# Load placeholder registry
_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "config" / "placeholder_registry.json"
_PLACEHOLDER_REGISTRY: Dict[str, Any] = {}
try:
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        _PLACEHOLDER_REGISTRY = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    pass

# Build alias → canonical map
_ALIAS_MAP: Dict[str, str] = {}
for canonical, info in _PLACEHOLDER_REGISTRY.get("placeholders", {}).items():
    _ALIAS_MAP[canonical.lower()] = canonical
    for alias in info.get("aliases", []):
        _ALIAS_MAP[alias.lower()] = canonical

# Claim types allowed without evidence (legal conclusions, not factual assertions)
_ALLOWED_WITHOUT_EVIDENCE: Set[str] = {
    "breach", "no_benefit", "failure_of_consideration", "continuing_cause",
}

# Claim types that REQUIRE evidence
_REQUIRES_EVIDENCE: Set[str] = {
    "payment", "agreement", "notice", "admission", "receipt",
    "acknowledgment", "confession", "demand", "delivery",
}

# ---------------------------------------------------------------------------
# Layer A: Entity Extractors
# ---------------------------------------------------------------------------

# Date patterns (multi-format Indian dates)
_RE_DATE_FORMATS = [
    # DD.MM.YYYY or DD/MM/YYYY or DD-MM-YYYY
    re.compile(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})\b"),
    # DDth Month YYYY
    re.compile(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
        r"(\d{4})\b",
        re.IGNORECASE,
    ),
    # Month DD, YYYY
    re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
        r"(\d{1,2}),?\s+(\d{4})\b",
        re.IGNORECASE,
    ),
]

# Exclusion patterns — NOT dates/amounts
_RE_SECTION_NUM = re.compile(r"Section\s+\d+[A-Z]?", re.IGNORECASE)
_RE_ARTICLE_NUM = re.compile(r"Article\s+\d+", re.IGNORECASE)
_RE_PARA_REF = re.compile(r"para(?:graph)?\s+\d+", re.IGNORECASE)
_RE_ORDER_RULE = re.compile(r"Order\s+[IVXLCDM]+\s+Rule\s+\d+", re.IGNORECASE)
_RE_CASE_NUM = re.compile(r"O\.?S\.?\s*No\.?\s*\d+", re.IGNORECASE)

# Amount patterns
_RE_AMOUNT_RS = re.compile(
    r"(?:Rs\.?\s*|₹\s*)([\d,]+(?:\.\d{1,2})?)\s*/?\-?",
    re.IGNORECASE,
)
_RE_AMOUNT_WORDS = re.compile(
    r"(?:Rupees|Rs\.?)\s+([\w\s]+?)\s+(?:Only|Lakhs?|Crores?)",
    re.IGNORECASE,
)
_RE_AMOUNT_LAKH = re.compile(
    r"(?:Rs\.?\s*|₹\s*)([\d.]+)\s*(?:lakh|lac)s?",
    re.IGNORECASE,
)

# Period patterns (NOT amounts)
_RE_PERIOD = re.compile(r"\b\d+\s+(?:years?|months?|days?)\b", re.IGNORECASE)
_RE_PERCENTAGE = re.compile(r"\b\d+(?:\.\d+)?%", re.IGNORECASE)

# Reference number patterns (keyword-aware)
_RE_CHEQUE = re.compile(r"cheque\s+(?:no\.?\s*|number\s*|#\s*)(\w+)", re.IGNORECASE)
_RE_UTR = re.compile(r"UTR[:\s]+(\w+)", re.IGNORECASE)
_RE_NEFT = re.compile(r"NEFT\s+(?:Ref\.?\s*|reference\s*)(\w+)", re.IGNORECASE)
_RE_RECEIPT = re.compile(r"Receipt\s+(?:No\.?\s*|number\s*)(\w+)", re.IGNORECASE)
_RE_FIR = re.compile(r"FIR\s+(?:No\.?\s*)(\d+/\d+)", re.IGNORECASE)

# Case citation patterns (hallucination detector)
_RE_CASE_CITATION = re.compile(
    r"\b(?:\d{4}\s+)?(?:AIR|SCC|ILR|All\s+ER|MLJ|KLT|Bom\s+LR)\b",
    re.IGNORECASE,
)


def _is_excluded_context(text: str, pos: int) -> bool:
    """Check if a number at position is in an excluded context (Section, Article, etc.)."""
    # Get surrounding context
    start = max(0, pos - 30)
    context = text[start:pos + 20]
    return bool(
        _RE_SECTION_NUM.search(context)
        or _RE_ARTICLE_NUM.search(context)
        or _RE_PARA_REF.search(context)
        or _RE_ORDER_RULE.search(context)
        or _RE_CASE_NUM.search(context)
    )


def _extract_dates(text: str) -> List[Dict[str, Any]]:
    """Extract all dates from text, excluding Section/Article numbers."""
    dates: List[Dict[str, Any]] = []
    for pattern in _RE_DATE_FORMATS:
        for m in pattern.finditer(text):
            if not _is_excluded_context(text, m.start()):
                dates.append({
                    "type": "date",
                    "raw": m.group(),
                    "position": m.start(),
                })
    return dates


def _parse_indian_amount(raw: str) -> Optional[float]:
    """Parse Indian-format amount string to float."""
    cleaned = raw.replace(",", "").replace("/-", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_amounts(text: str) -> List[Dict[str, Any]]:
    """Extract all currency amounts, excluding periods and percentages."""
    amounts: List[Dict[str, Any]] = []

    for m in _RE_AMOUNT_RS.finditer(text):
        if _is_excluded_context(text, m.start()):
            continue
        val = _parse_indian_amount(m.group(1))
        if val and val > 0:
            amounts.append({"type": "amount", "raw": m.group(), "value": val, "position": m.start()})

    for m in _RE_AMOUNT_LAKH.finditer(text):
        if _is_excluded_context(text, m.start()):
            continue
        try:
            val = float(m.group(1)) * 100000
            amounts.append({"type": "amount", "raw": m.group(), "value": val, "position": m.start()})
        except ValueError:
            pass

    return amounts


def _extract_references(text: str) -> List[Dict[str, Any]]:
    """Extract reference numbers (cheque, UTR, NEFT, receipt, FIR) by keywords."""
    refs: List[Dict[str, Any]] = []
    for pattern, subtype in [
        (_RE_CHEQUE, "cheque"), (_RE_UTR, "utr"), (_RE_NEFT, "neft"),
        (_RE_RECEIPT, "receipt"), (_RE_FIR, "fir"),
    ]:
        for m in pattern.finditer(text):
            refs.append({
                "type": "reference",
                "subtype": subtype,
                "value": m.group(1),
                "raw": m.group(),
                "position": m.start(),
            })
    return refs


def _extract_citations(text: str) -> List[Dict[str, Any]]:
    """Detect case law citation patterns (AIR/SCC/ILR)."""
    citations: List[Dict[str, Any]] = []
    for m in _RE_CASE_CITATION.finditer(text):
        citations.append({
            "type": "citation",
            "raw": m.group(),
            "position": m.start(),
        })
    return citations


# ---------------------------------------------------------------------------
# Layer B: Evidence Anchoring
# ---------------------------------------------------------------------------

def _get_intake_dates(intake: Dict[str, Any]) -> Set[str]:
    """Collect all known dates from intake."""
    dates: Set[str] = set()
    facts = intake.get("facts", {})
    if isinstance(facts, dict):
        coa = facts.get("cause_of_action_date")
        if coa:
            dates.add(coa)
        for item in facts.get("chronology", []):
            if isinstance(item, dict) and item.get("date"):
                dates.add(item["date"])
    # Slots
    dynamic = intake.get("dynamic_fields", {})
    if isinstance(dynamic, dict):
        for slot in dynamic.get("slots", []):
            if isinstance(slot, dict) and slot.get("type") == "date" and slot.get("value"):
                dates.add(str(slot["value"]))
    return dates


def _get_intake_amounts(intake: Dict[str, Any]) -> Set[float]:
    """Collect all known amounts from intake — expanded mining."""
    amounts: Set[float] = set()
    facts = intake.get("facts", {})
    if isinstance(facts, dict):
        amt = facts.get("amounts", {})
        if isinstance(amt, dict):
            for val in amt.values():
                if isinstance(val, (int, float)) and val > 0:
                    amounts.add(float(val))
        # Mine amounts from chronology event descriptions
        for item in facts.get("chronology", []):
            if isinstance(item, dict):
                event = item.get("event", "")
                if event:
                    for a in _extract_amounts(event):
                        val = a.get("value", 0)
                        if val > 0:
                            amounts.add(val)
        # Mine amounts from summary
        summary = facts.get("summary", "")
        if summary:
            for a in _extract_amounts(summary):
                val = a.get("value", 0)
                if val > 0:
                    amounts.add(val)
    # Numeric slots from dynamic_fields
    dynamic = intake.get("dynamic_fields", {})
    if isinstance(dynamic, dict):
        for slot in dynamic.get("slots", []):
            if isinstance(slot, dict) and slot.get("type") == "number":
                try:
                    val = float(slot["value"])
                    if val > 0:
                        amounts.add(val)
                except (TypeError, ValueError):
                    pass
    return amounts


_REF_SLOT_KEYS = frozenset({
    "utr_number", "cheque_number", "fir_number", "receipt_number",
    "neft_ref", "account_number", "reference_number", "ref_number",
    "rtgs_number", "transaction_id", "case_number",
})


def _get_intake_references(intake: Dict[str, Any]) -> Set[str]:
    """Collect known reference numbers from intake — focused on actual refs."""
    refs: Set[str] = set()
    evidence = intake.get("evidence", [])
    if isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict) and item.get("ref"):
                refs.add(str(item["ref"]))
    dynamic = intake.get("dynamic_fields", {})
    if isinstance(dynamic, dict):
        for slot in dynamic.get("slots", []):
            if isinstance(slot, dict) and slot.get("value"):
                key = (slot.get("key") or "").lower().replace(" ", "_")
                if key in _REF_SLOT_KEYS:
                    refs.add(str(slot["value"]))
    return refs


# ---------------------------------------------------------------------------
# User-Request Entity Mining
# ---------------------------------------------------------------------------

def _get_user_request_amounts(user_request: str) -> Set[float]:
    """Extract amounts from raw user_request text using the same parser."""
    amounts: Set[float] = set()
    for a in _extract_amounts(user_request):
        val = a.get("value", 0)
        if val > 0:
            amounts.add(val)
    return amounts


def _get_user_request_dates(user_request: str) -> Set[str]:
    """Extract dates from raw user_request text using the same parser."""
    return {d["raw"] for d in _extract_dates(user_request)}


def _get_user_request_references(user_request: str) -> Set[str]:
    """Extract references from raw user_request text using the same parser."""
    return {r["value"] for r in _extract_references(user_request)}


def _pick_placeholder(entity_type: str, subtype: str = "") -> str:
    """Pick the best placeholder name from registry."""
    # Map entity types to placeholder names
    mapping = {
        "date": "{{DATE}}",
        "amount": "{{AMOUNT}}",
        "cheque": "{{CHEQUE_NO}}",
        "utr": "{{UTR_NUMBER}}",
        "neft": "{{UTR_NUMBER}}",
        "receipt": "{{RECEIPT_NO}}",
        "fir": "{{FIR_NO}}",
    }
    return mapping.get(subtype) or mapping.get(entity_type, "{{MISSING_DETAIL}}")


def _anchor_entities(
    text: str,
    dates: List[Dict[str, Any]],
    amounts: List[Dict[str, Any]],
    references: List[Dict[str, Any]],
    intake: Dict[str, Any],
    user_request: str = "",
) -> Tuple[str, List[Dict[str, Any]]]:
    """Tier A: Replace unsupported tokens with placeholders. Returns (corrected_text, issues)."""
    issues: List[Dict[str, Any]] = []
    intake_dates = _get_intake_dates(intake)
    intake_amounts = _get_intake_amounts(intake)
    intake_refs = _get_intake_references(intake)

    # Expand with user-request-sourced entities (scalable — works for any scenario)
    if user_request:
        intake_amounts |= _get_user_request_amounts(user_request)
        intake_dates |= _get_user_request_dates(user_request)
        intake_refs |= _get_user_request_references(user_request)

    # Collect replacements (process in reverse order to preserve positions)
    replacements: List[Tuple[int, int, str, str, str]] = []  # (start, end, original, replacement, issue_type)

    # Check dates
    for d in dates:
        raw = d["raw"]
        # Check if this date matches any intake date (fuzzy: check if raw contains any known date string)
        matched = any(
            raw in known or known in raw
            for known in intake_dates
        )
        if not matched:
            placeholder = "{{DATE}}"
            replacements.append((d["position"], d["position"] + len(raw), raw, placeholder, "unsupported_date"))

    # Check amounts
    for a in amounts:
        val = a.get("value", 0)
        matched = any(abs(val - known) < 1.0 for known in intake_amounts)
        if not matched:
            placeholder = "{{AMOUNT}}"
            replacements.append((a["position"], a["position"] + len(a["raw"]), a["raw"], placeholder, "unsupported_amount"))

    # Check references
    for r in references:
        matched = r["value"] in intake_refs
        if not matched:
            placeholder = _pick_placeholder("reference", r.get("subtype", ""))
            replacements.append((r["position"], r["position"] + len(r["raw"]), r["raw"], placeholder, "unsupported_reference"))

    # Apply replacements in reverse order
    corrected = text
    for start, end, original, replacement, issue_type in sorted(replacements, key=lambda x: x[0], reverse=True):
        corrected = corrected[:start] + replacement + corrected[end:]
        issues.append({
            "issue_type": issue_type,
            "description": f"Unsupported {issue_type.replace('unsupported_', '')}: {original}",
            "original": original,
            "replacement": replacement,
            "severity": "replaced",
        })

    return corrected, issues


def _flag_unsupported_claims(
    claims: List[Dict[str, Any]],
    intake: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Tier B: Flag claims that require evidence but have none."""
    issues: List[Dict[str, Any]] = []

    for claim in claims:
        claim_type = claim.get("claim_type", "")
        evidence_refs = claim.get("evidence_refs", [])

        if claim_type in _REQUIRES_EVIDENCE and not evidence_refs:
            issues.append({
                "issue_type": "unsupported_claim",
                "description": f"Claim type '{claim_type}' requires evidence but has no evidence_refs",
                "original": json.dumps(claim),
                "replacement": f"[[UNSUPPORTED_CLAIM: {claim_type}]]",
                "severity": "flagged",
            })

    return issues


# ---------------------------------------------------------------------------
# Layer C: Claim Ledger Cross-Check
# ---------------------------------------------------------------------------

def _cross_check_claims(
    text: str,
    claims: List[Dict[str, Any]],
    intake: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Check claim ledger consistency against text and intake."""
    issues: List[Dict[str, Any]] = []

    for claim in claims:
        claim_type = claim.get("claim_type", "")
        evidence_refs = claim.get("evidence_refs", [])

        # Check: claim requires evidence and has none (and is not an allowed type)
        if (
            claim_type not in _ALLOWED_WITHOUT_EVIDENCE
            and not evidence_refs
            and claim_type in _REQUIRES_EVIDENCE
        ):
            issues.append({
                "issue_type": "unsupported_claim",
                "description": f"Claim '{claim_type}' has no evidence reference",
                "original": claim_type,
                "severity": "warning",
            })

    return issues


# ---------------------------------------------------------------------------
# Citation check
# ---------------------------------------------------------------------------

def _check_citations(text: str) -> List[Dict[str, Any]]:
    """Flag any case law citation patterns (AIR/SCC/ILR) as potentially fabricated."""
    issues: List[Dict[str, Any]] = []
    citations = _extract_citations(text)
    for c in citations:
        issues.append({
            "issue_type": "unsupported_reference",
            "description": f"Case citation pattern detected: {c['raw']} — may be fabricated",
            "original": c["raw"],
            "severity": "flagged",
        })
    return issues


# ---------------------------------------------------------------------------
# Layer D: Drafting Quality Checks
# ---------------------------------------------------------------------------

# Skeleton detection: sentences that are bare conclusions without factual detail
_RE_SKELETON_SENTENCES = [
    re.compile(p, re.IGNORECASE) for p in [
        # Bare conclusion sentences (< 15 words, ends with period)
        r"^(?:The\s+)?[Dd]efendant\s+(?:has\s+)?failed\.?\s*$",
        r"^(?:The\s+)?[Tt]ransaction\s+failed\.?\s*$",
        r"^(?:The\s+)?[Cc]onsideration\s+failed\.?\s*$",
        r"^(?:The\s+)?[Dd]efendant\s+(?:has\s+)?defaulted\.?\s*$",
        r"^(?:The\s+)?[Dd]efendant\s+(?:has\s+)?breached\.?\s*$",
    ]
]

# Drafting-notes language that must never appear in a filed document
_RE_DRAFTING_NOTES = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bto\s+be\s+verif(?:ied|y)\b",
        r"\bplaceholder\b(?!\s*})",  # "placeholder" but not inside {{PLACEHOLDER}}
        r"\bto\s+be\s+enter(?:ed|ing)\b",
        r"\bto\s+be\s+calculat(?:ed|ing)\b",
        r"\bas\s+per\s+records?\b",
        r"\bdetails?\s+to\s+follow\b",
        r"\binsert\s+(?:here|date|name|amount)\b",
        r"\b(?:TBD|TBC|TODO)\b",
    ]
]


def _check_drafting_quality(
    text: str,
    section_id: str,
) -> List[Dict[str, Any]]:
    """Check for skeleton sentences and drafting-notes language.

    These are quality issues flagged for retry, not evidence issues.
    """
    issues: List[Dict[str, Any]] = []

    # Only check LLM-generated content sections
    if section_id in ("court_heading", "title", "verification", "advocate"):
        return issues

    # Check for skeleton sentences (bare conclusions without factual detail)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("{{"):
            continue
        for pattern in _RE_SKELETON_SENTENCES:
            if pattern.match(stripped):
                issues.append({
                    "issue_type": "skeleton_sentence",
                    "description": f"Bare conclusion without factual detail: '{stripped}' — rewrite with specifics (who, what, when, how)",
                    "original": stripped,
                    "severity": "warning",
                })

    # Check for drafting-notes language
    for pattern in _RE_DRAFTING_NOTES:
        for m in pattern.finditer(text):
            issues.append({
                "issue_type": "drafting_notes_language",
                "description": f"Drafting-notes language: '{m.group()}' — must not appear in filed document",
                "original": m.group(),
                "severity": "warning",
            })

    # Check minimum sentence count for narrative sections
    # Facts section should have at least 4 substantive sentences
    if section_id == "facts":
        sentences = [s.strip() for s in re.split(r"[.!?]\s+", text) if len(s.strip()) > 20]
        if len(sentences) < 4:
            issues.append({
                "issue_type": "insufficient_narrative",
                "description": f"Facts section has only {len(sentences)} substantive sentences — minimum 4 needed for narrative quality",
                "original": f"{len(sentences)} sentences found",
                "severity": "warning",
            })

    # Check for "and/or" usage
    and_or_count = len(re.findall(r"\band/or\b", text, re.IGNORECASE))
    if and_or_count > 0:
        issues.append({
            "issue_type": "and_or_usage",
            "description": f"'and/or' used {and_or_count} time(s) — use 'and' or 'or' instead",
            "original": "and/or",
            "severity": "warning",
        })

    return issues


# ---------------------------------------------------------------------------
# Main Validator
# ---------------------------------------------------------------------------

def _validate_section(
    filled: Dict[str, Any],
    intake: Dict[str, Any],
    user_request: str = "",
) -> Dict[str, Any]:
    """Run 3-layer validation on a single filled section."""
    sid = filled.get("section_id", "?")
    text = filled.get("text", "")
    stype = filled.get("type", "template")
    claims = filled.get("claims", [])

    # Skip validation for pure template sections
    if stype == "template":
        return filled

    all_issues: List[Dict[str, Any]] = []

    # Layer A: Entity extraction
    dates = _extract_dates(text)
    amounts = _extract_amounts(text)
    references = _extract_references(text)
    entities_found = len(dates) + len(amounts) + len(references)

    # Layer B Tier A: Evidence anchoring (token replacement)
    corrected_text, anchor_issues = _anchor_entities(text, dates, amounts, references, intake, user_request)
    all_issues.extend(anchor_issues)
    entities_replaced = len(anchor_issues)
    entities_anchored = entities_found - entities_replaced

    # Layer B Tier B: Claim flagging
    claim_flag_issues = _flag_unsupported_claims(claims, intake)
    all_issues.extend(claim_flag_issues)

    # Layer C: Claim ledger cross-check
    cross_issues = _cross_check_claims(corrected_text, claims, intake)
    all_issues.extend(cross_issues)

    # Citation check
    citation_issues = _check_citations(corrected_text)
    all_issues.extend(citation_issues)

    # Layer D: Drafting quality checks
    quality_issues = _check_drafting_quality(corrected_text, sid)
    all_issues.extend(quality_issues)

    logger.info(
        "[SECTION_VALIDATOR] %s: entities=%d | anchored=%d | replaced=%d | claims_flagged=%d | citations=%d | quality=%d",
        sid, entities_found, entities_anchored, entities_replaced,
        len(claim_flag_issues), len(citation_issues), len(quality_issues),
    )

    filled["text"] = corrected_text
    filled["validation_issues"] = all_issues
    return filled


def section_validator_node(state: DraftingState) -> Command:
    """Validate all filled sections. Deterministic — no LLM calls."""
    logger.info("[SECTION_VALIDATOR] ▶ start")
    t0 = time.perf_counter()

    filled_sections = state.get("filled_sections", [])
    if not filled_sections:
        logger.error("[SECTION_VALIDATOR] no filled_sections in state")
        return Command(goto="draft")

    intake = _as_dict(state.get("intake"))
    user_request = (state.get("user_request") or "").strip()

    validated: List[Dict[str, Any]] = []
    total_issues = 0
    total_replaced = 0

    for filled in filled_sections:
        if isinstance(filled, dict):
            result = _validate_section(filled, intake, user_request)
            validated.append(result)
            issues = result.get("validation_issues", [])
            total_issues += len(issues)
            total_replaced += sum(1 for i in issues if i.get("severity") == "replaced")

    elapsed = time.perf_counter() - t0
    logger.info(
        "[SECTION_VALIDATOR] ✓ done (%.1fs) | sections=%d | issues=%d | replacements=%d",
        elapsed, len(validated), total_issues, total_replaced,
    )

    return Command(
        update={"filled_sections": validated},
        goto="assembler",
    )
