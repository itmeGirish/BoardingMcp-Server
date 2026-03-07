"""
Live injunction suit test — evaluates whether the pipeline correctly drafts
a permanent injunction plaint instead of misframing as money recovery.

Usage:
    agent_steer/Scripts/python.exe research/run_injunction_test.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

QUERY = (
    "Prepare a suit for permanent injunction restraining Defendant from interfering "
    "with Plaintiff's peaceful possession of schedule property. "
    "Plaintiff is in lawful possession. Defendant attempting illegal encroachment. "
    "Include temporary injunction prayer under Order 39 Rules 1 & 2 CPC. "
    "Draft clearly with property description in schedule."
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


def score_injunction_accuracy(text: str) -> dict:
    """Score the draft against injunction-specific criteria."""
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {
        # ── FRAMING (most critical — was this drafted as injunction or money recovery?) ──
        "[FRAME] Title says INJUNCTION (not recovery)": (
            has(r"injunction") and not has(r"suit\s+for\s+recovery\s+of\s+rs")
        ),
        "[FRAME] NO interest calculation section": not has(r"pre-?suit\s+interest.*pendente\s+lite"),
        "[FRAME] NO failure of consideration plea": not has(r"failure\s+of\s+consideration"),
        "[FRAME] NO refund/restitution as primary relief": not has(r"refund|restitution"),
        "[FRAME] Prayer seeks INJUNCTION (not money decree)": (
            has(r"injunction") and has(r"restrain")
        ),
        "[FRAME] Doc type NOT money recovery in title": not has(r"suit\s+for\s+recovery\s+of\s+rs"),

        # ── STRUCTURAL checks ──
        "[STRUCT] Permanent injunction mentioned": has(r"permanent\s+injunction"),
        "[STRUCT] Encroachment / interference described": has(r"encroach|interfer|trespass"),
        "[STRUCT] Lawful possession pleaded": has(r"lawful\s+possession|peaceful\s+possession|rightful\s+possession"),
        "[STRUCT] Schedule property referenced": has(r"schedule\s+property|schedule\s+hereunder|property\s+described"),
        "[STRUCT] Order 39 Rules 1 & 2 cited": has(r"order\s+39|order\s+xxxix"),
        "[STRUCT] Temporary injunction prayer": has(r"temporary\s+injunction|interim\s+injunction|ad\s+interim"),
        "[STRUCT] Verification clause present": has(r"verif"),
        "[STRUCT] Court type mentioned": has(r"court|judge|court_name"),
        "[STRUCT] Costs claimed": has(r"cost"),

        # ── LEGAL accuracy ──
        "[LEGAL] Specific Relief Act cited": has(r"specific\s+relief\s+act|section\s+3[789]|section\s+38|section\s+39"),
        "[LEGAL] Prima facie case / balance of convenience / irreparable": (
            has(r"prima\s+facie") or has(r"balance\s+of\s+convenience") or has(r"irreparable")
        ),
        "[LEGAL] Cause of action stated": has(r"cause\s+of\s+action"),
        "[LEGAL] Limitation addressed": has(r"limitation"),
        "[LEGAL] NO Article 136 (execution)": not has(r"article\s+136"),
        "[LEGAL] Annexure labels present": has(r"annexure"),
        "[LEGAL] No fabricated case law": not has(r"\d{4}\s+scc\s+\d+") and not has(r"air\s+\d{4}"),

        # ── QUALITY ──
        "[QUALITY] Narrative facts (not skeleton)": len(re.findall(r"\.\s+", t)) >= 10,
        "[QUALITY] No drafting-notes language": (
            not has(r"to\s+be\s+verif(?:ied|y)")
            and not has(r"\bplaceholder\b(?!\s*})")
            and not has(r"to\s+be\s+enter(?:ed|ing)")
        ),
        "[QUALITY] No and/or usage": not has(r"\band/or\b"),
        "[QUALITY] Concise (not over-explained)": len(t.split()) < 5000,
        "[QUALITY] General relief clause": has(r"any\s+other\s+relief|deem.*fit"),
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "percent": round(passed / total * 100, 1),
    }


async def main():
    print("=" * 70)
    print("INJUNCTION SUIT TEST — Full Pipeline")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\nQuery: {QUERY[:120]}...\n")

    import time as _time
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph

    graph = get_drafting_graph()
    t_start = _time.perf_counter()
    result = _as_dict(await graph.ainvoke({"user_request": QUERY}))
    total_elapsed = _time.perf_counter() - t_start
    print(f"\n  TOTAL PIPELINE TIME: {total_elapsed:.1f}s ({total_elapsed / 60:.1f} min)")

    # ── Extract classification info ──
    classify = _as_dict(result.get("classify"))
    doc_type = classify.get("doc_type", "UNKNOWN")
    law_domain = classify.get("law_domain", "UNKNOWN")
    print(f"\n  CLASSIFIED: domain={law_domain} | doc_type={doc_type}")

    # ── Check template used ──
    template = result.get("template")
    if isinstance(template, dict):
        template_id = template.get("template_id", "UNKNOWN")
        print(f"  TEMPLATE:   {template_id}")
    else:
        print("  TEMPLATE:   NONE (old draft fallback)")

    # ── Extract final draft ──
    final_block = _as_dict(result.get("final_draft"))
    artifacts = final_block.get("draft_artifacts") or []
    draft_text = ""
    source = "none"

    if artifacts:
        first = artifacts[0] if isinstance(artifacts[0], dict) else _as_dict(artifacts[0])
        draft_text = (first.get("text") or "").strip()
        source = "final_draft"
    else:
        draft_block = _as_dict(result.get("draft"))
        draft_arts = draft_block.get("draft_artifacts") or []
        if draft_arts:
            first = draft_arts[0] if isinstance(draft_arts[0], dict) else _as_dict(draft_arts[0])
            draft_text = (first.get("text") or "").strip()
            source = "draft_fallback"

    # ── Print draft ──
    print(f"\n{'=' * 70}")
    print(f"  SOURCE: {source.upper()}")
    print(f"{'=' * 70}\n")
    print(draft_text[:3000] if draft_text else "[NO DRAFT TEXT GENERATED]")
    if len(draft_text) > 3000:
        print(f"\n  ... [{len(draft_text) - 3000} more chars truncated]")
    print(f"\n{'─' * 70}")

    # ── Score ──
    print("\n INJUNCTION ACCURACY SCORE")
    print("─" * 70)
    score = score_injunction_accuracy(draft_text)

    # Group by category
    categories = {"FRAME": [], "STRUCT": [], "LEGAL": [], "QUALITY": []}
    for check, passed in score["checks"].items():
        cat = check.split("]")[0].replace("[", "")
        categories.get(cat, []).append((check, passed))

    for cat, items in categories.items():
        cat_passed = sum(1 for _, p in items if p)
        cat_total = len(items)
        print(f"\n  {cat} ({cat_passed}/{cat_total}):")
        for check, passed in items:
            status = "PASS" if passed else "FAIL"
            mark = "✓" if passed else "✗"
            print(f"    [{status}] {mark}  {check}")

    print(f"\n  TOTAL: {score['passed']}/{score['total']}  ({score['percent']}%)")

    # ── Critical verdict ──
    frame_checks = [v for k, v in score["checks"].items() if "[FRAME]" in k]
    frame_passed = sum(1 for v in frame_checks if v)
    if frame_passed == len(frame_checks):
        print("\n  ✓ VERDICT: Correctly framed as INJUNCTION suit")
    else:
        frame_failures = [k for k, v in score["checks"].items() if "[FRAME]" in k and not v]
        print(f"\n  ✗ VERDICT: MISFRAMED — {len(frame_checks) - frame_passed} framing errors:")
        for f in frame_failures:
            print(f"    - {f}")

    # ── Save ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"injunction_test_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Raw state saved → {out_path}")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
