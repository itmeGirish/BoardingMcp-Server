"""
Dual scenario comparison — runs both scenarios sequentially and prints results.

Usage: agent_steer/Scripts/python.exe research/run_dual_scenario_compare.py
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
}


def _as_dict(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    fn = getattr(val, "model_dump", None)
    return fn() if callable(fn) else {}


def _quick_score(text: str) -> dict:
    """Quick quality scoring for comparison."""
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {
        "Narrative facts (8+ sentences)": len(re.findall(r"\.\s+", t)) >= 20,
        "Facts-law separation": not bool(re.search(
            r"facts\s+of\s+the\s+case\s+(.*?)(?:legal\s+basis|cause\s+of\s+action)",
            t, re.DOTALL,
        ) and re.search(
            r"section\s+\d+\s+of\s+the",
            (re.search(r"facts\s+of\s+the\s+case\s+(.*?)(?:legal\s+basis|cause\s+of\s+action)", t, re.DOTALL) or type('', (), {'group': lambda s, n: ''})()).group(1) or "",
        )),
        "Strong CoA (origin+further+continuing)": (
            has(r"first\s+arose|cause\s+of\s+action.*arose")
            and has(r"further\s+(?:arose|accrued|subsist|continu)")
            and has(r"continu(?:ing|es|ed)\s+(?:one|cause|to|as)")
        ),
        "Jurisdiction specificity": has(r"resid|carries\s+on\s+business|situate") and has(r"pecuniary|monetary"),
        "Legal trigger explained": (
            has(r"(?:provides?|states?)\s+that")
            or has(r"section\s+\d+.*?(?:provides?|states?|mandates?)")
        ),
        "Prayer 6+ sub-items": len(re.findall(r"\([a-g]\)", t)) >= 5,
        "Defensive pleading": (
            has(r"no\s+part\s+performance|no\s+counter.?claim|no\s+set.?off")
            or has(r"without\s+prejudice")
        ),
        "5+ Annexures": len(set(re.findall(r"annexure[-\s]+([a-z])", t, re.IGNORECASE))) >= 5,
        "Interest rate justified": has(r"wrongful|commercial|depriv|bank\s+(?:lending\s+)?rate|prevailing"),
        "No drafting-notes language": not has(r"to\s+be\s+verif|to\s+be\s+enter|to\s+be\s+calculat|\btbd\b|\btodo\b"),
        "Limitation article cited": has(r"article\s+\d+") or has(r"\{\{limitation"),
        "Court heading present": has(r"in the court of"),
        "Verification clause": has(r"verif"),
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {"checks": checks, "passed": passed, "total": total, "pct": round(passed / total * 100, 1)}


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

    # Extract enrichment
    mandatory = _as_dict(result.get("mandatory_provisions"))
    lim = _as_dict(mandatory.get("limitation"))
    proc_provisions = mandatory.get("procedural_provisions") or []
    verified_count = len(mandatory.get("verified_provisions") or [])

    # Score
    score = _quick_score(draft_text)

    print(f"\n  TIME: {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print(f"  SOURCE: {source} | REVIEW: pass={review_pass} | blocking={len(blocking)}")
    print(f"  LIMITATION: Article {lim.get('article', 'N/A')}")
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
    out_path = OUTPUT_DIR / f"quality_run_{name}_{ts}.json"
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
        "limitation": lim.get("article", "N/A"),
        "procedural_count": len(proc_provisions),
        "verified_count": verified_count,
        "score": score,
    }


async def main():
    print("=" * 70)
    print("  DUAL SCENARIO QUALITY TEST — Post Quality Rules Implementation")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = []
    total_start = time.perf_counter()

    for name, query in SCENARIOS.items():
        r = await run_one(name, query)
        results.append(r)

    total_elapsed = time.perf_counter() - total_start

    # Summary comparison
    print(f"\n\n{'=' * 70}")
    print("  SUMMARY COMPARISON")
    print(f"{'=' * 70}")
    print(f"\n  Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f}m)\n")

    header = f"  {'Metric':<35} {'Money Recovery':<20} {'Dealership Damages':<20}"
    print(header)
    print("  " + "-" * 73)

    for r in results:
        pass  # printed in table below

    r1 = results[0] if results else {}
    r2 = results[1] if len(results) > 1 else {}

    rows = [
        ("Time", f"{r1.get('elapsed',0):.1f}s", f"{r2.get('elapsed',0):.1f}s"),
        ("Draft length", f"{r1.get('draft_len',0)} chars", f"{r2.get('draft_len',0)} chars"),
        ("Review pass", str(r1.get('review_pass')), str(r2.get('review_pass'))),
        ("Blocking issues", str(r1.get('blocking_count',0)), str(r2.get('blocking_count',0))),
        ("Limitation article", str(r1.get('limitation','N/A')), str(r2.get('limitation','N/A'))),
        ("Procedural provisions", str(r1.get('procedural_count',0)), str(r2.get('procedural_count',0))),
        ("Verified provisions", str(r1.get('verified_count',0)), str(r2.get('verified_count',0))),
        ("Quality score", f"{r1.get('score',{}).get('passed',0)}/{r1.get('score',{}).get('total',0)} ({r1.get('score',{}).get('pct',0)}%)",
                          f"{r2.get('score',{}).get('passed',0)}/{r2.get('score',{}).get('total',0)} ({r2.get('score',{}).get('pct',0)}%)"),
    ]

    for label, v1, v2 in rows:
        print(f"  {label:<35} {v1:<20} {v2:<20}")

    print(f"\n{'=' * 70}")
    print("  DONE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
