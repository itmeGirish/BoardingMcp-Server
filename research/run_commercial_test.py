"""
Live commercial invoice recovery test — evaluates whether the pipeline correctly
drafts a goods-sold-and-delivered plaint instead of misframing as Section 65 restitution.

Usage:
    agent_steer/Scripts/python.exe research/run_commercial_test.py
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
    "Draft a recovery suit for Rs. 5,00,000/- being unpaid invoices for goods supplied "
    "by Plaintiff (a textile trading firm) to Defendant (a garment manufacturer). "
    "Goods were supplied on credit over 3 months per purchase orders, delivery challans "
    "signed by Defendant. Multiple invoices raised but Defendant failed to pay despite "
    "repeated reminders and legal notice. "
    "File before the appropriate Civil Court. "
    "Include cause of action, limitation, valuation, court fee, interest, and verification."
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


def score_commercial_accuracy(text: str) -> dict:
    """Score the draft against commercial invoice recovery criteria."""
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {
        # ── FRAMING (most critical — was this drafted correctly for invoice recovery?) ──
        "[FRAME] Title says RECOVERY (money suit)": has(r"suit\s+for\s+recovery|recovery\s+of\s+rs"),
        "[FRAME] NO Section 65 / void contract / restitution as PRIMARY theory": (
            not has(r"section\s+65\s+of\s+the\s+indian\s+contract")
            or has(r"alternative|without\s+prejudice")  # OK if used as alternative plea only
        ),
        "[FRAME] NO 'advance payment' framing": not has(r"advance\s+payment|paid\s+as\s+advance"),
        "[FRAME] Goods supplied / delivered framing": has(r"goods\s+supplied|goods\s+delivered|supplied\s+goods|delivered\s+goods"),
        "[FRAME] Invoice / unpaid invoice referenced": has(r"invoice|invoiced|unpaid"),
        "[FRAME] Purchase order / delivery challan referenced": has(r"purchase\s+order|delivery\s+challan|challan"),

        # ── STRUCTURAL checks ──
        "[STRUCT] Claim amount Rs. 5,00,000": has(r"5[,.]?00[,.]?000|five\s+lakh"),
        "[STRUCT] Plaintiff as supplier/trader": has(r"textile|trading|supplier|firm"),
        "[STRUCT] Defendant as buyer/manufacturer": has(r"garment|manufacturer|buyer|purchaser"),
        "[STRUCT] Default/breach pleaded": has(r"fail(ed|ure)|default(ed)?|breach(ed)?|did\s+not\s+pay|neglect"),
        "[STRUCT] Legal notice mentioned": has(r"legal\s+notice|demand\s+notice"),
        "[STRUCT] Annexure labels present": has(r"annexure"),
        "[STRUCT] Verification clause present": has(r"verif"),
        "[STRUCT] Court type mentioned": has(r"court|judge|court_name"),

        # ── LEGAL accuracy ──
        "[LEGAL] Sale of Goods Act OR Indian Contract Act cited": (
            has(r"sale\s+of\s+goods\s+act") or has(r"indian\s+contract\s+act") or has(r"contract\s+act")
        ),
        "[LEGAL] Section for breach/payment obligation cited": (
            has(r"section\s+\d+") and (has(r"breach") or has(r"payment") or has(r"price") or has(r"liable"))
        ),
        "[LEGAL] Cause of action stated": has(r"cause\s+of\s+action"),
        "[LEGAL] Limitation addressed": has(r"limitation"),
        "[LEGAL] NO Article 136 (execution of decree)": not has(r"article\s+136"),
        "[LEGAL] NO fabricated case law": not has(r"\d{4}\s+scc\s+\d+") and not has(r"air\s+\d{4}"),

        # ── QUALITY ──
        "[QUALITY] Narrative facts (not skeleton)": len(re.findall(r"\.\s+", t)) >= 10,
        "[QUALITY] No drafting-notes language": (
            not has(r"to\s+be\s+verif(?:ied|y)")
            and not has(r"\bplaceholder\b(?!\s*})")
            and not has(r"to\s+be\s+enter(?:ed|ing)")
        ),
        "[QUALITY] Interest section present": has(r"interest"),
        "[QUALITY] Costs claimed": has(r"cost"),
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
    print("COMMERCIAL INVOICE RECOVERY TEST — Full Pipeline")
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
    print("\n COMMERCIAL INVOICE RECOVERY ACCURACY SCORE")
    print("─" * 70)
    score = score_commercial_accuracy(draft_text)

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
        print("\n  ✓ VERDICT: Correctly framed as COMMERCIAL INVOICE RECOVERY suit")
    else:
        frame_failures = [k for k, v in score["checks"].items() if "[FRAME]" in k and not v]
        print(f"\n  ✗ VERDICT: MISFRAMED — {len(frame_checks) - frame_passed} framing errors:")
        for f in frame_failures:
            print(f"    - {f}")

    # ── Save ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"commercial_test_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Raw state saved → {out_path}")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
