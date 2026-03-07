"""Run dealership scenario WITHOUT specific amounts — tests commercial court fallback."""
import asyncio, json, sys, time, re
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

QUERY = (
    "Draft a commercial suit seeking damages for illegal termination of dealership agreement. "
    "Plaintiff invested substantial capital and developed territory market. "
    "Termination was arbitrary and contrary to agreement terms. "
    "Claim compensation for loss of profit, goodwill and unsold stock. "
    "Draft with proper breach of contract pleading for Commercial Court."
)

def _as_dict(val):
    if val is None: return {}
    if isinstance(val, dict): return val
    fn = getattr(val, "model_dump", None)
    return fn() if callable(fn) else {}

async def main():
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph
    graph = get_drafting_graph()
    
    print("=" * 70)
    print("  DEALERSHIP (NO AMOUNTS) — v5.0 PIPELINE TEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\nQuery: {QUERY}\n")
    
    t0 = time.perf_counter()
    result = _as_dict(await graph.ainvoke({"user_request": QUERY}))
    elapsed = time.perf_counter() - t0
    
    # Extract draft
    draft = _as_dict(result.get("draft"))
    final = _as_dict(result.get("final_draft"))
    arts = (final.get("draft_artifacts") or draft.get("draft_artifacts") or [])
    text = ""
    if arts:
        first = arts[0] if isinstance(arts[0], dict) else _as_dict(arts[0])
        text = (first.get("text") or "").strip()
    
    # Extract enrichment info
    enrichment = _as_dict(result.get("mandatory_provisions"))
    lim = _as_dict(enrichment.get("limitation"))
    lkb = _as_dict(result.get("lkb_brief"))
    detected_court = _as_dict(lkb.get("detected_court"))
    
    # Intake amounts
    intake = _as_dict(result.get("intake"))
    facts = _as_dict(intake.get("facts"))
    amounts = _as_dict(facts.get("amounts"))
    
    print(f"\n  Elapsed: {elapsed:.1f}s")
    print(f"  Draft length: {len(text)} chars")
    print(f"  Limitation: {lim.get('article', 'NOT_SET')}")
    print(f"  Detected court: {detected_court.get('court', 'NOT_SET')}")
    print(f"  Intake amounts: {amounts}")
    print(f"  Commercial court detected: {'Commercial' in detected_court.get('court', '')}")
    
    # Key checks
    t_lower = text.lower()
    checks = {
        "Commercial Court heading": "commercial court" in t_lower or "commercial division" in t_lower,
        "Commercial Suit No.": "commercial suit no" in t_lower,
        "Section 12A compliance": "section 12a" in t_lower or "pre-institution mediation" in t_lower,
        "Statement of Truth": "statement of truth" in t_lower,
        "Damages schedule": "particulars of damages" in t_lower or "damages schedule" in t_lower,
        "Section 73 cited": "section 73" in t_lower,
        "NO Section 55 misapplied": "section 55" not in t_lower or "limitation" in t_lower[max(0,t_lower.find("section 55")-50):t_lower.find("section 55")+50] if "section 55" in t_lower else True,
        "NO Section 14 SRA": "section 14" not in t_lower or "specific relief" not in t_lower,
        "Section 39 cited": "section 39" in t_lower,
    }
    
    passed = sum(1 for v in checks.values() if v)
    print(f"\n  KEY CHECKS: {passed}/{len(checks)}")
    for k, v in checks.items():
        print(f"    {'PASS' if v else 'FAIL'} | {k}")
    
    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(OUTPUT_DIR / f"v5_dealership_noamount_{ts}.txt", "w", encoding="utf-8") as f:
        f.write(text)
    
    save = {
        "query": QUERY,
        "elapsed_s": round(elapsed, 1),
        "draft_length": len(text),
        "limitation": lim,
        "detected_court": detected_court,
        "intake_amounts": amounts,
        "checks": checks,
        "passed": passed,
        "total": len(checks),
    }
    with open(OUTPUT_DIR / f"v5_dealership_noamount_{ts}.json", "w", encoding="utf-8") as f:
        json.dump(save, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n  Draft saved -> output/v5_dealership_noamount_{ts}.txt")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
