"""Postprocess Node — deterministic (NO LLM).

Safe auto-fixes ONLY:
- Numbering continuity
- Annexure label mapping
- Heading casing/spacing
- Placeholder normalization (from registry)

NEVER auto-fixes substance (limitation reasoning, legal arguments, interest rates).

Pipeline position: evidence_anchoring → **postprocess** → citation_validator
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langgraph.types import Command

from langgraph.graph import END

from ....config import logger, settings
from ..states import DraftingState
from ._utils import _as_dict

# Load placeholder registry for alias normalization
_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "config" / "placeholder_registry.json"
_ALIAS_MAP: Dict[str, str] = {}
try:
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
    for canonical, info in registry.get("placeholders", {}).items():
        for alias in info.get("aliases", []):
            _ALIAS_MAP[alias] = canonical
except (FileNotFoundError, json.JSONDecodeError):
    pass


def _normalize_placeholders(text: str) -> Tuple[str, int]:
    """Replace alias placeholders with canonical names. Returns (text, count)."""
    count = 0
    for alias, canonical in _ALIAS_MAP.items():
        pattern = "{{" + alias + "}}"
        if pattern in text:
            text = text.replace(pattern, "{{" + canonical + "}}")
            count += 1
    return text, count


def _fix_escaped_placeholders(text: str) -> Tuple[str, int]:
    """Collapse accidentally escaped placeholder braces back to canonical form."""
    fixed = re.sub(r"\{\{\{\{([A-Z0-9_]+)\}\}\}\}", r"{{\1}}", text)
    return fixed, 1 if fixed != text else 0


def _fix_mid_word_placeholders(text: str) -> Tuple[str, int]:
    """Fix placeholders that are fused to adjacent word characters.

    LLMs sometimes produce "several yea{{AMOUNT}}" or "{{DATE}}onwards"
    when they confuse placeholder syntax with natural text. This inserts
    a space between the word character and the placeholder braces.
    """
    count = 0
    # word char immediately before {{ → insert space
    fixed = re.sub(r"(\w)(\{\{)", r"\1 \2", text)
    count += (len(fixed) - len(text))  # rough count
    # }} immediately before word char → insert space
    text = fixed
    fixed = re.sub(r"(\}\})(\w)", r"\1 \2", text)
    count += (len(fixed) - len(text))
    return fixed, max(count, 0)


def _flag_incomplete_sentences(text: str) -> List[Dict[str, Any]]:
    """Detect sentences that appear truncated (ending mid-phrase).

    LLMs producing full-document JSON sometimes rush later sections,
    leaving sentences cut off at prepositions, articles, or "Section".
    Flags only — does NOT auto-fix (substance).
    """
    issues: List[Dict[str, Any]] = []
    # Split on line breaks to check each paragraph
    for line in text.split("\n"):
        stripped = line.rstrip()
        if not stripped or len(stripped) < 20:
            continue
        # Skip placeholders, headings, and table rows
        if stripped.endswith("}}") or stripped == stripped.upper() or "|" in stripped:
            continue
        # Check if line ends with a truncation indicator
        # (preposition, article, conjunction, or "Section"/"under" without completion)
        trunc = re.search(
            r"\b(under|under\s+Section|of|the|in|at|by|for|and|or|to|from|with|that|which|Section)\s*$",
            stripped,
        )
        if trunc:
            issues.append({
                "type": "incomplete_sentence",
                "severity": "non_blocking",
                "match": stripped[-60:],
                "description": f"Possible truncated sentence ending with '{trunc.group()}' — review for completeness",
            })
    return issues


def _fix_paragraph_breaks(text: str) -> Tuple[str, int]:
    """Split run-together numbered paragraphs into separate lines.

    LLMs often output "4. First para. 5. Second para." as one continuous
    string. This inserts newlines before each numbered paragraph start.
    """
    original = text
    # Insert \n\n before numbered paragraph starts that are NOT at line start
    text = re.sub(r"(?<!\n)(\s)(\d+\.\s)", r"\n\n\2", text)
    fixes = 1 if text != original else 0
    return text, fixes


def _fix_paragraph_number_spacing(text: str) -> Tuple[str, int]:
    """Normalize numbered paragraphs from `1.Text` to `1. Text`."""
    fixed = re.sub(r"(?m)^(\s*\d+)\.(\S)", r"\1. \2", text)
    return fixed, 1 if fixed != text else 0


def _fix_split_act_years(text: str) -> Tuple[str, int]:
    """Join stray act-year lines like `Code of Civil Procedure,` + `1908.`."""
    fixed = re.sub(r"(Code of Civil Procedure,)\s*\n+\s*(1908\.)", r"\1 \2", text)
    fixed = re.sub(r"([A-Za-z][A-Za-z\s]+Act,)\s*\n+\s*((?:18|19|20)\d{2}\.)", r"\1 \2", fixed)
    return fixed, 1 if fixed != text else 0


def _repair_breach_heading_runon(text: str) -> Tuple[str, int]:
    """Repair common run-together breach heading corruption before numbering."""
    lines = text.split("\n")
    fixed: List[str] = []
    fixes = 0

    for line in lines:
        stripped = line.strip()
        match = re.match(
            r"^(BREACH\s+PARTICULA\w*)(?:\s+\{\{[A-Z0-9_]+\}\}\.)?\s*(.+)$",
            stripped,
            flags=re.IGNORECASE,
        )
        if match and match.group(2):
            prev_num = 0
            for prior in reversed(fixed):
                num_match = re.match(r"^\s*(\d+)\.\s", prior)
                if num_match:
                    prev_num = int(num_match.group(1))
                    break
            next_num = prev_num + 1 if prev_num else 1
            fixed.append("BREACH PARTICULARS")
            fixed.append("")
            fixed.append(f"{next_num}. {match.group(2).strip()}")
            fixes += 1
            continue
        fixed.append(line)

    return "\n".join(fixed), fixes


def _fix_prayer_items(text: str) -> Tuple[str, int]:
    """Ensure prayer sub-items (a), (b), (c) are on separate lines."""
    original = text
    # Split run-together prayer items: "...relief; (b) Award..." → newline before (b)
    text = re.sub(r";\s*\(([a-z])\)", r";\n(\1)", text)
    # Also handle period before prayer item: "...suit. (b) Award..."
    text = re.sub(r"\.\s+\(([b-z])\)", r".\n(\1)", text)
    fixes = 1 if text != original else 0
    return text, fixes


def _fix_annexure_list_breaks(text: str) -> Tuple[str, int]:
    """Split semicolon-separated annexure items into separate lines."""
    original = text
    text = re.sub(r";\s*(Annexure\s)", r";\n\n\1", text, flags=re.IGNORECASE)
    fixes = 1 if text != original else 0
    return text, fixes


def _collapse_blank_lines(text: str) -> Tuple[str, int]:
    """Collapse 3+ consecutive blank lines to 2."""
    original = text
    text = re.sub(r"\n{3,}", "\n\n", text)
    fixes = 1 if text != original else 0
    return text, fixes


def _strip_trailing_whitespace(text: str) -> Tuple[str, int]:
    """Strip trailing whitespace from each line."""
    lines = text.split("\n")
    fixed = [line.rstrip() for line in lines]
    fixes = sum(1 for a, b in zip(lines, fixed) if a != b)
    return "\n".join(fixed), fixes


def _fix_numbering(text: str) -> Tuple[str, int]:
    """Fix paragraph numbering continuity — CONTINUOUS across entire document.

    Does NOT reset numbering on section headings. Paragraphs are numbered
    1, 2, 3... through the whole plaint as required by court filing standards.
    Skips renumbering inside PRAYER sections (which use (a), (b), (c)).
    """
    lines = text.split("\n")
    fixed_lines: List[str] = []
    expected = 1
    fixes = 0
    in_prayer = False

    for line in lines:
        stripped = line.strip()

        # Detect ALL-CAPS heading (do NOT reset numbering — keep continuous)
        if (
            stripped
            and stripped == stripped.upper()
            and len(stripped) < 80
            and "{{" not in stripped
            and not stripped.startswith(("(", "•", "-"))
            and len(stripped) > 3
        ):
            in_prayer = stripped in ("PRAYER", "PRAYERS", "PRAYER CLAUSE")
            fixed_lines.append(line)
            continue

        # Skip renumbering inside PRAYER sections
        if in_prayer:
            fixed_lines.append(line)
            continue

        # Match numbered paragraph starts: "1.", "2.", etc.
        m = re.match(r"^(\s*)(\d+)\.\s", line)
        if m:
            indent = m.group(1)
            actual = int(m.group(2))
            if actual != expected:
                line = f"{indent}{expected}. {line[m.end():]}"
                fixes += 1
            expected += 1
        fixed_lines.append(line)

    return "\n".join(fixed_lines), fixes


def _fix_annexure_labels(text: str) -> Tuple[str, int]:
    """Ensure annexure references in body match the document list section."""
    # Find all annexure references
    body_refs = set(re.findall(r"Annexure[\s-]+([A-Z](?:\d+)?)", text, re.IGNORECASE))
    # No auto-fix logic needed for first pass — just count for reporting
    return text, 0


def _fix_and_or(text: str) -> Tuple[str, int]:
    """Replace 'and/or' with 'and' or 'or' (professional drafting standard).

    Heuristic: In legal drafting, 'and/or' is almost always replaceable
    with 'and'. Only exception: if preceded by a clear disjunctive context.
    We default to 'and' since it's the safer legal choice.
    """
    count = 0
    # "failed and/or neglected" → "failed and neglected"
    # "refused and/or failed"  → "refused and failed"
    result = text
    and_or_pattern = re.compile(r"\band/or\b", re.IGNORECASE)
    matches = list(and_or_pattern.finditer(result))
    count = len(matches)
    if count:
        result = and_or_pattern.sub("and", result)
    return result, count


# Anti-patterns: drafting-notes language that must NEVER appear in a filed document
_DRAFTING_NOTES_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bto\s+be\s+verif(?:ied|y)\b",
        r"\bplaceholder\b",
        r"\bto\s+be\s+enter(?:ed|ing)\b",
        r"\bto\s+be\s+calculat(?:ed|ing)\b",
        r"\bto\s+be\s+fill(?:ed|ing)\b",
        r"\bas\s+per\s+records?\b",
        r"\bdetails?\s+to\s+follow\b",
        r"\binsert\s+(?:here|date|name|amount)\b",
        r"\b(?:TBD|TBC|TODO)\b",
        r"\bneed(?:s|ed)?\s+to\s+(?:be\s+)?(?:confirm|verif|check)\b",
    ]
]


def _flag_drafting_notes(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Detect drafting-notes language that should never appear in a filed plaint.

    Does NOT auto-fix (substance) — only flags for review.
    Context-aware: legal phrases like "interest to be calculated from..." are NOT flagged.
    Returns (text_unchanged, issues_found).
    """
    # Words before/after "to be calculated" that indicate legal context (not a drafting note)
    _CALC_LEGAL_BEFORE = {"interest", "amount", "sum", "rate", "damages", "compensation", "costs"}
    _CALC_LEGAL_AFTER = {"from", "until", "at", "on", "per", "and", "as", "till", "upto"}

    issues: List[Dict[str, Any]] = []
    for pattern in _DRAFTING_NOTES_PATTERNS:
        for m in pattern.finditer(text):
            matched = m.group().lower()

            # Context-aware check for "to be calculated" — skip if in legal context
            if "calculat" in matched:
                # Check 60 chars before and 30 chars after for legal context
                before = text[max(0, m.start() - 60):m.start()].lower()
                after = text[m.end():min(len(text), m.end() + 30)].lower()
                before_words = set(before.split())
                after_words = after.split()
                first_after = after_words[0] if after_words else ""
                if before_words & _CALC_LEGAL_BEFORE or first_after in _CALC_LEGAL_AFTER:
                    continue  # Legal context — not a drafting note

            issues.append({
                "type": "drafting_notes_language",
                "severity": "blocking",
                "match": m.group(),
                "position": m.start(),
                "description": f"Drafting-notes language detected: '{m.group()}' — must not appear in a filed document",
            })
    return text, issues


def _detect_repetition(text: str) -> List[Dict[str, Any]]:
    """Detect phrases repeated more than 3 times in the document.

    Flags repetition but does NOT auto-fix (substance).
    """
    issues: List[Dict[str, Any]] = []
    # Normalize for comparison
    t = " ".join(text.lower().split())

    # Check for common repetitive phrases (3+ word phrases occurring 4+ times)
    words = t.split()
    if len(words) < 20:
        return issues

    # Count 3-gram frequencies
    trigram_counts: Dict[str, int] = {}
    for i in range(len(words) - 2):
        trigram = " ".join(words[i:i+3])
        # Skip very common legal phrases that are expected to repeat
        if trigram in ("of the court", "the code of", "code of civil",
                       "of civil procedure", "the said amount",
                       "per cent per", "cent per annum",
                       "the plaintiff and", "and against the"):
            continue
        trigram_counts[trigram] = trigram_counts.get(trigram, 0) + 1

    for phrase, count in trigram_counts.items():
        if count >= 4:
            issues.append({
                "type": "excessive_repetition",
                "severity": "non_blocking",
                "description": f"Phrase '{phrase}' repeated {count} times — consider varying language",
            })

    return issues


def _strip_protocol_markers(text: str) -> Tuple[str, int]:
    """Remove LLM protocol markers that should never appear in output."""
    markers = ["---SECTION_TEXT---", "---CLAIM_LEDGER---"]
    count = 0
    for marker in markers:
        occurrences = text.count(marker)
        if occurrences:
            text = text.replace(marker, "")
            count += occurrences
    if count:
        # Clean up double blank lines left by marker removal
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text, count


def _fix_spaced_out_titles(text: str) -> Tuple[str, int]:
    """Collapse spaced-out ALL-CAPS titles like 'S U I T  F O R  D A M A G E S'.

    LLMs sometimes produce decorative spacing in title lines. This collapses
    single-char-spaced words back to normal: 'S U I T  F O R' → 'SUIT FOR'.
    Handles mixed content (letters, digits, punctuation) as long as the line
    is predominantly single-spaced uppercase characters.
    """
    fixes = 0
    lines = text.split("\n")
    fixed: List[str] = []
    for line in lines:
        stripped = line.strip()
        # Detect: predominantly single uppercase letters separated by spaces
        # Must be at least 20 chars (avoids false positives on short lines)
        # Allow digits, commas, periods mixed in
        if len(stripped) >= 20:
            # Count single-char tokens separated by single spaces
            tokens = stripped.split(" ")
            single_char_count = sum(1 for t in tokens if len(t) == 1 and t.isupper())
            # If >60% of tokens are single uppercase letters, it's spaced-out
            if len(tokens) > 5 and single_char_count / len(tokens) > 0.6:
                # Rebuild: collapse runs of single-char tokens into words
                # Non-single-char tokens (like "39", "1872,") stay as-is
                result_parts: List[str] = []
                current_word: List[str] = []
                for t in tokens:
                    if len(t) == 1 and (t.isupper() or t == ","):
                        current_word.append(t)
                    else:
                        if current_word:
                            result_parts.append("".join(current_word))
                            current_word = []
                        result_parts.append(t)
                if current_word:
                    result_parts.append("".join(current_word))
                collapsed = " ".join(result_parts)
                if collapsed != stripped:
                    line = line.replace(stripped, collapsed)
                    fixes += 1
        fixed.append(line)
    return "\n".join(fixed), fixes


def _fix_heading_spacing(text: str) -> Tuple[str, int]:
    """Ensure consistent blank lines before headings."""
    fixes = 0
    # Add blank line before ALL-CAPS headings that don't have one
    lines = text.split("\n")
    fixed: List[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Detect heading: ALL CAPS, short, not a placeholder
        if (
            stripped
            and stripped == stripped.upper()
            and len(stripped) < 80
            and "{{" not in stripped
            and i > 0
            and fixed
            and fixed[-1].strip()
        ):
            fixed.append("")
            fixes += 1
        fixed.append(line)
    return "\n".join(fixed), fixes


def _strip_leaked_instructions(text: str) -> Tuple[str, int]:
    """Remove drafting instruction text that the LLM copied verbatim from the prompt.

    Patterns like 'PLACEMENT: after PRAYER', 'WHAT TO WRITE:', 'INSTRUCTION:' are
    prompt directives — not legal content. Remove lines that match these patterns.
    Also removes meta-notes like 'Note: All factual assertions herein...' which are
    LLM self-commentary, not court-filing content.
    """
    fixes = 0
    lines = text.split("\n")
    fixed: List[str] = []
    _instruction_patterns = re.compile(
        r"^\s*(?:PLACEMENT:\s|WHAT TO WRITE:\s|INSTRUCTION:\s|"
        r"Note:\s+(?:All|The|This|These)\s)", re.IGNORECASE
    )
    for line in lines:
        if _instruction_patterns.match(line):
            fixes += 1
            continue  # skip the line entirely
        fixed.append(line)
    return "\n".join(fixed), fixes


def _strip_duplicate_advocate_block(text: str) -> Tuple[str, int]:
    """Remove duplicate advocate blocks — keep only the first occurrence.

    LLMs sometimes output the advocate block twice: once after verification
    (correct) and once at the very end under 'ADVOCATE BLOCK' or
    'ADVOCATE FOR THE PLAINTIFF' heading. Remove the second occurrence.
    """
    # Find all advocate block occurrences (Through: + name + Advocate + Enrollment)
    pattern = re.compile(
        r"(?:ADVOCATE\s+(?:BLOCK|FOR\s+THE\s+PLAINTIFF)\s*\n+)?"
        r"(?:Through:\s*\n)?"
        r"\{\{ADVOCATE_NAME\}\}\s*\n"
        r"(?:Advocate\s*\n)?"
        r"Enrollment\s+No\.\s*\{\{ADVOCATE_ENROLLMENT\}\}",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(text))
    if len(matches) <= 1:
        return text, 0

    # Keep the first, remove subsequent
    # Remove from the last match's broader context backwards
    for match in reversed(matches[1:]):
        # Expand to capture the full block including heading and address
        start = match.start()
        end = match.end()
        # Look backwards for heading
        before = text[:start].rstrip()
        for heading in ("ADVOCATE BLOCK", "ADVOCATE FOR THE PLAINTIFF"):
            idx = before.rfind(heading)
            if idx >= 0 and len(before) - idx < 60:
                start = idx
                break
        # Look forward for address placeholder
        after_text = text[end:]
        addr_match = re.match(r"\s*\n\{\{ADVOCATE_ADDRESS\}\}", after_text)
        if addr_match:
            end += addr_match.end()
        text = text[:start].rstrip() + text[end:]

    return text, len(matches) - 1


def postprocess_node(state: DraftingState) -> Command:
    """Apply safe deterministic fixes to the assembled draft."""
    logger.info("[POSTPROCESS] ▶ start")
    t0 = time.perf_counter()

    draft = _as_dict(state.get("draft"))
    artifacts = draft.get("draft_artifacts", [])

    if not artifacts:
        logger.error("[POSTPROCESS] no draft artifacts — skipping")
        return Command(goto="citation_validator")

    light_mode = state.get("postprocess_light", False)
    issues: List[Dict[str, Any]] = []
    total_fixes = 0

    processed_artifacts: List[Dict[str, Any]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            processed_artifacts.append(artifact)
            continue

        text = artifact.get("text", "")

        # 0. Strip LLM protocol markers (safe, always applied)
        text, marker_fixes = _strip_protocol_markers(text)
        if marker_fixes:
            issues.append({"type": "protocol_markers_stripped", "count": marker_fixes})
            total_fixes += marker_fixes

        # 0.5. Fix mid-word placeholders (safe — adds space only, always applied)
        text, escaped_placeholder_fixes = _fix_escaped_placeholders(text)
        if escaped_placeholder_fixes:
            issues.append({"type": "escaped_placeholders_fixed", "count": escaped_placeholder_fixes})
            total_fixes += escaped_placeholder_fixes

        text, midword_fixes = _fix_mid_word_placeholders(text)
        if midword_fixes:
            issues.append({"type": "mid_word_placeholder_fixed", "count": midword_fixes})
            total_fixes += midword_fixes

        # 1. Placeholder normalization
        text, placeholder_fixes = _normalize_placeholders(text)
        if placeholder_fixes:
            issues.append({"type": "placeholder_normalized", "count": placeholder_fixes})
            total_fixes += placeholder_fixes

        # 2. Clean "and/or" → "and" (safe deterministic fix, always applied)
        text, and_or_fixes = _fix_and_or(text)
        if and_or_fixes:
            issues.append({"type": "and_or_fixed", "count": and_or_fixes})
            total_fixes += and_or_fixes

        if not light_mode:
            # 2.5. Fix spaced-out titles (S U I T → SUIT)
            text, spaced_fixes = _fix_spaced_out_titles(text)
            if spaced_fixes:
                issues.append({"type": "spaced_out_title_fixed", "count": spaced_fixes})
                total_fixes += spaced_fixes

            # 2.6. Strip leaked instruction text (PLACEMENT:, Note:, etc.)
            text, instruction_fixes = _strip_leaked_instructions(text)
            if instruction_fixes:
                issues.append({"type": "leaked_instructions_stripped", "count": instruction_fixes})
                total_fixes += instruction_fixes

            # 2.7. Remove duplicate advocate blocks
            text, advocate_fixes = _strip_duplicate_advocate_block(text)
            if advocate_fixes:
                issues.append({"type": "duplicate_advocate_block_removed", "count": advocate_fixes})
                total_fixes += advocate_fixes

            # 2.8. Split run-together numbered paragraphs
            text, para_fixes = _fix_paragraph_breaks(text)
            if para_fixes:
                issues.append({"type": "paragraph_breaks_fixed", "count": para_fixes})
                total_fixes += para_fixes

            text, para_space_fixes = _fix_paragraph_number_spacing(text)
            if para_space_fixes:
                issues.append({"type": "paragraph_number_spacing_fixed", "count": para_space_fixes})
                total_fixes += para_space_fixes

            text, breach_heading_fixes = _repair_breach_heading_runon(text)
            if breach_heading_fixes:
                issues.append({"type": "breach_heading_runon_fixed", "count": breach_heading_fixes})
                total_fixes += breach_heading_fixes

            text, split_year_fixes = _fix_split_act_years(text)
            if split_year_fixes:
                issues.append({"type": "split_act_years_fixed", "count": split_year_fixes})
                total_fixes += split_year_fixes

            # 2.9. Split run-together prayer sub-items
            text, prayer_fixes = _fix_prayer_items(text)
            if prayer_fixes:
                issues.append({"type": "prayer_items_fixed", "count": prayer_fixes})
                total_fixes += prayer_fixes

            # 2.10. Split semicolon-separated annexure items
            text, annex_fixes = _fix_annexure_list_breaks(text)
            if annex_fixes:
                issues.append({"type": "annexure_list_fixed", "count": annex_fixes})
                total_fixes += annex_fixes

            # 2.11. Collapse 3+ blank lines to 2
            text, blank_fixes = _collapse_blank_lines(text)
            if blank_fixes:
                issues.append({"type": "blank_lines_collapsed", "count": blank_fixes})
                total_fixes += blank_fixes

            # 2.12. Strip trailing whitespace
            text, ws_fixes = _strip_trailing_whitespace(text)
            if ws_fixes:
                issues.append({"type": "trailing_whitespace_stripped", "count": ws_fixes})
                total_fixes += ws_fixes

            # 3. Numbering continuity (section-aware)
            text, numbering_fixes = _fix_numbering(text)
            if numbering_fixes:
                issues.append({"type": "numbering_fixed", "count": numbering_fixes})
                total_fixes += numbering_fixes

            # 3.5. Resolve {{LAST_PARA}} / {{LAST_PARA_NUMBER}} in verification/SOT
            para_nums = [int(m.group(1)) for m in re.finditer(r"^\s*(\d+)\.\s", text, re.MULTILINE)]
            _last_para_variants = ("{{LAST_PARA}}", "{{LAST_PARA_NUMBER}}", "{{LAST_PARAGRAPH}}")
            if any(v in text for v in _last_para_variants):
                last_para = max(para_nums) if para_nums else 0
                if last_para > 0:
                    for v in _last_para_variants:
                        if v in text:
                            text = text.replace(v, str(last_para))
                    total_fixes += 1
                    issues.append({"type": "verification_para_count_fixed", "count": 1})

            # 3.6. Fix stale "paragraphs 1 to N" where N doesn't match actual count
            _stale_m = re.search(r"paragraphs\s+1\s+to\s+(\d+)", text)
            if _stale_m and para_nums:
                _stated = int(_stale_m.group(1))
                _actual = max(para_nums) if para_nums else _stated
                if _stated != _actual and _actual > 0:
                    text = text.replace(
                        f"paragraphs 1 to {_stated}",
                        f"paragraphs 1 to {_actual}",
                    )
                    total_fixes += 1

            # 4. Heading spacing
            text, spacing_fixes = _fix_heading_spacing(text)
            if spacing_fixes:
                issues.append({"type": "heading_spacing_fixed", "count": spacing_fixes})
                total_fixes += spacing_fixes

            # 5. Annexure label check
            text, annexure_fixes = _fix_annexure_labels(text)
            if annexure_fixes:
                issues.append({"type": "annexure_fixed", "count": annexure_fixes})
                total_fixes += annexure_fixes

            # 6. Flag drafting-notes language (NOT auto-fixed — flagged for review)
            text, notes_issues = _flag_drafting_notes(text)
            if notes_issues:
                issues.extend(notes_issues)

            # 7. Detect excessive repetition (NOT auto-fixed — informational)
            rep_issues = _detect_repetition(text)
            if rep_issues:
                issues.extend(rep_issues)

            # 8. Detect incomplete/truncated sentences (NOT auto-fixed — flagged)
            trunc_issues = _flag_incomplete_sentences(text)
            if trunc_issues:
                issues.extend(trunc_issues)

        processed = {**artifact, "text": text}
        processed_artifacts.append(processed)

    # Decide: skip review if draft is clean (saves ~130s LLM call).
    # Clean = section_validator found 0 blocking issues + all must_include passed +
    # postprocess found no drafting-notes blocking issues.
    skip_review = False
    if getattr(settings, "DRAFTING_SKIP_REVIEW_IF_CLEAN", False) and not light_mode:
        blocking_issues = [i for i in issues if i.get("severity") == "blocking"]
        filled_sections = state.get("filled_sections", [])
        all_must_include_passed = all(
            s.get("must_include_passed", True)
            for s in filled_sections
            if isinstance(s, dict)
        )
        # Count only blocking validator issues — replaced items are already handled by
        # validator (Tier A safe replacement), warnings (quality hints) don't need LLM review
        validator_blocking = sum(
            1
            for s in filled_sections
            if isinstance(s, dict)
            for vi in s.get("validation_issues", [])
            if isinstance(vi, dict) and vi.get("severity") == "blocking"
        )
        logger.info(
            "[POSTPROCESS] skip-review check: pp_blocking=%d | mi_passed=%s | val_blocking=%d",
            len(blocking_issues), all_must_include_passed, validator_blocking,
        )
        if not blocking_issues and all_must_include_passed and validator_blocking == 0:
            skip_review = True

    elapsed = time.perf_counter() - t0

    draft_update = {"draft_artifacts": processed_artifacts}
    update: Dict[str, Any] = {
        "draft": draft_update,
        "postprocess_issues": issues,
    }

    if skip_review:
        logger.info(
            "[POSTPROCESS] ✓ done (%.1fs) | fixes=%d | issues=%d | SKIP REVIEW (clean draft)",
            elapsed, total_fixes, len(issues),
        )
        update["final_draft"] = draft_update
        return Command(update=update, goto=END)
    else:
        logger.info(
            "[POSTPROCESS] ✓ done (%.1fs) | fixes=%d | issues=%d | light=%s → citation_validator",
            elapsed, total_fixes, len(issues), light_mode,
        )
        return Command(update=update, goto="citation_validator")
