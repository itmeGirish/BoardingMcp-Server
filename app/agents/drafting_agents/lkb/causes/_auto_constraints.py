"""v10.0 Auto-Constraint Generator — converts LKB fields to gap constraints.

Instead of 1,518 lines of hardcoded engine builders, this module reads
existing LKB fields (primary_acts, required_reliefs, coa_guidance, etc.)
and auto-generates gap_definitions for substantive sections.

The LLM writes ALL legal content. Gates validate the output.
Engine only produces structural sections (court heading, parties, etc.).

Usage:
    from ._auto_constraints import build_substantive_gaps

    gaps = build_substantive_gaps(lkb_entry, cause_type)
    # Returns list of gap_definitions for JURISDICTION, LEGAL_BASIS,
    # CAUSE_OF_ACTION, VALUATION, PRAYER
"""
from __future__ import annotations

from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# CPC sections that are jurisdictional/procedural — NEVER in LEGAL BASIS
# ---------------------------------------------------------------------------

_PROCEDURAL_CPC_SECTIONS = {
    "Section 9", "Section 15", "Section 16", "Section 17", "Section 18",
    "Section 19", "Section 20", "Section 34", "Section 91", "Section 151",
    "Order XXXVII", "Order XXXVII Rule 1", "Order XXXVII Rule 2",
    "Order XX Rule 11", "Order XX Rule 12", "Order XX Rule 18",
}


# ---------------------------------------------------------------------------
# Individual gap generators — each reads existing LKB fields
# ---------------------------------------------------------------------------

def _auto_jurisdiction_gap(lkb: Dict[str, Any], cause_type: str) -> Dict:
    """JURISDICTION gap — constraints from family (situs vs general)."""
    from ._family_defaults import get_family

    family = get_family(cause_type)

    constraints = [
        "State that the Plaintiff is a person sui juris and competent to institute the suit",
        "State that the Defendant is a person sui juris and can be sued",
    ]

    # Property suits → S.16 situs jurisdiction
    if family in ("partition", "possession", "tenancy"):
        constraints.append(
            "Invoke Section 16 of CPC, 1908 — the suit immovable property is "
            "situated within the local limits of this Court"
        )
    elif family == "injunction":
        # Injunction may be property-based or person-based
        constraints.append(
            "Invoke Section 16 of CPC, 1908 if the suit relates to immovable property "
            "(property situated within jurisdiction), OR Section 20 of CPC, 1908 if "
            "the suit relates to a personal right (defendant resides or cause of action arose)"
        )
    elif family == "tort":
        # Tort suits → S.19 CPC (where wrong was committed)
        constraints.append(
            "Invoke Section 19 of CPC, 1908 — the wrong was committed, or the "
            "Defendant resides or carries on business, within the jurisdiction "
            "of this Court. Section 20 CPC also applies as residuary"
        )
    elif family == "contract":
        constraints.append(
            "Invoke Section 20 of CPC, 1908 — the contract was executed, or was to be "
            "performed, or the defendant resides, or the cause of action arose, within "
            "the jurisdiction of this Court"
        )
    else:
        constraints.append(
            "Invoke Section 20 of CPC, 1908 — the defendant resides or carries on "
            "business, or the cause of action arose, within the jurisdiction of this Court"
        )

    # S.15 CPC — pecuniary jurisdiction
    constraints.append(
        "Invoke Section 15 of CPC, 1908 — the suit is filed in the Court of the "
        "lowest grade competent to try it; the suit value is within the pecuniary "
        "limits prescribed for this Court"
    )

    # Commercial court S.12A mediation
    court_rules = lkb.get("court_rules", {})
    prereqs = lkb.get("procedural_prerequisites", [])
    if "commercial" in court_rules or "section_12a_mediation" in prereqs:
        constraints.append(
            "If Commercial Court jurisdiction applies, mention Section 12A "
            "pre-institution mediation compliance or exemption"
        )

    return {
        "gap_id": "JURISDICTION",
        "heading": "JURISDICTION",
        "constraints": constraints,
        "anti_constraints": [
            "Do NOT cite case law on jurisdiction",
            "Do NOT argue jurisdiction — simply state the statutory basis",
        ],
    }


def _auto_legal_basis_gap(lkb: Dict[str, Any]) -> Dict:
    """LEGAL_BASIS gap — constraints from primary_acts, permitted_doctrines.

    CPC procedural sections (S.9, S.16, S.19, S.20, S.34, etc.) are filtered
    out — they belong in JURISDICTION, not LEGAL BASIS.
    """
    constraints = []

    # Primary acts → what to cite (filter CPC procedural sections)
    for act_entry in lkb.get("primary_acts", []):
        act = act_entry.get("act", "")
        sections = act_entry.get("sections", [])
        if "Code of Civil Procedure" in act:
            sections = [s for s in sections if s not in _PROCEDURAL_CPC_SECTIONS]
        if sections:
            sec_str = ", ".join(sections)
            constraints.append(f"Cite {sec_str} of {act}")
        elif act and "Code of Civil Procedure" not in act:
            constraints.append(f"Cite {act}")

    # Alternative acts (same CPC filter)
    for act_entry in lkb.get("alternative_acts", []):
        act = act_entry.get("act", "")
        sections = act_entry.get("sections", [])
        if "Code of Civil Procedure" in act:
            sections = [s for s in sections if s not in _PROCEDURAL_CPC_SECTIONS]
        if sections:
            sec_str = ", ".join(sections)
            constraints.append(f"May also cite {sec_str} of {act} if applicable")
        elif act and "Code of Civil Procedure" not in act:
            constraints.append(f"May also cite {act} if applicable")

    # Permitted doctrines → what legal principles to invoke
    for doctrine in lkb.get("permitted_doctrines", []):
        display = doctrine.replace("_", " ")
        constraints.append(f"May invoke doctrine of {display}")

    # Defensive points → additional legal points
    for point in lkb.get("defensive_points", []):
        constraints.append(f"Address: {point}")

    # NOTE: mandatory_averments are factual pleading requirements — they belong
    # in the relevant factual gap (FACTS, BREACH, etc.), NOT in LEGAL_BASIS.
    # They are injected by the family-specific gap definitions, not here.

    # Fallback if no primary_acts
    if not constraints:
        display = lkb.get("display_name", "the cause of action")
        constraints.append(f"State the legal basis for {display}")

    constraints.append(
        "Explain why the Plaintiff is entitled to the relief sought under the cited provisions"
    )

    return {
        "gap_id": "LEGAL_BASIS",
        "heading": "LEGAL BASIS",
        "constraints": constraints,
        "anti_constraints": [
            "Do NOT cite case law or AIR/SCC/ILR references",
            "Do NOT cite acts or sections not listed in VERIFIED PROVISIONS",
            "Do NOT repeat facts — state only the legal entitlement",
        ],
    }


def _auto_coa_gap(lkb: Dict[str, Any]) -> Dict:
    """CAUSE_OF_ACTION gap — constraints from coa_type, coa_guidance, limitation."""
    constraints = [
        "State when the cause of action FIRST arose — specific date",
        "State the specific act or omission by the Defendant that gave rise to the right to sue",
        "State that the suit is filed within the limitation period",
    ]

    coa_type = lkb.get("coa_type")
    if coa_type == "continuing":
        constraints.append(
            "State that the cause of action is continuing in nature "
            "and is subsisting on the date of filing"
        )
    elif coa_type == "single_event":
        constraints.append("Identify the single specific event that constitutes the cause of action")

    coa_guidance = lkb.get("coa_guidance", "")
    if coa_guidance:
        constraints.append(coa_guidance)

    # Inject limitation article + period from LKB
    limitation = lkb.get("limitation", {})
    article = limitation.get("article", "")
    period = limitation.get("period", "")
    accrual = limitation.get("from", "")
    if article and article != "UNKNOWN" and period:
        constraints.append(
            f"The suit is governed by Article {article} of the Limitation Act, 1963 "
            f"— limitation period is {period} from: {accrual}"
        )

    return {
        "gap_id": "CAUSE_OF_ACTION",
        "heading": "CAUSE OF ACTION",
        "constraints": constraints,
        "anti_constraints": [
            "Do NOT repeat facts already stated in earlier sections",
            "Do NOT cite case law",
            "Keep this section concise — 2-3 paragraphs maximum",
        ],
    }


def _auto_valuation_gap(lkb: Dict[str, Any]) -> Dict:
    """VALUATION gap — constraints from court_fee data."""
    constraints = [
        "State the total suit valuation in Rs. with amount in words",
        "State the purpose of valuation (jurisdiction and court fee)",
        "State the court fee amount paid",
        "State that the plaint is properly stamped / tendered with requisite court fee",
    ]

    court_fee = lkb.get("court_fee_statute", {})
    if court_fee:
        act = court_fee.get("act", "")
        if act:
            constraints.append(f"Court fee is computed under {act}")
        else:
            constraints.append(
                "Court fee computed under the applicable state Court Fees Act "
                "(use {{COURT_FEE_ACT_NAME}} — state-specific, must be verified)"
            )
    else:
        constraints.append(
            "Court fee computed under the applicable state Court Fees Act "
            "(use {{COURT_FEE_ACT_NAME}} — state-specific, must be verified)"
        )

    return {
        "gap_id": "VALUATION",
        "heading": "VALUATION AND COURT FEE",
        "constraints": constraints,
        "anti_constraints": [
            "Do NOT guess the court fee amount — use {{COURT_FEE_AMOUNT}} if unknown",
            "Do NOT guess the suit value — use {{TOTAL_SUIT_VALUE}} if unknown",
        ],
    }


def _auto_prayer_gap(lkb: Dict[str, Any]) -> Dict:
    """PRAYER gap — constraints from required_reliefs, optional_reliefs, prayer_template."""
    constraints = [
        "Begin with: 'In the premises aforesaid, the Plaintiff most respectfully prays "
        "that this Hon'ble Court be pleased to:'",
        "Letter each prayer item: (a), (b), (c), etc.",
    ]

    # Required reliefs → MUST pray for
    for relief in lkb.get("required_reliefs", []):
        display = relief.replace("_", " ").replace("decree", "").strip()
        display = " ".join(display.split())  # collapse multiple spaces
        if display:
            constraints.append(f"MUST pray for: {display}")

    # Optional reliefs → MAY pray for
    for relief in lkb.get("optional_reliefs", []):
        display = relief.replace("_", " ").replace("decree", "").strip()
        display = " ".join(display.split())
        if display:
            constraints.append(f"May pray for: {display}")

    # prayer_template items as guidance — but ONLY items without {{...}} variables
    for item in lkb.get("prayer_template", []):
        if "{{" not in item:
            constraints.append(f"Use this prayer language: '{item}'")

    # Check if any relief involves money — require specific amount
    money_keywords = {"damages", "money", "compensation", "recovery", "arrears", "mesne_profits"}
    has_money_relief = any(
        any(kw in r.lower() for kw in money_keywords)
        for r in lkb.get("required_reliefs", []) + lkb.get("optional_reliefs", [])
    )
    if has_money_relief:
        constraints.append(
            "MUST state the specific monetary amount (in numerals AND words) for each "
            "money or damages prayer — use {{CLAIM_AMOUNT}} if exact figure unknown"
        )

    # Always include costs and general relief
    constraints.extend([
        "MUST pray for costs of the suit",
        "MUST end with: 'Grant such other and further relief(s) as this Hon'ble Court "
        "may deem fit and proper in the facts and circumstances of the case'",
    ])

    # Red flags relevant to prayer
    for flag in lkb.get("drafting_red_flags", []):
        flag_lower = flag.lower()
        if any(kw in flag_lower for kw in ("prayer", "relief", "decree", "consequential")):
            constraints.append(f"WARNING: {flag}")

    return {
        "gap_id": "PRAYER",
        "heading": "PRAYER",
        "constraints": constraints,
        "anti_constraints": [
            "Do NOT pray for relief against non-parties",
            "Do NOT leave {{...}} placeholders in prayer items — write specific relief text",
            "Do NOT use vague language — each prayer item must state a specific, actionable relief",
            "End each prayer item with a semicolon except the last which ends with a period",
        ],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_substantive_gaps(lkb: Dict[str, Any], cause_type: str) -> List[Dict]:
    """Auto-generate gap_definitions for all substantive sections from LKB fields.

    Returns 5 gap_definitions: JURISDICTION, LEGAL_BASIS, CAUSE_OF_ACTION,
    VALUATION, PRAYER. Each is auto-generated from existing LKB fields —
    no manual data authoring needed.

    These are APPENDED to the factual gaps (FACTS, BREACH, DAMAGES, etc.)
    which come from GAP_FAMILY_DEFAULTS.
    """
    return [
        _auto_jurisdiction_gap(lkb, cause_type),
        _auto_legal_basis_gap(lkb),
        _auto_coa_gap(lkb),
        _auto_valuation_gap(lkb),
        _auto_prayer_gap(lkb),
    ]
