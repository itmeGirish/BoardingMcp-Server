"""v10.0 Gap Fill Prompt — LLM generates N sections from gap_definitions.

Backward-compatible: if no gap_definitions, falls back to legacy 3-gap mode.

The template engine builds deterministic sections. The LLM fills variable-count
gaps defined by the LKB entry's gap_definitions (or family defaults).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..lkb.causes._family_defaults import get_family


# ---------------------------------------------------------------------------
# v10.0 System Prompt (N-gap aware)
# ---------------------------------------------------------------------------

def build_gap_fill_system_prompt(
    gap_definitions: Optional[List[Dict]] = None,
) -> str:
    """System prompt for gap-fill LLM call.

    If gap_definitions is provided, generates N-gap-aware instructions.
    Otherwise falls back to legacy 3-gap prompt.
    """
    if gap_definitions:
        n = len(gap_definitions)
        gap_ids = [g["gap_id"] for g in gap_definitions]
        markers = ", ".join(f"{{{{GENERATE:{gid}}}}}" for gid in gap_ids)
        output_lines = "\n".join(
            f"{{{{GENERATE:{gid}}}}}\n[Your {gid.lower().replace('_', ' ')} paragraphs here]\n"
            for gid in gap_ids
        )
        return f"""You are an expert Indian legal drafter with 25 years of courtroom practice.

You will receive a plaint template with {n} gaps marked. Generate ONLY the content for those {n} gaps. Do NOT generate any other section — the rest of the document is already written.

The gaps include both FACTUAL sections (facts, breach, damages, etc.) and SUBSTANTIVE sections (jurisdiction, legal basis, cause of action, valuation, prayer). Follow the per-section instructions carefully — each section has specific constraints.

RULES (follow ALL strictly):
1. Every FACT must trace to USER FACTS below. If a fact is missing, write {{{{FIELD_NAME}}}} as placeholder. NEVER fabricate facts.
2. Do NOT fabricate case citations (AIR/SCC/ILR). Cite only statutory provisions from VERIFIED PROVISIONS.
3. FACTS vs LAW: In FACTS-related sections (FACTS, BREACH, DAMAGES, etc.), plead ONLY factual events (dates, actions, amounts, documents). Do NOT cite Section/Order/Act numbers in facts sections — legal analysis belongs in LEGAL_BASIS.
4. Number paragraphs continuously starting from the number indicated in the gap marker.
5. Reference documents as Annexures using the labels from the document list (already written).
6. Do NOT output section headings inside the generated sections. Output numbered paragraphs only, formatted with a space after the number, e.g. '5. ...'.
7. Do NOT use 'continuing cause of action' or 'continuing breach' language unless USER FACTS expressly support it.
8. Do NOT claim compound interest unless the contract expressly provides for it.
9. PRAYER must contain SPECIFIC, ACTIONABLE reliefs — never leave {{{{...}}}} placeholders in prayer items.
10. In LEGAL_BASIS, cite ONLY provisions from VERIFIED PROVISIONS. Do NOT cite case law.

OUTPUT FORMAT:
Write each section starting with its marker on its own line:
{output_lines}
Write ONLY these {n} sections. Nothing else."""

    # Legacy 3-gap system prompt
    return """You are an expert Indian legal drafter with 25 years of courtroom practice.

You will receive a COMPLETE plaint template with 3 gaps marked. Generate ONLY the content for those 3 gaps. Do NOT generate any other section — the rest of the document is already written.

RULES (follow ALL strictly):
1. Every fact must trace to USER FACTS below. If a fact is missing, write {{FIELD_NAME}} as placeholder. NEVER fabricate facts.
2. Do NOT fabricate case citations (AIR/SCC/ILR). Cite only statutory provisions from VERIFIED PROVISIONS.
3. Write in formal pleading register — factual statements, not legal arguments. Save legal arguments for the Legal Basis section (already written).
4. Number paragraphs continuously starting from the number indicated in the gap marker.
5. Reference documents as Annexures using the labels from the document list (already written).

6. FACTS vs LAW: In {{GENERATE:FACTS}}, plead ONLY factual events (dates, actions, amounts, documents).
   Do NOT cite Section/Order/Act numbers in FACTS — legal analysis belongs in the LEGAL BASIS section already written.

OUTPUT FORMAT:
Write each section starting with its marker on its own line:
{{GENERATE:FACTS}}
[Your facts paragraphs here]

{{GENERATE:BREACH}}
[Your breach particulars here]

{{GENERATE:DAMAGES}}
[Your damages narrative here]

Write ONLY these 3 sections. Nothing else."""


# ---------------------------------------------------------------------------
# v10.0 User Prompt (N-gap aware)
# ---------------------------------------------------------------------------

def build_gap_fill_user_prompt(
    user_request: str,
    assembled_template: str,
    facts_summary: str,
    parties_context: str,
    evidence_context: str,
    verified_provisions: str,
    rag_context: str,
    draft_plan_context: str = "",
    cause_type: str = "",
    damages_categories: List[str] | None = None,
    facts_must_cover: List[str] | None = None,
    gap_definitions: Optional[List[Dict]] = None,
) -> str:
    """User prompt for gap-fill LLM call.

    If gap_definitions is provided, emits per-gap constraints from LKB.
    Otherwise falls back to legacy per-family constraints.

    User facts go FIRST (highest attention position — lost-in-the-middle).
    """
    parts = []

    # User facts FIRST
    parts.append(f"USER FACTS:\n{user_request}")

    if facts_summary:
        parts.append(f"\nEXTRACTED FACTS:\n{facts_summary}")

    if parties_context:
        parts.append(f"\nPARTIES:\n{parties_context}")

    if evidence_context:
        parts.append(f"\nEVIDENCE:\n{evidence_context}")

    # Damages categories to cover
    if damages_categories:
        cats = ", ".join(c.replace("_", " ") for c in damages_categories)
        parts.append(f"\nDAMAGES CATEGORIES TO COVER:\n{cats}")

    # Facts must cover — LKB-driven guidance on WHAT facts to plead
    if facts_must_cover:
        items = "\n".join(f"  - {item}" for item in facts_must_cover)
        parts.append(f"\nFACTS MUST COVER:\n{items}")

    # Template (shows full document context — LLM sees what's already written)
    template_preview = _truncate_template(assembled_template)
    parts.append(f"\nDOCUMENT TEMPLATE (for context — DO NOT regenerate these sections):\n{template_preview}")

    if verified_provisions:
        parts.append(f"\nVERIFIED PROVISIONS (cite ONLY these in your sections):\n{verified_provisions}")

    if rag_context:
        parts.append(f"\nSTATUTORY CONTEXT:\n{rag_context}")

    if draft_plan_context:
        parts.append(f"\nDRAFT PLAN CONSTRAINTS:\n{draft_plan_context}")

    # v10.0: Per-gap instructions from gap_definitions
    if gap_definitions:
        parts.append("\nPER-SECTION INSTRUCTIONS:")
        gap_ids = []
        for gap_def in gap_definitions:
            gid = gap_def["gap_id"]
            gap_ids.append(gid)
            parts.append(f"\n--- {{{{GENERATE:{gid}}}}} ---")
            parts.append(f"Section heading: {gap_def.get('heading', gid)}")

            constraints = gap_def.get("constraints", [])
            if constraints:
                parts.append("In this section, you MUST cover:")
                for c in constraints:
                    parts.append(f"  - {c}")

            anti_constraints = gap_def.get("anti_constraints", [])
            if anti_constraints:
                parts.append("In this section, you must NOT:")
                for ac in anti_constraints:
                    parts.append(f"  - {ac}")

        markers = ", ".join(f"{{{{GENERATE:{gid}}}}}" for gid in gap_ids)
        parts.append(
            f"\nGenerate the {len(gap_definitions)} sections now. "
            f"Start each with its marker ({markers})."
        )
    else:
        # Legacy per-family constraints
        _append_legacy_constraints(parts, cause_type)
        parts.append(
            f"\nGenerate the 3 sections now. Start each with its marker "
            f"({{{{GENERATE:FACTS}}}}, {{{{GENERATE:BREACH}}}}, {{{{GENERATE:DAMAGES}}}})."
        )

    return "\n".join(parts)


def _append_legacy_constraints(parts: List[str], cause_type: str):
    """Append legacy per-family constraints (used when gap_definitions=None)."""
    _fam = get_family(cause_type)
    if _fam == "injunction" or cause_type == "easement":
        parts.append(
            "\nPROPERTY RIGHT / INJUNCTION DRAFTING CONSTRAINTS:\n"
            "- In {{GENERATE:BREACH}}, plead the Plaintiff's existing right / possession and the Defendant's specific acts of interference or threat.\n"
            "- In {{GENERATE:DAMAGES}}, do not plead a money damages claim or interest. Plead irreparable harm, inadequacy of monetary compensation, and the need to restrain / undo the Defendant's acts.\n"
            "- Preserve land-identification and possession facts such as survey number, agricultural land description, cultivation, and revenue-record support where available."
        )
        if cause_type == "easement":
            parts.append(
                "- For an easement claim, plead more than twenty years of open, peaceable, uninterrupted use as of right, identify the dominant heritage and the obstructed pathway / servient strip, and describe the obstruction clearly. "
                "Do NOT plead a money damages claim. Focus on declaration of easementary right and the need for mandatory and permanent injunction."
            )
    elif _fam == "contract":
        contract_constraints = (
            "\nCONTRACT DRAFTING CONSTRAINTS:\n"
            "- Keep the 3 sections distinct: {{GENERATE:FACTS}} = contract background and Plaintiff performance; {{GENERATE:BREACH}} = Defendant's non-performance/default; {{GENERATE:DAMAGES}} = direct loss and quantification.\n"
            "- In {{GENERATE:FACTS}}, plead the date/nature of contract, the Defendant's obligation, and the Plaintiff's own performance. Use clean pleading language such as 'entered into a written agreement regarding ...' and 'duly performed all obligations required on its part under the agreement'. Do not shift breach allegations into this section. Do NOT use 'ready and willing' or 'readiness and willingness' language in a pure damages suit.\n"
            "- Avoid formulaic pleading phrases such as 'all conditions precedent have been fulfilled' unless USER FACTS expressly identify a real contractual or statutory precondition.\n"
            "- In {{GENERATE:BREACH}}, plead only the contractual default, due date / breach date, notice, and non-compliance. Prefer phrasing like 'committed breach on {{DATE_OF_BREACH}}' or 'failed to perform by {{DATE_OF_BREACH}}'. Use restrained language like 'failed to perform', 'remained in default', or 'did not comply with the notice'. Do NOT use awkward date formulas such as 'remained in default as on {{DATE_OF_BREACH}}'. Do NOT repeat the exact phrase 'to perform the contractual obligations' across multiple consecutive paragraphs. Do NOT use repudiatory, anticipatory, abandonment, termination, refusal, 'failed and neglected', or 'subsisting breach' language unless USER FACTS expressly support it. Do NOT describe loss, disruption, prejudice, or financial consequences in this section; those belong only in {{GENERATE:DAMAGES}}.\n"
            "- In {{GENERATE:DAMAGES}}, plead only the damages categories listed above. If only one damages category is listed, do not introduce additional loss heads. State the amount, the basis of computation, and that the claimed loss is the direct and natural consequence of the breach. Where a standard computation schedule is being used, refer to the statement / computation of damages as Annexure P-3.\n"
            "- If the only listed damages category is actual loss, quantify the damages in {{GENERATE:DAMAGES}} as Rs. {{TOTAL_SUIT_VALUE}}/- and avoid introducing a second standalone amount placeholder for the same claim.\n"
            "- For a Section 73 damages suit, describe loss as direct / natural consequence of the breach and plead foreseeability only if USER FACTS support it. Do NOT plead Section 74, liquidated damages, penalty clause, or arbitration-clause status unless USER FACTS expressly support them.\n"
            "- Do NOT add cause-of-action, limitation, jurisdiction, or legal-basis sentences inside the generated sections. Do NOT use 'continuing cause of action', 'continuing breach', or similar language unless USER FACTS expressly support a continuing default.\n"
            "- Do NOT output section headings inside the generated sections. Output numbered paragraphs only, and always format them with a space after the number, e.g. '5. ...'.\n"
            "- When referring to supporting documents in a standard contract damages plaint, refer to the contract copy as Annexure P-1 and the legal notice as Annexure P-2.\n"
            "- Prefer these standard placeholders where details are missing: {{DATE_OF_CONTRACT}}, {{CONTRACT_DETAILS}}, {{DEFENDANT_OBLIGATION}}, {{PLAINTIFF_PERFORMANCE_DETAILS}}, {{DATE_OF_BREACH}}, {{NOTICE_DATE}}, {{TOTAL_SUIT_VALUE}}."
        )
        if cause_type != "specific_performance":
            contract_constraints += (
                "\n- This is not a specific performance track. Do NOT plead specific performance, "
                "readiness and willingness, execution of sale deed, or other equitable relief unless "
                "USER FACTS expressly require that remedy."
            )
        parts.append(contract_constraints)
    elif _fam == "accounts":
        parts.append(
            "\nACCOUNTS / RELATIONSHIP DRAFTING CONSTRAINTS:\n"
            "- This is a suit for rendition of accounts — NOT a money recovery / damages suit.\n"
            "- In {{GENERATE:FACTS}}, plead the RELATIONSHIP BASIS: nature of the relationship "
            "(agency / partnership / joint business / fiduciary / trust), when it was formed, "
            "the Defendant's role in managing funds / property / business, the period of account, "
            "and the Plaintiff's entitlement to accounts.\n"
            "- In {{GENERATE:BREACH}}, plead the DUTY TO ACCOUNT AND DEFAULT: the Defendant's "
            "obligation to render accounts, specific demands made by the Plaintiff (dates and mode), "
            "the Defendant's refusal or failure to comply, and particulars of books / records / "
            "accounts withheld by the Defendant.\n"
            "- In {{GENERATE:DAMAGES}}, plead the AMOUNT BELIEVED DUE: approximate amount the "
            "Plaintiff believes is due after accounts (if known), basis of that belief, "
            "and why court-supervised accounting is necessary to ascertain the true amount.\n"
            "- Do NOT use typical damages language (loss suffered, direct consequence, "
            "compensation). This suit seeks accounts and payment of amount FOUND DUE.\n"
            "- Do NOT plead interest on delayed payment, liquidated damages, or penalty.\n"
            "- Do NOT output section headings inside the generated sections. Output numbered "
            "paragraphs only.\n"
            "- Prefer these standard placeholders: {{RELATIONSHIP_TYPE}}, {{RELATIONSHIP_DATE}}, "
            "{{ACCOUNTING_PERIOD}}, {{DEMAND_DATE}}, {{APPROXIMATE_AMOUNT_DUE}}."
        )


# ---------------------------------------------------------------------------
# Template truncation
# ---------------------------------------------------------------------------

def _truncate_template(template: str, max_lines: int = 80) -> str:
    """Show template structure without full content to save tokens."""
    lines = template.split("\n")
    if len(lines) <= max_lines:
        return template

    # Show first 30 lines + section headers + last 20 lines
    result = []
    result.extend(lines[:30])
    result.append("\n... [template sections: JURISDICTION, LIMITATION, SECTION 12A, etc.] ...\n")

    # Find section headers in middle
    for line in lines[30:-20]:
        stripped = line.strip()
        if stripped.isupper() and len(stripped) > 3 and len(stripped) < 60:
            result.append(stripped)
        elif stripped.startswith("{{GENERATE:"):
            result.append(stripped)

    result.append("\n... [remaining template sections] ...\n")
    result.extend(lines[-20:])
    return "\n".join(result)


# ---------------------------------------------------------------------------
# v10.0 N-gap parser (backward-compatible)
# ---------------------------------------------------------------------------

def parse_gap_fill_response(
    response: str,
    gap_definitions: Optional[List[Dict]] = None,
) -> Dict[str, str]:
    """Parse LLM response into N sections.

    If gap_definitions is provided, parses variable-count gaps by gap_id.
    Otherwise falls back to legacy 3-gap parse (FACTS, BREACH, DAMAGES).

    Returns dict keyed by gap_id (or legacy keys: facts, breach, damages).
    """
    if gap_definitions:
        return _parse_n_gaps(response, gap_definitions)

    # Legacy 3-gap parse
    result = {"facts": "", "breach": "", "damages": ""}

    parts = re.split(r'\{\{GENERATE:(FACTS|BREACH|DAMAGES)(?:\|[^}]*)?\}\}', response)

    for i, part in enumerate(parts):
        if part == "FACTS" and i + 1 < len(parts):
            result["facts"] = parts[i + 1].strip()
        elif part == "BREACH" and i + 1 < len(parts):
            result["breach"] = parts[i + 1].strip()
        elif part == "DAMAGES" and i + 1 < len(parts):
            result["damages"] = parts[i + 1].strip()

    return result


def _parse_n_gaps(response: str, gap_definitions: List[Dict]) -> Dict[str, str]:
    """Parse N gaps from LLM response based on gap_definitions."""
    gap_ids = [g["gap_id"] for g in gap_definitions]
    result = {gid: "" for gid in gap_ids}

    # Build pattern to split on any gap marker
    pattern = '|'.join(re.escape(gid) for gid in gap_ids)
    parts = re.split(
        rf'\{{\{{GENERATE:({pattern})(?:\|[^}}]*)?\}}\}}',
        response,
    )

    for i, part in enumerate(parts):
        if part in gap_ids and i + 1 < len(parts):
            result[part] = parts[i + 1].strip()

    return result


# ---------------------------------------------------------------------------
# v10.0 N-gap merger (backward-compatible)
# ---------------------------------------------------------------------------

def merge_template_with_gaps(
    template: str,
    gaps: Dict[str, str],
    cause_type: str = "",
    gap_definitions: Optional[List[Dict]] = None,
) -> str:
    """Replace gap markers in template with LLM-generated content.

    If gap_definitions is provided, uses heading from gap_definitions for each gap.
    Otherwise falls back to legacy 3-gap merge with hardcoded headings.
    """
    if gap_definitions:
        return _merge_n_gaps(template, gaps, gap_definitions)

    # Legacy 3-gap merge
    result = template
    facts_heading = "FACTS OF THE CASE"
    breach_heading = "BREACH PARTICULARS"
    damages_heading = "DAMAGES"

    if (cause_type or "").startswith("recovery_of_possession"):
        breach_heading = "DEFENDANT'S UNAUTHORIZED OCCUPATION"
        damages_heading = "MESNE PROFITS"
    elif get_family(cause_type) == "injunction":
        breach_heading = "PLAINTIFF RIGHT AND DEFENDANT INTERFERENCE"
        damages_heading = "IRREPARABLE HARM AND BALANCE OF CONVENIENCE"
    elif get_family(cause_type) == "accounts":
        facts_heading = "RELATIONSHIP BASIS AND FACTS"
        breach_heading = "DUTY TO ACCOUNT AND DEFAULT"
        damages_heading = "AMOUNT FOUND DUE AFTER ACCOUNTS"

    if gaps.get("facts"):
        result = re.sub(
            r'\{\{GENERATE:FACTS(?:\|[^}]*)?\}\}',
            f"{facts_heading}\n\n{gaps['facts']}",
            result,
        )

    if gaps.get("breach"):
        result = re.sub(
            r'\{\{GENERATE:BREACH\}\}',
            f"{breach_heading}\n\n{gaps['breach']}",
            result,
        )

    if gaps.get("damages"):
        result = re.sub(
            r'\{\{GENERATE:DAMAGES\}\}',
            f"{damages_heading}\n\n{gaps['damages']}",
            result,
        )

    result = re.sub(r'\{\{GENERATE:\w+(?:\|[^}]*)?\}\}', '{{SECTION_NOT_GENERATED}}', result)
    return result


def _merge_n_gaps(
    template: str,
    gaps: Dict[str, str],
    gap_definitions: List[Dict],
) -> str:
    """Merge N gaps using headings from gap_definitions."""
    result = template

    for gap_def in gap_definitions:
        gid = gap_def["gap_id"]
        heading = gap_def.get("heading", gid.replace("_", " ").title())
        content = gaps.get(gid, "")

        if content:
            result = re.sub(
                rf'\{{\{{GENERATE:{re.escape(gid)}(?:\|[^}}]*)?\}}\}}',
                f"{heading}\n\n{content}",
                result,
            )

    # Clean up any unfilled markers
    result = re.sub(r'\{\{GENERATE:\w+(?:\|[^}]*)?\}\}', '{{SECTION_NOT_GENERATED}}', result)
    return result


# ---------------------------------------------------------------------------
# Paragraph renumbering (unchanged)
# ---------------------------------------------------------------------------

def renumber_paragraphs(text: str) -> str:
    """Fix paragraph numbering to be continuous across merged document."""
    counter = [0]

    def _replace(match):
        counter[0] += 1
        return f"{counter[0]}."

    result = re.sub(r'(?m)^(\d+)\.\s', _replace, text)
    return result
