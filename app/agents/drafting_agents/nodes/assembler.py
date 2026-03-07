"""Assembler Node — deterministic (NO LLM).

Renders section-keyed JSON from draft_single_call into a formatted document.
Adds deterministic headings, verification clause, advocate block.
Outputs standard DraftArtifact (same schema as current pipeline).

Pipeline position: structural_gate → **assembler** → evidence_anchoring
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List

from langgraph.types import Command

from ....config import logger
from ..states import DraftingState
from ._utils import _as_dict


# Section ID → display heading
_SECTION_HEADINGS: Dict[str, str] = {
    "court_heading": "",  # No extra heading — content IS the heading
    "title": "",  # No extra heading — content IS the title
    "parties": "",  # Parties are part of heading block
    "jurisdiction": "JURISDICTION",
    "facts": "FACTS OF THE CASE",
    "legal_basis": "LEGAL BASIS",
    "cause_of_action": "CAUSE OF ACTION",
    "limitation": "LIMITATION",
    "valuation_court_fee": "VALUATION AND COURT FEE",
    "interest": "INTEREST",
    "prayer": "PRAYER",
    "document_list": "LIST OF DOCUMENTS",
    "verification": "VERIFICATION",
    # Criminal
    "grounds": "GROUNDS",
    # Constitutional
    "fundamental_rights": "FUNDAMENTAL RIGHTS VIOLATED",
    "no_alternative_remedy": "NO ALTERNATIVE REMEDY",
    "interim_relief": "INTERIM RELIEF",
    # Response
    "preliminary_objections": "PRELIMINARY OBJECTIONS",
    "parawise_reply": "PARA-WISE REPLY",
    "additional_facts": "ADDITIONAL FACTS",
    "legal_grounds": "LEGAL GROUNDS",
}

# Deterministic advocate block
_ADVOCATE_BLOCK = """
Through:
{{ADVOCATE_NAME}}
Advocate
Enrollment No. {{ADVOCATE_ENROLLMENT}}
{{ADVOCATE_ADDRESS}}
"""


def _collect_placeholders(text: str) -> List[Dict[str, str]]:
    """Find all {{PLACEHOLDER}} patterns in text."""
    placeholders: List[Dict[str, str]] = []
    seen: set = set()
    for m in re.finditer(r"\{\{(\w+)\}\}", text):
        key = m.group(1)
        if key not in seen:
            seen.add(key)
            placeholders.append({"key": key, "reason": "Detail not provided — verify before filing"})
    return placeholders


def _collect_flags(text: str) -> List[str]:
    """Find all [[FLAG]] markers in text."""
    flags: List[str] = []
    for m in re.finditer(r"\[\[([^\]]+)\]\]", text):
        flags.append(m.group(1))
    return flags


def _fix_paragraph_breaks(text: str) -> str:
    """Split run-together numbered paragraphs into separate lines.

    LLMs often output "4. First para. 5. Second para." as one continuous
    string inside a JSON value. This inserts newlines before each numbered
    paragraph start so the assembled document reads correctly.
    """
    # Insert \n\n before numbered paragraph starts that are NOT at line start
    # Pattern: non-newline char + space + digit(s) + period + space
    text = re.sub(r"(?<!\n)(\s)(\d+\.\s)", r"\n\n\2", text)
    return text


def _fix_annexure_list(text: str) -> str:
    """Split semicolon-separated annexure items into separate lines.

    LLMs often output "Annexure A - doc; Annexure B - doc;" as one line.
    """
    # Only apply within the document list section
    # Split on "; Annexure" or "; annexure" pattern
    text = re.sub(r";\s*(Annexure\s)", r";\n\n\1", text, flags=re.IGNORECASE)
    return text


def _fix_prayer_items(text: str) -> str:
    """Ensure prayer sub-items (a), (b), (c) are on separate lines."""
    # Split run-together prayer items: "...relief; (b) Award..." → newline before (b)
    text = re.sub(r";\s*\(([a-z])\)", r";\n(\1)", text)
    # Also handle period before prayer item: "...suit. (b) Award..."
    text = re.sub(r"\.\s+\(([b-z])\)", r".\n(\1)", text)
    return text


def _clean_encoding_artifacts(text: str) -> str:
    """Remove encoding artifacts like replacement character."""
    # Unicode replacement character from bad encoding
    text = text.replace("\ufffd", "-")
    # Zero-width chars
    text = text.replace("\u200b", "").replace("\u200c", "")
    return text


def assembler_node(state: DraftingState) -> Command:
    """Render section-keyed JSON into formatted document."""
    logger.info("[ASSEMBLER] ▶ start")
    t0 = time.perf_counter()

    filled_sections = state.get("filled_sections") or {}
    classify = _as_dict(state.get("classify"))
    doc_type = classify.get("doc_type", "legal_document")

    # Handle both dict (v4.0) and list (v3.0 legacy) formats
    if isinstance(filled_sections, list):
        # Legacy format: list of {section_id, heading, text}
        parts: List[str] = []
        for sec in filled_sections:
            if isinstance(sec, dict):
                heading = (sec.get("heading") or "").strip()
                text = (sec.get("text") or "").strip()
                if text:
                    if heading:
                        parts.append(f"\n{heading}\n")
                    parts.append(text)
                    parts.append("")
        full_text = "\n".join(parts).strip()
    elif isinstance(filled_sections, dict):
        # v4.0 format: {section_id: section_text}
        parts = []
        # Render in a sensible order — use all keys that exist
        ordered_keys = [
            "court_heading", "title", "parties", "jurisdiction", "facts",
            "legal_basis", "cause_of_action", "limitation",
            "valuation_court_fee", "interest", "prayer",
            "document_list", "verification",
            # Criminal/constitutional/family/response extras
            "grounds", "fundamental_rights", "no_alternative_remedy",
            "interim_relief", "preliminary_objections", "parawise_reply",
            "additional_facts", "legal_grounds",
        ]
        # Render ordered keys first, then any remaining keys
        rendered = set()
        for key in ordered_keys:
            sec_text = filled_sections.get(key, "")
            if isinstance(sec_text, str) and sec_text.strip():
                sec_text = sec_text.strip()
                # Apply section-specific formatting fixes
                if key in ("facts", "jurisdiction", "legal_basis",
                           "cause_of_action", "limitation", "interest",
                           "valuation_court_fee", "grounds",
                           "preliminary_objections", "additional_facts"):
                    sec_text = _fix_paragraph_breaks(sec_text)
                elif key == "document_list":
                    sec_text = _fix_paragraph_breaks(sec_text)
                    sec_text = _fix_annexure_list(sec_text)
                elif key == "prayer":
                    sec_text = _fix_prayer_items(sec_text)
                sec_text = _clean_encoding_artifacts(sec_text)

                heading = _SECTION_HEADINGS.get(key, key.upper().replace("_", " "))
                if heading:
                    parts.append(f"\n{heading}\n")
                parts.append(sec_text)
                parts.append("")
                rendered.add(key)

        # Any extra keys not in our ordered list
        for key, sec_text in filled_sections.items():
            if key not in rendered and isinstance(sec_text, str) and sec_text.strip():
                sec_text = _fix_paragraph_breaks(sec_text.strip())
                sec_text = _clean_encoding_artifacts(sec_text)
                heading = key.upper().replace("_", " ")
                parts.append(f"\n{heading}\n")
                parts.append(sec_text)
                parts.append("")

        full_text = "\n".join(parts).strip()
        # Final cleanup: collapse triple+ blank lines to double
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)

        # Append advocate block if not already present
        if "advocate" not in full_text.lower() and "enrollment" not in full_text.lower():
            full_text += "\n" + _ADVOCATE_BLOCK.strip()
    else:
        logger.error("[ASSEMBLER] unexpected filled_sections type: %s", type(filled_sections))
        return Command(goto="draft")

    if not full_text.strip():
        logger.error("[ASSEMBLER] assembled text is empty — fallback to old draft")
        return Command(goto="draft")

    # Collect metadata
    placeholders = _collect_placeholders(full_text)
    flags = _collect_flags(full_text)

    # Extract title from assembled text (first non-empty heading-like line)
    title = doc_type.replace("_", " ").title()
    title_text = filled_sections.get("title", "") if isinstance(filled_sections, dict) else ""
    if isinstance(title_text, str) and title_text.strip():
        first_line = title_text.strip().split("\n")[0].strip()
        if first_line:
            title = first_line

    draft_artifact = {
        "doc_type": doc_type,
        "title": title,
        "text": full_text,
        "placeholders_used": placeholders,
        "citations_used": [],
    }

    section_count = len([
        k for k, v in (filled_sections.items() if isinstance(filled_sections, dict) else [])
        if isinstance(v, str) and v.strip()
    ]) if isinstance(filled_sections, dict) else len(filled_sections)

    elapsed = time.perf_counter() - t0
    logger.info(
        "[ASSEMBLER] ✓ done (%.1fs) | sections=%d | placeholders=%d | flags=%d | chars=%d",
        elapsed, section_count, len(placeholders), len(flags), len(full_text),
    )

    return Command(
        update={
            "draft": {"draft_artifacts": [draft_artifact]},
        },
        goto="evidence_anchoring",
    )
