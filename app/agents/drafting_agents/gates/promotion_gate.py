"""
Promotion Gate  (CLAUD.md Step 15) -- Rule-based, NO LLM calls.

Evaluates candidate staging rules to determine which ones meet the
criteria for promotion to the main rule set.  Rules that are too
case-specific (contain names, dates, case numbers, addresses) or
contradict existing main rules are rejected.
"""

import re


# ---------------------------------------------------------------------------
# Promotion thresholds
# ---------------------------------------------------------------------------

MIN_OCCURRENCE_COUNT = 3
ALLOWED_SEVERITIES = frozenset(["medium", "high"])

# ---------------------------------------------------------------------------
# Patterns that indicate case-specific content (should NOT be promoted)
# ---------------------------------------------------------------------------

# Indian case number formats:  "Crl.M.C. No. 1234/2024", "W.P.(C) 5678/2023"
_CASE_NUMBER_RE = re.compile(
    r"(?:"
    r"\b(?:Crl|Civ|W\.?P|SLP|CMP|RP|MA|OA|SA|FA|WP)"  # Common prefixes
    r"[.\s()\w]*No\.?\s*\d+"                              # followed by number
    r"|"
    r"\b\d{1,6}\s*/\s*\d{4}\b"                           # bare number/year
    r")",
    re.IGNORECASE,
)

# Proper names heuristic: two or more capitalised words in a row that are
# NOT common legal terms
_COMMON_LEGAL_TERMS = frozenset([
    "high court", "supreme court", "district court", "sessions court",
    "civil court", "family court", "consumer forum", "labour court",
    "criminal appeal", "civil appeal", "writ petition",
    "special leave petition", "first information report",
    "code of criminal procedure", "code of civil procedure",
    "indian penal code", "bharatiya nyaya sanhita",
    "evidence act", "limitation act",
])

_PROPER_NAME_RE = re.compile(
    r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
)

# Date patterns:  "12/03/2024", "12-03-2024", "12 March 2024", "2024-03-12"
_DATE_RE = re.compile(
    r"(?:"
    r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b"
    r"|"
    r"\b\d{4}[/\-]\d{1,2}[/\-]\d{1,2}\b"
    r"|"
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|"
    r"August|September|October|November|December)\s+\d{4}\b"
    r")",
    re.IGNORECASE,
)

# Address patterns: PIN codes, common address markers
_ADDRESS_RE = re.compile(
    r"(?:"
    r"\b\d{6}\b"                                  # 6-digit PIN code
    r"|"
    r"\b(?:Plot|House|Flat|Door)\s*(?:No\.?|#)\s*" # House/Plot number
    r"|"
    r"\b(?:Street|Road|Lane|Nagar|Colony|Marg|"
    r"Block|Sector|Phase|Village|Tehsil|Taluk)\b"
    r")",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_case_specific(rule_content: str) -> tuple[bool, list[str]]:
    """
    Check if a rule's content contains case-specific information
    that makes it unsuitable for promotion to the main rule set.

    Returns:
        (is_specific, reasons)
    """
    reasons: list[str] = []

    if not rule_content:
        return False, reasons

    # Check for case numbers
    if _CASE_NUMBER_RE.search(rule_content):
        reasons.append("contains_case_number")

    # Check for dates
    if _DATE_RE.search(rule_content):
        reasons.append("contains_specific_date")

    # Check for addresses
    if _ADDRESS_RE.search(rule_content):
        reasons.append("contains_address")

    # Check for proper names (exclude common legal terms)
    name_matches = _PROPER_NAME_RE.findall(rule_content)
    for name in name_matches:
        if name.lower() not in _COMMON_LEGAL_TERMS:
            reasons.append(f"contains_proper_name: '{name}'")
            break  # One is enough to flag

    return len(reasons) > 0, reasons


def _is_contradictory(
    candidate_rule: dict,
    existing_rules: list[dict],
) -> tuple[bool, str | None]:
    """
    Check if a candidate rule contradicts any existing main rule.

    A contradiction is detected when:
    - Both rules target the same section_id / rule_category AND
    - Their actions are logically opposite (e.g., "include" vs "exclude",
      "required" vs "prohibited")
    """
    candidate_section = (
        candidate_rule.get("section_id", "")
        or candidate_rule.get("rule_category", "")
    ).lower().strip()
    candidate_action = (
        candidate_rule.get("action", "")
        or candidate_rule.get("rule_action", "")
    ).lower().strip()

    if not candidate_section or not candidate_action:
        return False, None

    # Opposite action pairs
    opposites = {
        "include": "exclude",
        "exclude": "include",
        "required": "prohibited",
        "prohibited": "required",
        "add": "remove",
        "remove": "add",
        "allow": "disallow",
        "disallow": "allow",
    }

    for existing in existing_rules:
        existing_section = (
            existing.get("section_id", "")
            or existing.get("rule_category", "")
        ).lower().strip()
        existing_action = (
            existing.get("action", "")
            or existing.get("rule_action", "")
        ).lower().strip()

        if existing_section == candidate_section:
            expected_opposite = opposites.get(candidate_action)
            if expected_opposite and existing_action == expected_opposite:
                return True, (
                    f"Contradicts existing rule on '{candidate_section}': "
                    f"candidate says '{candidate_action}', "
                    f"existing says '{existing_action}'."
                )

    return False, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_promotion_eligibility(
    candidate_rules: list[dict],
    existing_main_rules: list[dict] | None = None,
) -> dict:
    """
    Promotion gate (Step 15).

    Evaluates which staging rules meet promotion criteria for the
    main rule set.  Pure rule-based -- no LLM calls.

    Each candidate rule dict is expected to have:
        rule_id, rule_content, occurrence_count, severity,
        section_id (or rule_category), action (or rule_action).

    Args:
        candidate_rules:     List of staging rule dicts to evaluate.
        existing_main_rules: (Optional) Current main rules for
                             contradiction checking.

    Returns:
        dict with keys:
            gate            - "promotion_gate"
            passed          - True (always; this gate reports eligibility)
            eligible_rules  - list of rules that passed all checks
            rejected_rules  - list of rules with rejection reasons
    """
    if existing_main_rules is None:
        existing_main_rules = []

    eligible: list[dict] = []
    rejected: list[dict] = []

    for rule in candidate_rules:
        rule_id = rule.get("rule_id", "unknown")
        rule_content = rule.get("rule_content", "")
        occurrence_count = int(rule.get("occurrence_count", 0))
        severity = (rule.get("severity") or "").lower().strip()
        rejection_reasons: list[str] = []

        # Check 1: Minimum occurrence count
        if occurrence_count < MIN_OCCURRENCE_COUNT:
            rejection_reasons.append(
                f"occurrence_count={occurrence_count} "
                f"(minimum: {MIN_OCCURRENCE_COUNT})"
            )

        # Check 2: Severity must be medium or high
        if severity not in ALLOWED_SEVERITIES:
            rejection_reasons.append(
                f"severity='{severity}' "
                f"(allowed: {', '.join(sorted(ALLOWED_SEVERITIES))})"
            )

        # Check 3: Must not be case-specific
        is_specific, specificity_reasons = _is_case_specific(rule_content)
        if is_specific:
            rejection_reasons.append(
                f"case_specific: {', '.join(specificity_reasons)}"
            )

        # Check 4: Must not contradict existing main rules
        is_contra, contra_reason = _is_contradictory(rule, existing_main_rules)
        if is_contra:
            rejection_reasons.append(f"contradictory: {contra_reason}")

        if rejection_reasons:
            rejected.append({
                "rule_id": rule_id,
                "rule_content": rule_content,
                "occurrence_count": occurrence_count,
                "severity": severity,
                "rejection_reasons": rejection_reasons,
            })
        else:
            eligible.append({
                "rule_id": rule_id,
                "rule_content": rule_content,
                "occurrence_count": occurrence_count,
                "severity": severity,
            })

    return {
        "gate": "promotion_gate",
        "passed": True,
        "eligible_rules": eligible,
        "rejected_rules": rejected,
    }
