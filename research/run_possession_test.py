"""
Recovery of possession test — evaluates LKB alias resolution + pipeline quality.
Tests the v5.1 changes: LKB aliases, slim review, conditional resolution.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

QUERY = (
    "Draft a civil suit for recovery of possession of immovable property. "
    "Plaintiff is owner of the property situated at Survey No. 45, Koramangala, Bangalore "
    "and Defendant is in unauthorized occupation after expiry of permissive possession/lease "
    "granted on 01.01.2020 which expired on 31.12.2022. "
    "Defendant refusing to vacate despite legal notice dated 15.03.2023. "
    "Property value is Rs.50,00,000/-. Monthly rental value is Rs.25,000/-. "
    "Seek recovery of possession, mesne profits from 01.01.2023 at Rs.25,000/- per month, "
    "and costs of the suit. File before the City Civil Court, Bangalore."
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


def score_possession_draft(text: str) -> dict:
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {
        # ── Structural ──
        "[STRUCT] Court heading (City Civil Court Bangalore)": has(r"city\s+civil\s+court|civil\s+court.*bangalore|court_name"),
        "[STRUCT] Parties block present": has(r"plaintiff") and has(r"defendant"),
        "[STRUCT] Property description (Survey No. 45)": has(r"survey\s+no|survey\s+number|khasra|plot"),
        "[STRUCT] Koramangala/Bangalore location": has(r"koramangala|bangalore|bengaluru"),
        "[STRUCT] Lease/permissive possession stated": has(r"lease|permissive\s+possession|licens|tenancy"),
        "[STRUCT] Lease dates (01.01.2020 / 31.12.2022)": has(r"2020") and has(r"2022"),
        "[STRUCT] Legal notice dated 15.03.2023": has(r"legal\s+notice|notice") and has(r"2023"),
        "[STRUCT] Property value Rs.50,00,000": has(r"50.00.000|50,00,000|5000000|fifty\s+lakh"),
        "[STRUCT] Mesne profits Rs.25,000/month": has(r"25.000|25,000|mesne\s+profit"),
        "[STRUCT] Prayer section present": has(r"prayer"),
        "[STRUCT] Verification clause": has(r"verif"),
        # ── Legal accuracy ──
        "[LEGAL] Recovery of possession as relief": has(r"recovery\s+of\s+possession|deliver.*possession|vacant.*possession"),
        "[LEGAL] Mesne profits as relief": has(r"mesne\s+profit"),
        "[LEGAL] Costs as relief": has(r"cost"),
        "[LEGAL] Specific Relief Act cited": has(r"specific\s+relief\s+act"),
        "[LEGAL] CPC/Order provisions cited": has(r"code\s+of\s+civil\s+procedure|order\s+[xvi]|cpc|civil\s+procedure"),
        "[LEGAL] Unauthorized occupation pleaded": has(r"unauthori[sz]ed\s+occupation|trespass|without\s+(?:any\s+)?(?:right|authority|permission)"),
        "[LEGAL] Expiry of lease/permission": has(r"expir|terminat|determin|lapse"),
        "[LEGAL] Jurisdiction stated": has(r"jurisdiction"),
        "[LEGAL] Limitation correct (Art 64/65/67 or placeholder)": (
            has(r"article\s+(?:64|65|67)")
            or has(r"limitation\s+act")
            or has(r"\{\{limitation")
        ),
        "[LEGAL] No fabricated case citations": not has(r"\d{4}\s+scc\s+\d+") and not has(r"air\s+\d{4}"),
        "[LEGAL] Cause of action paragraph": has(r"cause\s+of\s+action"),
        # ── Quality ──
        "[QUALITY] Narrative depth (15+ sentences)": len(re.findall(r"\.\s+", t)) >= 15,
        "[QUALITY] No 'and/or' usage": not has(r"\band/or\b"),
        "[QUALITY] Paragraph numbering present": has(r"\b\d+\.\s+that\b") or has(r"\b1\.\s"),
        "[QUALITY] Annexure references": has(r"annexure"),
        "[QUALITY] No superseded acts (IPC/CrPC/Evidence Act)": (
            not has(r"indian\s+penal\s+code") and not has(r"code\s+of\s+criminal\s+procedure")
        ),
        "[QUALITY] Valuation and court fee stated": has(r"valuat") and has(r"court\s+fee"),
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
    print("RECOVERY OF POSSESSION TEST — v5.1 Pipeline")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\nQuery:\n{QUERY}\n")

    from app.agents.drafting_agents.drafting_graph import get_drafting_graph

    graph = get_drafting_graph()

    # ── Run pipeline ──
    t_start = time.perf_counter()
    result = _as_dict(await graph.ainvoke({"user_request": QUERY}))
    total_elapsed = time.perf_counter() - t_start

    # ── Extract timing from state ──
    print(f"\n{'=' * 70}")
    print(f"  TOTAL PIPELINE TIME: {total_elapsed:.1f}s ({total_elapsed / 60:.1f} min)")
    print(f"{'=' * 70}")

    # ── Extract final draft ──
    final_block = _as_dict(result.get("final_draft"))
    artifacts = final_block.get("draft_artifacts") or []
    draft_text = ""
    source = "none"

    if artifacts:
        first = artifacts[0] if isinstance(artifacts[0], dict) else _as_dict(artifacts[0])
        draft_text = (first.get("text") or "").strip()
        source = "final_draft"
        placeholders = first.get("placeholders_used") or []
    else:
        draft_block = _as_dict(result.get("draft"))
        draft_arts = draft_block.get("draft_artifacts") or []
        if draft_arts:
            first = draft_arts[0] if isinstance(draft_arts[0], dict) else _as_dict(draft_arts[0])
            draft_text = (first.get("text") or "").strip()
            source = "draft_fallback"
            placeholders = first.get("placeholders_used") or []
        else:
            placeholders = []

    # ── Print draft ──
    print(f"\n  SOURCE: {source.upper()}")
    print(f"  DRAFT LENGTH: {len(draft_text)} chars")
    print(f"{'─' * 70}")
    print(draft_text[:3000] if draft_text else "[NO DRAFT TEXT]")
    if len(draft_text) > 3000:
        print(f"\n  ... [{len(draft_text) - 3000} more chars] ...")

    # ── LKB resolution check ──
    print(f"\n{'=' * 70}")
    print("  LKB ALIAS RESOLUTION CHECK")
    print(f"{'=' * 70}")
    classify = _as_dict(result.get("classify"))
    cause_type = classify.get("cause_type", "UNKNOWN")
    print(f"  Classified cause_type: {cause_type}")

    enrichment = _as_dict(result.get("enrichment"))
    lkb_entry = enrichment.get("lkb_entry")
    print(f"  LKB entry found: {'YES' if lkb_entry else 'NO (MISS)'}")
    if lkb_entry and isinstance(lkb_entry, dict):
        print(f"  Primary acts: {[a.get('act','') for a in (lkb_entry.get('primary_acts') or [])]}")
        lim = lkb_entry.get("limitation", {})
        if isinstance(lim, dict):
            print(f"  Limitation article: {lim.get('article', 'UNKNOWN')}")

    # ── Score ──
    print(f"\n{'=' * 70}")
    print("  ACCURACY SCORE")
    print(f"{'=' * 70}")
    score = score_possession_draft(draft_text)
    for check, passed in score["checks"].items():
        status = "PASS" if passed else "FAIL"
        mark = "+" if passed else "x"
        print(f"  [{status}] {mark}  {check}")
    print(f"\n  TOTAL: {score['passed']}/{score['total']}  ({score['percent']}%)")

    # ── Review info ──
    review_block = _as_dict(result.get("review"))
    review_data = _as_dict(review_block.get("review"))
    blocking = review_data.get("blocking_issues") or []
    review_pass = review_data.get("review_pass", None)
    print(f"\n  REVIEW: pass={review_pass} | blocking_issues={len(blocking)}")
    for i, b in enumerate(blocking, 1):
        if isinstance(b, dict):
            print(f"    [{i}] [{b.get('severity','legal').upper()}] {b.get('issue','')}")

    # ── Placeholders ──
    if placeholders:
        print(f"\n  PLACEHOLDERS ({len(placeholders)}):")
        for ph in placeholders[:10]:
            if isinstance(ph, dict):
                print(f"    {{{{{ph.get('key','')}}}}}  — {ph.get('reason','')}")
            else:
                print(f"    {ph}")

    # ── Performance summary ──
    print(f"\n{'=' * 70}")
    print("  PERFORMANCE SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total time:       {total_elapsed:.1f}s")
    print(f"  Draft length:     {len(draft_text)} chars")
    print(f"  Placeholders:     {len(placeholders)}")
    print(f"  Score:            {score['passed']}/{score['total']} ({score['percent']}%)")
    print(f"  LKB resolved:     {'YES' if lkb_entry else 'NO'}")
    print(f"  Review pass:      {review_pass}")
    print(f"  Blocking issues:  {len(blocking)}")

    # ── Save ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"possession_test_{ts}.json"
    save_data = {
        **result,
        "_meta": {
            "query": QUERY,
            "total_elapsed_s": round(total_elapsed, 1),
            "score": score,
            "cause_type": cause_type,
            "lkb_resolved": bool(lkb_entry),
            "draft_chars": len(draft_text),
            "placeholders": len(placeholders),
            "review_pass": review_pass,
            "blocking_issues": len(blocking),
        }
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Raw state saved -> {out_path}")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
