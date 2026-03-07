"""Section Drafter Node — LLM, per-section.

Drafts all sections CONCURRENTLY via asyncio.gather:
- template → inject body directly, zero LLM
- template_with_fill / llm_fill → LLM generates with focused prompt
- Parses claim ledger from LLM output
- Validates must_include patterns (max 2 retries)

Concurrency cuts wall-clock time from ~9 min (sequential) to ~2-3 min.

Pipeline position: outline_validator → **section_drafter** → section_validator
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from ....config import logger, settings
from ....services import draft_ollama_model as draft_openai_model
from ..prompts.section_drafter import build_section_system_prompt, build_section_user_prompt
from ..states import DraftingState
from ._utils import _as_dict

_MAX_SECTION_RETRIES = getattr(settings, "DRAFTING_MAX_SECTION_RETRIES", 2)


def _check_section_condition(section: Dict[str, Any], doc_type: str) -> bool:
    """Check if a section's condition is met. Returns True if section should be included.

    Condition format: "doc_type_contains:keyword1|keyword2|keyword3"
    If no condition → always include.
    """
    condition = section.get("condition", "")
    if not condition:
        return True

    if condition.startswith("doc_type_contains:"):
        keywords = condition.split(":", 1)[1].split("|")
        dt = (doc_type or "").lower()
        return any(kw.strip().lower() in dt for kw in keywords)

    # Unknown condition type → include by default
    return True


def _check_must_include(text: str, must_include: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Check if text satisfies all must_include patterns. Returns (passed, failures)."""
    if not must_include:
        return True, []

    failures: List[str] = []
    for item in must_include:
        if not item.get("required", True):
            continue

        match_type = item.get("type", "keyword")
        pattern = item.get("match", "")
        desc = item.get("description", pattern)

        if match_type == "keyword":
            if pattern.lower() not in text.lower():
                failures.append(f"keyword missing: {desc}")
        elif match_type == "regex":
            try:
                if not re.search(pattern, text, re.IGNORECASE):
                    failures.append(f"regex not matched: {desc}")
            except re.error:
                pass  # Skip invalid regex
        elif match_type == "concept":
            # Concept check: any word from pattern should appear
            words = [w.strip() for w in pattern.split("|")]
            if not any(w.lower() in text.lower() for w in words if w):
                failures.append(f"concept missing: {desc}")
        elif match_type == "evidence_anchor":
            if pattern.lower() not in text.lower():
                failures.append(f"evidence anchor missing: {desc}")

    return len(failures) == 0, failures


def _parse_section_output(raw: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Parse LLM output into section text and claim ledger.

    Handles the ---SECTION_TEXT--- / ---CLAIM_LEDGER--- format.
    Falls back to treating entire output as section text if format not found.
    """
    text_marker = "---SECTION_TEXT---"
    claims_marker = "---CLAIM_LEDGER---"

    if text_marker in raw:
        # Split on ALL occurrences of both markers to extract text and claims
        # Handle patterns like: [text]---SECTION_TEXT--- or ---SECTION_TEXT---[text]---SECTION_TEXT---
        parts = raw.split(text_marker)
        claims: List[Dict[str, Any]] = []

        if claims_marker in raw:
            # Extract claims from the claims section
            claims_raw = raw.split(claims_marker, 1)[1]
            # Strip any trailing markers from claims
            claims_raw = claims_raw.replace(text_marker, "").strip()
            claims = _parse_claims_json(claims_raw)

        # The text is the longest non-empty part (excluding claims content)
        text_before_claims = raw.split(claims_marker, 1)[0] if claims_marker in raw else raw
        # Remove all marker occurrences
        section_text = text_before_claims.replace(text_marker, "").strip()

        return section_text, claims

    # Fallback: entire output is section text
    # But check if there's a JSON array at the end (claim ledger without markers)
    text = raw.strip()
    claims = []

    # Try to find JSON array at the end
    last_bracket = text.rfind("[")
    if last_bracket > 0 and text.rstrip().endswith("]"):
        possible_json = text[last_bracket:]
        parsed = _parse_claims_json(possible_json)
        if parsed:
            text = text[:last_bracket].strip()
            claims = parsed

    return text, claims


def _parse_claims_json(raw: str) -> List[Dict[str, Any]]:
    """Parse claim ledger JSON from raw text."""
    raw = raw.strip()
    if not raw:
        return []

    # Strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [c for c in data if isinstance(c, dict)]
    except json.JSONDecodeError:
        pass

    # Try to find JSON array
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return [c for c in data if isinstance(c, dict)]
        except json.JSONDecodeError:
            pass

    return []


async def _draft_single_section(
    section: Dict[str, Any],
    intake: Dict[str, Any],
    classify: Dict[str, Any],
    rag: Dict[str, Any],
    mandatory_provisions: Dict[str, Any],
    court_fee: Dict[str, Any],
    template: Dict[str, Any],
    user_request: str = "",
) -> Dict[str, Any]:
    """Draft a single section (async). Returns filled_section dict."""
    sid = section.get("section_id", "?")
    stype = section.get("type", "template")
    heading = section.get("heading", "")

    # Check condition — skip section entirely if condition not met (e.g., interest for injunction suits)
    actual_doc_type = classify.get("doc_type") or template.get("doc_type", "")
    if not _check_section_condition(section, actual_doc_type):
        logger.info("[SECTION_DRAFTER] %s: SKIPPED (condition not met for doc_type=%r)", sid, actual_doc_type)
        return {
            "section_id": sid,
            "heading": heading,
            "text": "",
            "type": stype,
            "claims": [],
            "must_include_passed": True,
            "retries": 0,
            "validation_issues": [],
            "skipped": True,
        }

    # Template sections — inject body directly, no LLM
    if stype == "template":
        body = section.get("body", "")
        logger.info("[SECTION_DRAFTER] %s: template (no LLM)", sid)
        return {
            "section_id": sid,
            "heading": heading,
            "text": body,
            "type": stype,
            "claims": [],
            "must_include_passed": True,
            "retries": 0,
            "validation_issues": [],
        }

    # LLM sections — build prompts and call LLM
    party_labels = template.get("party_labels", {"primary": "Plaintiff", "opposite": "Defendant"})

    # Use the actual classified doc_type (not the template's generic label)
    actual_doc_type = classify.get("doc_type") or template.get("doc_type", "")

    system_prompt = build_section_system_prompt(
        section=section,
        doc_type=actual_doc_type,
        party_labels=party_labels,
    )
    user_prompt = build_section_user_prompt(
        section=section,
        intake=intake,
        classify=classify,
        rag=rag,
        mandatory_provisions=mandatory_provisions,
        court_fee=court_fee,
        template=template,
        user_request=user_request,
    )

    must_include = section.get("must_include", [])
    best_text = ""
    best_claims: List[Dict[str, Any]] = []
    retries = 0

    for attempt in range(_MAX_SECTION_RETRIES + 1):
        t0 = time.perf_counter()
        try:
            is_retry = attempt > 0
            if is_retry:
                # Rebuild system prompt with retry flag
                system_prompt = build_section_system_prompt(
                    section=section,
                    doc_type=actual_doc_type,
                    party_labels=party_labels,
                    is_retry=True,
                )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            response = await draft_openai_model.ainvoke(messages)
            raw_text = getattr(response, "content", "") or ""
            elapsed = time.perf_counter() - t0

            section_text, claims = _parse_section_output(raw_text)

            if not section_text.strip():
                logger.warning("[SECTION_DRAFTER] %s: empty output (attempt %d, %.1fs)", sid, attempt + 1, elapsed)
                retries += 1
                continue

            # Check must_include
            mi_passed, mi_failures = _check_must_include(section_text, must_include)

            if mi_passed:
                logger.info(
                    "[SECTION_DRAFTER] %s: ✓ pass (attempt %d, %.1fs) | claims=%d",
                    sid, attempt + 1, elapsed, len(claims),
                )
                return {
                    "section_id": sid,
                    "heading": heading,
                    "text": section_text,
                    "type": stype,
                    "claims": claims,
                    "must_include_passed": True,
                    "retries": attempt,
                    "validation_issues": [],
                }
            else:
                logger.warning(
                    "[SECTION_DRAFTER] %s: ✗ must_include failed (attempt %d, %.1fs) | failures=%s",
                    sid, attempt + 1, elapsed, mi_failures,
                )
                # Keep best attempt
                if len(section_text) > len(best_text):
                    best_text = section_text
                    best_claims = claims
                retries += 1

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            logger.error("[SECTION_DRAFTER] %s: error (attempt %d, %.1fs): %s", sid, attempt + 1, elapsed, exc)
            retries += 1

    # All retries exhausted — use best attempt
    logger.warning("[SECTION_DRAFTER] %s: all retries exhausted — using best attempt", sid)
    return {
        "section_id": sid,
        "heading": heading,
        "text": best_text,
        "type": stype,
        "claims": best_claims,
        "must_include_passed": False,
        "retries": retries,
        "validation_issues": [],
    }


async def section_drafter_node(state: DraftingState) -> Command:
    """Draft all sections CONCURRENTLY from template.

    Template sections are instant (no LLM). LLM sections run in parallel via
    asyncio.gather, cutting wall-clock time from ~9 min to ~2-3 min.
    Section order is preserved — gather returns results in input order.
    """
    logger.info("[SECTION_DRAFTER] ▶ start")
    t0 = time.perf_counter()

    template = state.get("template")
    if not template or not isinstance(template, dict):
        logger.error("[SECTION_DRAFTER] no template in state — fallback to draft")
        return Command(goto="draft")

    intake = _as_dict(state.get("intake"))
    classify = _as_dict(state.get("classify"))
    rag = _as_dict(state.get("rag"))
    mandatory_provisions = _as_dict(state.get("mandatory_provisions"))
    court_fee = _as_dict(state.get("court_fee"))
    user_request = state.get("user_request", "")

    sections = template.get("sections", [])

    # Launch ALL sections concurrently — template sections return instantly,
    # LLM sections run in parallel. asyncio.gather preserves input order.
    coros = [
        _draft_single_section(
            section=section,
            intake=intake,
            classify=classify,
            rag=rag,
            mandatory_provisions=mandatory_provisions,
            court_fee=court_fee,
            template=template,
            user_request=user_request,
        )
        for section in sections
    ]
    filled_sections = list(await asyncio.gather(*coros))

    all_claims: List[Dict[str, Any]] = []
    total_retries = 0
    for filled in filled_sections:
        all_claims.extend(filled.get("claims", []))
        total_retries += filled.get("retries", 0)

    elapsed = time.perf_counter() - t0
    passed_count = sum(1 for f in filled_sections if f.get("must_include_passed"))
    llm_count = sum(1 for f in filled_sections if f.get("type") in ("llm_fill", "template_with_fill"))

    logger.info(
        "[SECTION_DRAFTER] ✓ done (%.1fs) | sections=%d | llm=%d | passed=%d/%d | retries=%d | claims=%d",
        elapsed, len(filled_sections), llm_count, passed_count, llm_count, total_retries, len(all_claims),
    )

    return Command(
        update={
            "filled_sections": filled_sections,
            "claim_ledger": all_claims,
        },
        goto="section_validator",
    )
