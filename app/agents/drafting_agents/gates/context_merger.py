"""
Context Merger Gate  (CLAUD.md Step 11) -- Rule-based, NO LLM calls.

Merges all agent outputs (template pack, compliance report, local rules,
prayer pack, research bundle, citation pack, mistake checklist, and
master facts) into a single unified DRAFT_CONTEXT that the drafting
agent can consume directly.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_sections(template_pack: dict) -> list[dict]:
    """
    Extract section definitions from the template pack.

    Each section dict is expected to have at least:
        section_id, title, order, content_hint, required (bool)
    """
    return list(template_pack.get("sections", []))


def _apply_compliance(
    sections: list[dict],
    compliance_report: dict,
) -> tuple[list[dict], list[str]]:
    """
    Enforce compliance requirements on the section list.

    - Mark mandatory sections that compliance says are required.
    - Append any mandatory annexures not already present.

    Returns:
        (updated_sections, warnings)
    """
    warnings: list[str] = []

    mandatory_sections = set(compliance_report.get("mandatory_sections", []))
    mandatory_annexures = compliance_report.get("mandatory_annexures", [])

    # Ensure mandatory sections are marked as required
    section_ids = set()
    for section in sections:
        section_ids.add(section.get("section_id", ""))
        if section.get("section_id", "") in mandatory_sections:
            if not section.get("required"):
                warnings.append(
                    f"Section '{section.get('title', section.get('section_id'))}' "
                    f"upgraded to required by compliance."
                )
                section["required"] = True

    # Flag missing mandatory sections
    for ms in mandatory_sections:
        if ms not in section_ids:
            warnings.append(
                f"Compliance requires section '{ms}' but it is not in the template."
            )

    # Append mandatory annexures
    existing_annexure_ids = {
        s.get("section_id", "")
        for s in sections
        if s.get("section_type") == "annexure"
    }
    for annexure in mandatory_annexures:
        ann_id = annexure if isinstance(annexure, str) else annexure.get("annexure_id", "")
        if ann_id and ann_id not in existing_annexure_ids:
            sections.append({
                "section_id": ann_id,
                "title": ann_id.replace("_", " ").title(),
                "order": 999,  # Append at end
                "section_type": "annexure",
                "required": True,
                "content_hint": "Mandatory annexure added by compliance.",
                "source": "compliance",
            })

    return sections, warnings


def _apply_localization(
    sections: list[dict],
    local_rules: dict,
) -> tuple[list[dict], list[str]]:
    """
    Apply localization formatting rules to sections.

    local_rules may contain:
        language, date_format, numbering_style, court_header_format,
        stamp_paper_required, local_sections (extra sections for the jurisdiction)
    """
    warnings: list[str] = []

    formatting = {
        "language": local_rules.get("language"),
        "date_format": local_rules.get("date_format"),
        "numbering_style": local_rules.get("numbering_style"),
        "court_header_format": local_rules.get("court_header_format"),
        "stamp_paper_required": local_rules.get("stamp_paper_required", False),
    }

    # Attach formatting metadata to each section
    for section in sections:
        section["localization"] = formatting

    # Append any jurisdiction-specific extra sections
    for extra in local_rules.get("local_sections", []):
        sections.append({
            "section_id": extra.get("section_id", "local_extra"),
            "title": extra.get("title", "Local Requirement"),
            "order": extra.get("order", 998),
            "section_type": "local",
            "required": extra.get("required", False),
            "content_hint": extra.get("content_hint", ""),
            "source": "localization",
            "localization": formatting,
        })

    return sections, warnings


def _insert_prayers(sections: list[dict], prayer_pack: dict) -> list[dict]:
    """
    Insert prayer / relief clauses into the section list.

    prayer_pack is expected to have:
        prayers: list[{prayer_id, text, order}]
    """
    prayers = prayer_pack.get("prayers", [])
    if not prayers:
        return sections

    # Build a consolidated prayer section
    prayer_texts = [p.get("text", "") for p in prayers if p.get("text")]
    sections.append({
        "section_id": "prayer",
        "title": "Prayer / Relief Sought",
        "order": 900,
        "section_type": "prayer",
        "required": True,
        "content": prayer_texts,
        "source": "prayer_pack",
    })

    return sections


def _add_citations(
    sections: list[dict],
    citation_pack: dict | None,
) -> list[dict]:
    """
    Attach citations to the draft context if available.
    """
    if not citation_pack:
        return sections

    citations = citation_pack.get("citations", [])
    if not citations:
        return sections

    sections.append({
        "section_id": "citations",
        "title": "Relevant Case Law & Citations",
        "order": 850,
        "section_type": "citations",
        "required": False,
        "content": citations,
        "source": "citation_pack",
    })

    return sections


def _add_research(
    sections: list[dict],
    research_bundle: dict | None,
) -> list[dict]:
    """
    Attach research principles / precedents to the draft context.
    """
    if not research_bundle:
        return sections

    principles = research_bundle.get("principles", [])
    precedents = research_bundle.get("precedents", [])

    if not principles and not precedents:
        return sections

    sections.append({
        "section_id": "research",
        "title": "Legal Principles & Precedents",
        "order": 840,
        "section_type": "research",
        "required": False,
        "content": {
            "principles": principles,
            "precedents": precedents,
        },
        "source": "research_bundle",
    })

    return sections


def _detect_conflicts(
    sections: list[dict],
    compliance_report: dict,
) -> list[str]:
    """
    Detect conflicts between different component outputs.

    For example: compliance says a section is "required" but the template
    marks it as "optional".
    """
    warnings: list[str] = []

    mandatory_sections = set(compliance_report.get("mandatory_sections", []))
    optional_in_template = set(compliance_report.get("optional_in_template", []))

    for section_id in mandatory_sections:
        if section_id in optional_in_template:
            warnings.append(
                f"Conflict: compliance marks '{section_id}' as required, "
                f"but the template marks it as optional. "
                f"Compliance requirement takes precedence."
            )

    return warnings


def _collect_hard_blocks(*components: dict | None) -> list[dict]:
    """
    Check all component outputs for hard_block flags.
    """
    hard_blocks: list[dict] = []
    for comp in components:
        if comp is None:
            continue
        if comp.get("hard_block"):
            hard_blocks.append({
                "source": comp.get("gate") or comp.get("source") or "unknown",
                "reason": comp.get("hard_block_reason", "Unspecified hard block"),
                "details": {
                    k: v for k, v in comp.items()
                    if k not in ("gate", "source", "hard_block", "hard_block_reason")
                },
            })
    return hard_blocks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def merge_context(
    template_pack: dict,
    compliance_report: dict,
    local_rules: dict,
    prayer_pack: dict,
    research_bundle: dict | None = None,
    citation_pack: dict | None = None,
    mistake_checklist: dict | None = None,
    master_facts: dict | None = None,
    clarification_questions: list | None = None,
) -> dict:
    """
    Context Merger gate (Step 11).

    Merges all agent outputs into a single DRAFT_CONTEXT for the
    drafting agent.  Pure rule-based -- no LLM calls.

    Missing fields from the clarification gate are converted into
    ``{{FIELD_NAME}}`` placeholder markers in ``placeholder_map``
    so the drafting agent uses them instead of fabricating data.

    Args:
        template_pack:           Template sections and structure.
        compliance_report:       Mandatory sections, annexures, rules.
        local_rules:             Jurisdiction-specific formatting / sections.
        prayer_pack:             Prayer / relief clauses.
        research_bundle:         (Optional) Legal principles and precedents.
        citation_pack:           (Optional) Relevant case citations.
        mistake_checklist:       (Optional) Common mistakes to avoid.
        master_facts:            (Optional) Consolidated fact dictionary.
        clarification_questions: (Optional) Missing-field questions from Step 5.

    Returns:
        dict with keys:
            gate          - "context_merger"
            passed        - bool
            draft_context - {sections, master_facts, mistake_checklist, ...}
            hard_blocks   - list
            warnings      - list
    """
    all_warnings: list[str] = []
    clarification_questions = clarification_questions or []

    # 1. Collect base sections from template
    sections = _collect_sections(template_pack)

    # 2. Apply compliance requirements
    sections, compliance_warnings = _apply_compliance(sections, compliance_report)
    all_warnings.extend(compliance_warnings)

    # 3. Apply localization formatting
    sections, local_warnings = _apply_localization(sections, local_rules)
    all_warnings.extend(local_warnings)

    # 4. Insert prayers
    sections = _insert_prayers(sections, prayer_pack)

    # 5. Add citations if available
    sections = _add_citations(sections, citation_pack)

    # 6. Add research if available
    sections = _add_research(sections, research_bundle)

    # 7. Detect conflicts
    conflict_warnings = _detect_conflicts(sections, compliance_report)
    all_warnings.extend(conflict_warnings)

    # 8. Check for hard blocks across all components
    hard_blocks = _collect_hard_blocks(
        template_pack,
        compliance_report,
        local_rules,
        prayer_pack,
        research_bundle,
        citation_pack,
        mistake_checklist,
    )

    # 9. Sort sections by order
    sections.sort(key=lambda s: s.get("order", 0))

    # 10. Build placeholder map for missing fields
    #     The clarification gate records missing fields; here we convert them
    #     into {{FIELD_NAME}} markers so the drafting agent preserves them
    #     instead of fabricating data.
    placeholder_map = {}
    for q in clarification_questions:
        if isinstance(q, dict):
            field = q.get("field", "")
            if field:
                placeholder_map[field] = "{{" + field.upper() + "}}"

    # 11. Build the unified draft context
    draft_context = {
        "sections": sections,
        "master_facts": master_facts or {},
        "mistake_checklist": mistake_checklist.get("checks", []) if mistake_checklist else [],
        "placeholder_map": placeholder_map,
        "template_metadata": {
            k: v for k, v in template_pack.items() if k != "sections"
        },
        "compliance_metadata": {
            k: v for k, v in compliance_report.items()
            if k not in ("mandatory_sections", "mandatory_annexures",
                         "hard_block", "hard_block_reason", "optional_in_template")
        },
        "localization_metadata": {
            k: v for k, v in local_rules.items()
            if k != "local_sections"
        },
    }

    passed = len(hard_blocks) == 0

    return {
        "gate": "context_merger",
        "passed": passed,
        "draft_context": draft_context,
        "hard_blocks": hard_blocks,
        "warnings": all_warnings,
    }
