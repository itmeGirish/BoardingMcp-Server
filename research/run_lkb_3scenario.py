"""3-Scenario LKB Quality Test — runs money_recovery, dealership, specific_performance.

Compares LKB-enhanced pipeline output quality.

Usage: agent_steer/Scripts/python.exe research/run_lkb_3scenario.py
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

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

SCENARIOS = {
    "money_recovery": (
        "Draft a suit for recovery of Rs.20,00,000/- paid as advance for a business transaction "
        "which failed due to Defendant's default. "
        "Plead total failure of consideration under Section 65 of Indian Contract Act. "
        "Claim refund with interest and costs. "
        "Include cause of action paragraph with accrual date, continuing nature of cause of action, "
        "valuation, court fee, and proper verification clause. "
        "Draft suitable for filing before the District Court."
    ),
    "dealership_damages": (
        "Draft a commercial suit seeking damages for illegal termination of dealership agreement. "
        "Plaintiff invested substantial capital and developed territory market. "
        "Termination was arbitrary and contrary to agreement terms. "
        "Claim compensation for loss of profit, goodwill and unsold stock. "
        "Draft with proper breach of contract pleading."
    ),
    "specific_performance": (
        "Draft a suit for specific performance of agreement to sell immovable property. "
        "Plaintiff entered into agreement to sell dated 15.03.2024 with Defendant for purchase of "
        "a residential property for Rs.85,00,000/-. Plaintiff paid Rs.10,00,000/- as earnest money. "
        "Defendant is now refusing to execute the sale deed despite plaintiff being ready and willing. "
        "Claim specific performance or damages in the alternative. "
        "Draft suitable for filing before the District Court."
    ),
}


def _as_dict(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    fn = getattr(val, "model_dump", None)
    return fn() if callable(fn) else {}


def _lkb_score(text: str, lkb_brief: dict) -> dict:
    """Score draft against LKB requirements — checks substance, not just structure."""
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {}

    # Structure checks (same as before)
    checks["Narrative facts (8+ sentences)"] = len(re.findall(r"\.\s+", t)) >= 20
    checks["Strong CoA (origin+further)"] = (
        has(r"first\s+arose|cause\s+of\s+action.*arose")
        and has(r"further\s+(?:arose|accrued|subsist|continu)")
    )
    checks["Court heading present"] = has(r"in the court of")
    checks["Verification clause"] = has(r"verif")
    checks["5+ Annexures"] = len(set(re.findall(r"annexure[-\s]+([a-z])", t, re.IGNORECASE))) >= 5
    checks["No drafting-notes language"] = not has(r"to\s+be\s+verif|to\s+be\s+enter|to\s+be\s+calculat|\btbd\b|\btodo\b")

    # LKB substance checks
    if lkb_brief:
        # Check primary acts cited
        primary_acts = lkb_brief.get("primary_acts", [])
        for act_info in primary_acts:
            act_name = act_info.get("act", "")
            short = act_name.split(",")[0].strip().lower()
            checks[f"Primary Act: {act_name[:40]}"] = short in t

        # Check limitation article
        lim = lkb_brief.get("limitation", {})
        lkb_article = str(lim.get("article", ""))
        if lkb_article and lkb_article != "NONE":
            checks[f"Limitation Article {lkb_article}"] = has(rf"article\s+{re.escape(lkb_article)}\b")

        # Check court format
        detected_court = lkb_brief.get("detected_court", {})
        court_format = detected_court.get("format", "")
        if court_format:
            checks[f"Court format: {court_format}"] = court_format.lower().replace(".", r"\.?").replace(" ", r"\s*") in t or court_format in text

        # Check CoA type guidance followed
        coa_type = lkb_brief.get("coa_type", "")
        if coa_type == "single_event":
            # Should NOT have "continuing breach" / "continuing cause" for single event
            has_continuing_breach = has(r"continu(?:ing|es|ed)\s+(?:breach|to\s+breach)")
            checks["CoA type correct (not continuing breach)"] = not has_continuing_breach
        elif coa_type == "continuing":
            checks["CoA type correct (continuing)"] = has(r"continu(?:ing|es|ed)\s+(?:one|cause|to)")

        # Check damages categories in prayer
        damages = lkb_brief.get("damages_categories", [])
        if damages and len(damages) > 1:
            found_damages = 0
            for d in damages:
                terms = d.replace("_", " ").lower().split()
                if any(term in t for term in terms if len(term) > 3):
                    found_damages += 1
            checks[f"Damages categorized ({found_damages}/{len(damages)})"] = found_damages >= len(damages) // 2

        # Check defensive pleading
        defensive = lkb_brief.get("defensive_points", [])
        if defensive:
            found_def = 0
            for d in defensive:
                terms = d.replace("_", " ").lower().split()
                if any(term in t for term in terms if len(term) > 3):
                    found_def += 1
            checks[f"Defensive pleading ({found_def}/{len(defensive)})"] = found_def >= 1

        # Check no superseded acts
        checks["No superseded Acts cited"] = not has(r"specific\s+relief\s+act[,\s]*1877")

        # Check procedural compliance (for commercial court)
        proc = detected_court.get("procedural", [])
        if proc:
            for req in proc[:2]:  # Check first 2 procedural requirements
                key_terms = re.findall(r"Section\s+\d+[A-Z]?", req)
                for term in key_terms:
                    checks[f"Procedural: {term}"] = term.lower() in t

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {"checks": checks, "passed": passed, "total": total, "pct": round(passed / total * 100, 1) if total else 0}


async def run_one(name: str, query: str) -> dict:
    """Run one scenario and return results."""
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph

    print(f"\n{'=' * 70}")
    print(f"  SCENARIO: {name.upper()}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 70}")

    graph = get_drafting_graph()
    t0 = time.perf_counter()
    result = _as_dict(await graph.ainvoke({"user_request": query}))
    elapsed = time.perf_counter() - t0

    # Extract draft text
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

    # Extract review info
    review_block = _as_dict(result.get("review"))
    review_data = _as_dict(review_block.get("review"))
    blocking = review_data.get("blocking_issues") or []
    review_pass = review_data.get("review_pass")

    # Extract enrichment + LKB
    mandatory = _as_dict(result.get("mandatory_provisions"))
    lim = _as_dict(mandatory.get("limitation"))
    proc_provisions = mandatory.get("procedural_provisions") or []
    verified_count = len(mandatory.get("verified_provisions") or [])
    lkb_brief = _as_dict(result.get("lkb_brief"))

    # Extract classify
    classify = _as_dict(result.get("classify"))
    cause_type = classify.get("cause_type", "")

    # Score with LKB-aware checks
    score = _lkb_score(draft_text, lkb_brief)

    print(f"\n  TIME: {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print(f"  SOURCE: {source} | REVIEW: pass={review_pass} | blocking={len(blocking)}")
    print(f"  CAUSE_TYPE: {cause_type}")
    print(f"  LKB: {'YES' if lkb_brief else 'NO'}")
    print(f"  LIMITATION: Article {lim.get('article', 'N/A')} (source: {lim.get('source', 'N/A')})")
    print(f"  PROCEDURAL: {len(proc_provisions)} provisions")
    print(f"  VERIFIED: {verified_count} provisions")
    print(f"  DRAFT: {len(draft_text)} chars")
    print(f"\n  QUALITY SCORE: {score['passed']}/{score['total']} ({score['pct']}%)")
    for check, passed in score["checks"].items():
        mark = "PASS" if passed else "FAIL"
        print(f"    [{mark}] {check}")

    if blocking:
        print(f"\n  BLOCKING ISSUES ({len(blocking)}):")
        for i, b in enumerate(blocking, 1):
            if isinstance(b, dict):
                print(f"    [{i}] [{b.get('severity', '?')}] {b.get('issue', '')[:100]}")

    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"lkb_run_{name}_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Saved -> {out_path}")

    return {
        "name": name,
        "elapsed": elapsed,
        "source": source,
        "draft_text": draft_text,
        "draft_len": len(draft_text),
        "review_pass": review_pass,
        "blocking_count": len(blocking),
        "blocking": blocking,
        "cause_type": cause_type,
        "lkb_hit": bool(lkb_brief),
        "limitation": lim.get("article", "N/A"),
        "limitation_source": lim.get("source", "N/A"),
        "procedural_count": len(proc_provisions),
        "verified_count": verified_count,
        "score": score,
    }


async def main():
    print("=" * 70)
    print("  3-SCENARIO LKB QUALITY TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = []
    total_start = time.perf_counter()

    for name, query in SCENARIOS.items():
        r = await run_one(name, query)
        results.append(r)

    total_elapsed = time.perf_counter() - total_start

    # Summary
    print(f"\n\n{'=' * 70}")
    print("  SUMMARY COMPARISON")
    print(f"{'=' * 70}")
    print(f"\n  Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f}m)\n")

    header = f"  {'Metric':<35} {'Money Recovery':<20} {'Dealership':<20} {'Spec.Performance':<20}"
    print(header)
    print("  " + "-" * 93)

    r1 = results[0] if results else {}
    r2 = results[1] if len(results) > 1 else {}
    r3 = results[2] if len(results) > 2 else {}

    rows = [
        ("Time", f"{r1.get('elapsed',0):.1f}s", f"{r2.get('elapsed',0):.1f}s", f"{r3.get('elapsed',0):.1f}s"),
        ("Draft length", f"{r1.get('draft_len',0)} ch", f"{r2.get('draft_len',0)} ch", f"{r3.get('draft_len',0)} ch"),
        ("Cause type", r1.get('cause_type','?'), r2.get('cause_type','?'), r3.get('cause_type','?')),
        ("LKB hit", str(r1.get('lkb_hit')), str(r2.get('lkb_hit')), str(r3.get('lkb_hit'))),
        ("Limitation", r1.get('limitation','?'), r2.get('limitation','?'), r3.get('limitation','?')),
        ("Lim source", r1.get('limitation_source','?'), r2.get('limitation_source','?'), r3.get('limitation_source','?')),
        ("Review pass", str(r1.get('review_pass')), str(r2.get('review_pass')), str(r3.get('review_pass'))),
        ("Blocking", str(r1.get('blocking_count',0)), str(r2.get('blocking_count',0)), str(r3.get('blocking_count',0))),
        ("Quality", f"{r1.get('score',{}).get('passed',0)}/{r1.get('score',{}).get('total',0)} ({r1.get('score',{}).get('pct',0)}%)",
                    f"{r2.get('score',{}).get('passed',0)}/{r2.get('score',{}).get('total',0)} ({r2.get('score',{}).get('pct',0)}%)",
                    f"{r3.get('score',{}).get('passed',0)}/{r3.get('score',{}).get('total',0)} ({r3.get('score',{}).get('pct',0)}%)"),
    ]

    for label, v1, v2, v3 in rows:
        print(f"  {label:<35} {v1:<20} {v2:<20} {v3:<20}")

    # Key improvements check
    print(f"\n{'=' * 70}")
    print("  LKB IMPACT ANALYSIS")
    print(f"{'=' * 70}")

    for r in results:
        name = r.get("name", "?")
        score = r.get("score", {})
        checks = score.get("checks", {})
        failed = [k for k, v in checks.items() if not v]
        print(f"\n  {name.upper()}:")
        print(f"    Score: {score.get('passed',0)}/{score.get('total',0)} ({score.get('pct',0)}%)")
        if failed:
            print(f"    Failed checks: {', '.join(failed)}")
        else:
            print(f"    All checks PASSED")

    print(f"\n{'=' * 70}")
    print("  DONE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
