"""Section Fixer prompts — patch-only mode.

Input: section body text + specific issue + relevant context
Output: corrected section body ONLY (no heading, no annexure list)
"""
from __future__ import annotations

from typing import Any, Dict


def build_fixer_system_prompt() -> str:
    """System prompt for section fixer — patch-only, no rewrites."""
    return """CRITICAL: Return ONLY the corrected section body text. No JSON, no markdown fences, no preamble, no explanations.

You are a legal drafting correction specialist. Your ONLY job is to apply a SPECIFIC fix to a section of a legal draft.

RULES:
- Apply ONLY the fix described in FIX_INSTRUCTION
- Do NOT rewrite, restructure, or improve other parts of the section
- Do NOT add new facts, dates, amounts, or names not in the provided context
- Do NOT add case law citations
- Use {{PLACEHOLDER_NAME}} for any missing detail
- Preserve all existing correct content
- Do NOT change the heading or section structure
- The output must be the COMPLETE corrected section body (not just the changed part)"""


def build_fixer_user_prompt(
    *,
    section_id: str,
    section_text: str,
    issue_type: str,
    fix_instruction: str,
    quote: str,
    context: str,
) -> str:
    """User prompt for fixing a specific issue in a section."""
    parts = [
        f"Fix the following issue in the \"{section_id}\" section.\n",
        f"ISSUE TYPE: {issue_type}",
        f"FIX INSTRUCTION: {fix_instruction}",
    ]

    if quote:
        parts.append(f"QUOTE (exact text with the issue): \"{quote}\"")

    parts.append(f"\nCONTEXT:\n{context}")
    parts.append(f"\nCURRENT SECTION TEXT:\n{section_text}")
    parts.append("\nReturn the COMPLETE corrected section body text.")

    return "\n".join(parts)
