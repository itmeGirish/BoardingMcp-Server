"""
Live full-pipeline draft runner — console output.

Usage (from project root):
    agent_steer/Scripts/python.exe research/run_draft_live.py

Runs the real drafting graph (live LLM) and prints:
  - Draft text
  - Blocking issues from review
  - Limitation article used
  - Court fee stated
  - Annexure labels check
  - Section 65B usage check
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


QUERY = (
    "Draft a suit for recovery of Rs.20,00,000/- paid as advance for a business transaction "
    "which failed due to Defendant's default. "
    "Plead total failure of consideration under Section 65 of Indian Contract Act. "
    "Claim refund with interest and costs. "
    "Include cause of action paragraph with accrual date, continuing nature of cause of action, "
    "valuation, court fee, and proper verification clause. "
    "Draft suitable for filing before the District Court."
)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _as_dict(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    fn = getattr(val, "model_dump", None)
    return fn() if callable(fn) else {}


# ── Scoring ─────────────────────────────────────────────────────────────────

def _check_facts_law_separation(t: str) -> bool:
    """Check that the FACTS section does not contain statutory citations like 'Section X of the Y Act'.

    Returns True if facts-law separation is proper (no law in facts).
    """
    m = re.search(
        r"facts\s+of\s+the\s+case\s+(.*?)(?:legal\s+basis|cause\s+of\s+action)",
        t, re.DOTALL,
    )
    if not m:
        return True  # No facts section found — can't check
    facts_text = m.group(1)
    has_section_in_facts = bool(re.search(
        r"section\s+\d+\s+of\s+the\s+(?:indian|contract|evidence|limitation|specific|civil)",
        facts_text,
    ))
    return not has_section_in_facts


def score_legal_accuracy(text: str) -> dict:
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {
        # ── Structural checks (scenario-specific: recovery suit / Section 65) ──
        "[STRUCT] Claim Rs.20,00,000 recovery amount": has(r"20.00.000|20,00,000|2000000|twenty\s+lakh|claim_amount"),
        "[STRUCT] Business transaction / advance payment stated": has(r"advance|business\s+transaction|business\s+deal"),
        "[STRUCT] Defendant's default / breach pleaded": has(r"default|breach|fail"),
        "[STRUCT] Total failure of consideration pleaded": has(r"failure\s+of\s+consideration|total\s+failure"),
        "[STRUCT] Section 65 Indian Contract Act cited": has(r"section\s+65|s\.\s*65|sec\.\s*65"),
        "[STRUCT] Interest claimed": has(r"interest"),
        "[STRUCT] Costs claimed": has(r"cost"),
        "[STRUCT] Prayer for decree / recovery": has(r"prayer|decree|recover"),
        "[STRUCT] Court type mentioned": has(r"district\s+court|district\s+judge|principal\s+(?:district|civil)|civil\s+judge|senior\s+division|court_name"),
        "[STRUCT] Verification clause present": has(r"verif"),
        "[STRUCT] Valuation and court fee stated": has(r"valuat") and has(r"court fee"),
        # ── Legal accuracy checks ──────────────────────────────────────────────
        "[LEGAL] CoA: accrual date / default date stated": (
            has(r"cause\s+of\s+action.*(?:arose|accru)")
            or has(r"\{\{.*(?:date|accrual).*\}\}")
        ),
        "[LEGAL] CoA: continuing cause of action stated": has(r"continu"),
        "[LEGAL] Limitation: Article 47/55/113 OR placeholder": (
            has(r"article\s+(?:47|55|113)|art\s*\.?\s*(?:47|55|113)|three\s+year|3\s*year")
            or has(r"\{\{limitation_article\}\}|\{\{limitation_period\}\}")
        ),
        "[LEGAL] Limitation NOT anchored to notice date":
            not has(r"limitation\s+(?:period\s+)?runs\s+from[^.]{0,80}notice")
            and not has(r"cause of action[^.]{0,60}notice[^.]{0,60}arose"),
        "[LEGAL] Annexure labels present": has(r"annexure"),
        "[LEGAL] No fabricated case law citations": (
            not has(r"\d{4}\s+scc\s+\d+") and not has(r"air\s+\d{4}")
        ),
        "[LEGAL] Refund/restitution framing correct": has(r"refund|restit|repay|return"),
        "[LEGAL] Section 73 alternative plea": has(r"section\s+73|s\.\s*73|alternative|without\s+prejudice"),
        # ── Quality checks (12 senior lawyer feedback points) ──────────────────
        "[QUALITY] Q1 Narrative facts (not skeleton)": (
            # Must have enough substantive content (sentence-ending punctuation followed by new sentences)
            len(re.findall(r"\.\s+", t)) >= 15
            # Must NOT have bare conclusions like "defendant failed." as standalone sentence
            and not has(r"(?:^|\.\s+)(?:the\s+)?defendant\s+(?:has\s+)?failed\.\s")
            and not has(r"(?:^|\.\s+)(?:the\s+)?transaction\s+failed\.\s")
        ),
        "[QUALITY] Q2 Facts-law separation": _check_facts_law_separation(t),
        "[QUALITY] Q3 No drafting-notes language": (
            not has(r"to\s+be\s+verif(?:ied|y)")
            and not has(r"\bplaceholder\b(?!\s*})")
            and not has(r"to\s+be\s+enter(?:ed|ing)")
            and not has(r"to\s+be\s+calculat(?:ed|ing)")
            and not has(r"details?\s+to\s+follow")
            and not has(r"\b(?:tbd|tbc|todo)\b")
        ),
        "[QUALITY] Q4 Strong cause of action (origin+further+continuing)": (
            has(r"first\s+arose|cause\s+of\s+action.*arose")
            and has(r"further\s+(?:arose|accrued|subsist|continu|and\s+continuously)")
            and has(r"continu(?:ing|es|ed)\s+(?:one|cause|to|as)")
        ),
        "[QUALITY] Q5 Jurisdiction specificity (territorial link)": (
            has(r"resid|carries\s+on\s+business|situate")
            and has(r"pecuniary|monetary")
        ),
        "[QUALITY] Q6 Interest rate justification": (
            has(r"commercial|wrongful(?:ly)?\s+retain|bank\s+(?:lending\s+)?rate|depriv|benefit\s+of")
        ),
        "[QUALITY] Q7 Prayer specificity (6+ sub-prayers)": (
            len(re.findall(r"\([a-g]\)", t)) >= 5
            or len(re.findall(r"(?:^|\n)\s*\([a-g]\)", t)) >= 5
        ),
        "[QUALITY] Q8 Legal trigger explained (not just section named)": (
            has(r"section\s+65.*?(?:provides?|states?|mandates?|requires?|lays?\s+down|enacts?)")
            or has(r"(?:provides?|states?)\s+that\s+when")
        ),
        "[QUALITY] Q9 Defensive pleading present": (
            has(r"no\s+part\s+performance|no\s+forfeiture|no\s+counter.?claim|no\s+set.?off|no\s+adjustment")
            or has(r"without\s+(?:any\s+)?(?:lawful\s+)?(?:authority|justification|right)")
            or (has(r"without\s+prejudice") and has(r"in\s+the\s+alternative"))
            or has(r"without\s+conferring\s+any\s+benefit")
        ),
        "[QUALITY] Q10 No 'and/or' usage": not has(r"\band/or\b"),
        "[QUALITY] Q11 Pre-litigation costs in prayer": has(r"pre-?lit|legal\s+notice.*cost|cost.*legal\s+notice"),
        "[QUALITY] Q12 Concise (no excessive repetition)": (
            # Core legal concept may appear across many sections (facts, legal basis, CoA, limitation, prayer).
            # Threshold: <= 8 for a full 14-section plaint where it's the central cause of action.
            len(re.findall(r"failure\s+of\s+consideration", t)) <= 8
            and len(re.findall(r"total\s+failure", t)) <= 8
        ),
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "percent": round(passed / total * 100, 1),
    }


def extract_limitation_info(text: str):
    t = text.lower()
    articles = re.findall(r"article\s+(\d+[a-z]?)", t)
    notice_trigger = bool(re.search(r"limitation\s+runs\s+from.*notice|cause of action.*notice.*date", t))
    default_trigger = bool(re.search(r"cause of action.*default|limitation.*default|right to sue.*default", t))
    placeholder_used = "{{limitation_article}}" in t or "{{limitation_period}}" in t
    return {
        "articles_cited": sorted(set(articles)),
        "notice_as_trigger": notice_trigger,
        "default_as_trigger": default_trigger,
        "placeholder_used": placeholder_used,
    }


def extract_court_fee_info(text: str):
    t = text.lower()
    flat_slab = re.findall(r"court fee[^.]*rs\.?\s*(\d{3,6})\b", t)
    percentage = re.findall(r"court fee[^.]*(\d+(?:\.\d+)?)\s*%", t)
    placeholder = "{{court_fee_amount}}" in t
    return {
        "flat_slab_amounts": flat_slab,
        "percentage_rates": percentage,
        "placeholder_used": placeholder,
    }


def extract_annexure_consistency(text: str):
    body_refs = re.findall(r"annexure[-–\s]+([A-Za-z0-9]+)", text, re.IGNORECASE)
    list_entries = re.findall(r"annexure[-–\s]+([A-Za-z0-9]+)\s*[-–—:]", text, re.IGNORECASE)
    body_set = set(b.upper() for b in body_refs)
    list_set = set(l.upper() for l in list_entries)
    only_in_body = body_set - list_set
    only_in_list = list_set - body_set
    return {
        "body_refs": sorted(body_set),
        "list_entries": sorted(list_set),
        "only_in_body": sorted(only_in_body),
        "only_in_list": sorted(only_in_list),
        "consistent": not only_in_body and not only_in_list,
    }


def section_65b_check(text: str):
    t = text.lower()
    cited = bool(re.search(r"section\s+65b|65\s*b\s+of\s+the\s+evidence", t))
    misused = bool(re.search(r"65b[^.]*admission|65b[^.]*oral|65b[^.]*paper", t))
    return {"cited": cited, "misused_for_non_electronic": misused}


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 70)
    print("LIVE DRAFT TEST — Full Pipeline")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\nQuery (first 120 chars): {QUERY[:120]}...\n")

    import time as _time

    from app.agents.drafting_agents.drafting_graph import get_drafting_graph

    graph = get_drafting_graph()
    t_start = _time.perf_counter()
    result = _as_dict(await graph.ainvoke({"user_request": QUERY}))
    total_elapsed = _time.perf_counter() - t_start
    print(f"\n  TOTAL PIPELINE TIME: {total_elapsed:.1f}s ({total_elapsed / 60:.1f} min)")

    # ── Extract final draft ──────────────────────────────────────────────
    final_block = _as_dict(result.get("final_draft"))
    artifacts = final_block.get("draft_artifacts") or []
    draft_text = ""
    draft_title = "N/A"
    source = "none"

    if artifacts:
        first = artifacts[0] if isinstance(artifacts[0], dict) else _as_dict(artifacts[0])
        draft_text = (first.get("text") or "").strip()
        draft_title = (first.get("title") or "Final Draft").strip()
        source = "final_draft"
        placeholders = first.get("placeholders_used") or []
    else:
        # Fallback to draft node
        draft_block = _as_dict(result.get("draft"))
        draft_arts = draft_block.get("draft_artifacts") or []
        if draft_arts:
            first = draft_arts[0] if isinstance(draft_arts[0], dict) else _as_dict(draft_arts[0])
            draft_text = (first.get("text") or "").strip()
            draft_title = (first.get("title") or "Draft v1").strip()
            source = "draft_fallback"
            placeholders = first.get("placeholders_used") or []
        else:
            placeholders = []

    # ── Extract review blocking issues ───────────────────────────────────
    review_block = _as_dict(result.get("review"))
    review_data = _as_dict(review_block.get("review"))
    blocking = review_data.get("blocking_issues") or []
    review_pass = review_data.get("review_pass", None)

    # ── Print draft ───────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"  SOURCE: {source.upper()}   |   TITLE: {draft_title}")
    print(f"{'=' * 70}\n")
    print(draft_text if draft_text else "[NO DRAFT TEXT GENERATED]")
    print(f"\n{'─' * 70}")

    # ── Legal accuracy scoring ────────────────────────────────────────────
    print("\n ACCURACY SCORE")
    print("─" * 70)
    score = score_legal_accuracy(draft_text)
    for check, passed in score["checks"].items():
        status = "PASS" if passed else "FAIL"
        mark = "✓" if passed else "✗"
        print(f"  [{status}] {mark}  {check}")
    print(f"\n  TOTAL: {score['passed']}/{score['total']}  ({score['percent']}%)")

    # ── Specific legal defect analysis ────────────────────────────────────
    print("\n LIMITATION ANALYSIS")
    print("─" * 70)
    lim = extract_limitation_info(draft_text)
    print(f"  Articles cited:         {lim['articles_cited'] or 'NONE'}")
    print(f"  Placeholder used:       {'YES (correct)' if lim['placeholder_used'] else 'NO'}")
    print(f"  Notice as trigger:      {'[DEFECT] YES' if lim['notice_as_trigger'] else 'OK - NO'}")
    print(f"  Default as trigger:     {'OK - YES' if lim['default_as_trigger'] else 'NOT EXPLICIT'}")

    print("\n COURT FEE ANALYSIS")
    print("─" * 70)
    cf = extract_court_fee_info(draft_text)
    print(f"  Flat slab amounts:      {cf['flat_slab_amounts'] or 'NONE'}")
    print(f"  Percentage rates found: {cf['percentage_rates'] or 'NONE'}")
    print(f"  Placeholder used:       {'YES' if cf['placeholder_used'] else 'NO'}")

    print("\n ANNEXURE CONSISTENCY")
    print("─" * 70)
    anx = extract_annexure_consistency(draft_text)
    print(f"  Body refs:              {anx['body_refs']}")
    print(f"  List entries:           {anx['list_entries']}")
    print(f"  Only in body (defect):  {anx['only_in_body']}")
    print(f"  Only in list (defect):  {anx['only_in_list']}")
    print(f"  Consistent:             {'YES' if anx['consistent'] else '[DEFECT] NO'}")

    print("\n SECTION 65B CHECK")
    print("─" * 70)
    s65 = section_65b_check(draft_text)
    print(f"  Section 65B cited:      {'YES' if s65['cited'] else 'NO'}")
    print(f"  Misused (non-elec):     {'[DEFECT] YES' if s65['misused_for_non_electronic'] else 'OK'}")

    # ── Inline fix detection ──────────────────────────────────────────────
    review_final_artifacts = review_data.get("final_artifacts") or []
    inline_fix_used = bool(review_final_artifacts) and any(
        (a.get("text") if isinstance(a, dict) else "").strip()
        for a in review_final_artifacts
    )

    # ── Review blocking issues ────────────────────────────────────────────
    print(f"\n REVIEW NODE  (pass={review_pass} | inline_fix_used={inline_fix_used})")
    print("─" * 70)
    if blocking:
        for i, b in enumerate(blocking, 1):
            if isinstance(b, dict):
                sev = b.get("severity", "legal")
                print(f"  [{i}] [{sev.upper()}] ISSUE: {b.get('issue','')}")
                print(f"       FIX:      {b.get('fix','')}")
                print(f"       LOCATION: {b.get('location','')}")
            else:
                print(f"  [{i}] {b}")
    else:
        print("  No blocking issues reported.")

    # ── Placeholders ──────────────────────────────────────────────────────
    if placeholders:
        print(f"\n PLACEHOLDERS IN DRAFT ({len(placeholders)})")
        print("─" * 70)
        for ph in placeholders:
            if isinstance(ph, dict):
                print(f"  {{{{{ph.get('key','')}}}}}  — {ph.get('reason','')}")
            else:
                print(f"  {ph}")

    # ── Save raw state ─────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"live_run_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n Raw state saved → {out_path}")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
