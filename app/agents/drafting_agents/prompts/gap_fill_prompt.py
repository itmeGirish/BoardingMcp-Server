"""v8.0 Gap Fill Prompt — LLM generates ONLY 3 sections.

The template engine builds 15 sections deterministically. The LLM
fills in 3 gaps: FACTS, BREACH PARTICULARS, DAMAGES NARRATIVE.

Prompt is ~3K tokens (vs v7.0's ~6-8K). LLM output is ~8K chars (vs 25K).
"""
from __future__ import annotations

from typing import Any, Dict, List


def build_gap_fill_system_prompt() -> str:
    """System prompt for gap-fill LLM call."""
    return """You are an expert Indian legal drafter with 25 years of courtroom practice.

You will receive a COMPLETE plaint template with 3 gaps marked. Generate ONLY the content for those 3 gaps. Do NOT generate any other section — the rest of the document is already written.

RULES (follow ALL strictly):
1. Every fact must trace to USER FACTS below. If a fact is missing, write {{FIELD_NAME}} as placeholder. NEVER fabricate facts.
2. Do NOT fabricate case citations (AIR/SCC/ILR). Cite only statutory provisions from VERIFIED PROVISIONS.
3. Write in formal pleading register — factual statements, not legal arguments. Save legal arguments for the Legal Basis section (already written).
4. Number paragraphs continuously starting from the number indicated in the gap marker.
5. Reference documents as Annexures using the labels from the document list (already written).

OUTPUT FORMAT:
Write each section starting with its marker on its own line:
{{GENERATE:FACTS}}
[Your facts paragraphs here]

{{GENERATE:BREACH}}
[Your breach particulars here]

{{GENERATE:DAMAGES}}
[Your damages narrative here]

Write ONLY these 3 sections. Nothing else."""


def build_gap_fill_user_prompt(
    user_request: str,
    assembled_template: str,
    facts_summary: str,
    parties_context: str,
    evidence_context: str,
    verified_provisions: str,
    rag_context: str,
    cause_type: str = "",
    damages_categories: List[str] | None = None,
) -> str:
    """User prompt for gap-fill LLM call.

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

    # Template (shows full document context — LLM sees what's already written)
    # Truncate to avoid overwhelming — show structure not full content
    template_preview = _truncate_template(assembled_template)
    parts.append(f"\nDOCUMENT TEMPLATE (for context — DO NOT regenerate these sections):\n{template_preview}")

    if verified_provisions:
        parts.append(f"\nVERIFIED PROVISIONS (cite ONLY these in your sections):\n{verified_provisions}")

    if rag_context:
        parts.append(f"\nSTATUTORY CONTEXT:\n{rag_context}")

    parts.append(
        f"\nGenerate the 3 sections now. Start each with its marker "
        f"({{{{GENERATE:FACTS}}}}, {{{{GENERATE:BREACH}}}}, {{{{GENERATE:DAMAGES}}}})."
    )

    return "\n".join(parts)


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


def parse_gap_fill_response(response: str) -> Dict[str, str]:
    """Parse LLM response into the 3 sections.

    Returns dict with keys: facts, breach, damages.
    Each value is the generated text for that section.
    """
    import re

    result = {"facts": "", "breach": "", "damages": ""}

    # Split on markers
    # Pattern: {{GENERATE:FACTS}} or {{GENERATE:FACTS|start_para=5}}
    parts = re.split(r'\{\{GENERATE:(FACTS|BREACH|DAMAGES)(?:\|[^}]*)?\}\}', response)

    # parts will be: [preamble, 'FACTS', facts_text, 'BREACH', breach_text, 'DAMAGES', damages_text]
    for i, part in enumerate(parts):
        if part == "FACTS" and i + 1 < len(parts):
            result["facts"] = parts[i + 1].strip()
        elif part == "BREACH" and i + 1 < len(parts):
            result["breach"] = parts[i + 1].strip()
        elif part == "DAMAGES" and i + 1 < len(parts):
            result["damages"] = parts[i + 1].strip()

    return result


def merge_template_with_gaps(template: str, gaps: Dict[str, str]) -> str:
    """Replace gap markers in template with LLM-generated content.

    Args:
        template: Document skeleton from TemplateEngine.assemble()
        gaps: Dict with keys facts, breach, damages from parse_gap_fill_response()

    Returns:
        Complete document text.
    """
    import re

    result = template

    # Replace each marker with generated content
    if gaps.get("facts"):
        result = re.sub(
            r'\{\{GENERATE:FACTS(?:\|[^}]*)?\}\}',
            f"FACTS OF THE CASE\n\n{gaps['facts']}",
            result,
        )

    if gaps.get("breach"):
        result = re.sub(
            r'\{\{GENERATE:BREACH\}\}',
            f"BREACH PARTICULARS\n\n{gaps['breach']}",
            result,
        )

    if gaps.get("damages"):
        result = re.sub(
            r'\{\{GENERATE:DAMAGES\}\}',
            f"DAMAGES\n\n{gaps['damages']}",
            result,
        )

    # Clean up any unfilled markers (shouldn't happen, but defensive)
    result = re.sub(r'\{\{GENERATE:\w+(?:\|[^}]*)?\}\}', '{{SECTION_NOT_GENERATED}}', result)

    return result


def renumber_paragraphs(text: str) -> str:
    """Fix paragraph numbering to be continuous across merged document.

    Template sections use their own numbering. After merge, renumber
    all paragraphs 1, 2, 3... continuously.
    """
    import re

    counter = [0]

    def _replace(match):
        counter[0] += 1
        return f"{counter[0]}."

    # Match paragraph numbers at start of line: "1. ", "12. ", etc.
    result = re.sub(r'(?m)^(\d+)\.\s', _replace, text)
    return result
