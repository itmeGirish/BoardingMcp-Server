"""
Run a single pipeline scenario and save output.
Usage: python research/run_pipeline_scenario.py <scenario_name>
"""
from __future__ import annotations
import asyncio, json, sys, time, re
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
        "Include cause of action paragraph, valuation, court fee, and verification clause. "
        "Draft suitable for filing before the District Court."
    ),
    "partition": (
        "Draft a suit for partition and separate possession of ancestral joint family property "
        "situated at Bangalore. The Plaintiff and Defendants are Hindu co-owners who inherited "
        "the property from their deceased father. The property includes a residential house at "
        "No. 42, 3rd Cross, Jayanagar, Bangalore measuring 2400 sq.ft. and agricultural land "
        "at Survey No. 85, Anekal Taluk, Bangalore Rural measuring 2 acres. "
        "The Defendants are denying the Plaintiff's rightful 1/3rd share and refusing to partition. "
        "Include genealogy table, schedule of properties, and prayer for appointment of Commissioner. "
        "Draft for City Civil Court, Bangalore."
    ),
    "injunction": (
        "Draft a suit for permanent injunction to restrain the Defendant from constructing "
        "on Plaintiff's land. Defendant is an adjacent land owner who encroached 200 sq.ft. "
        "and started construction. Plaintiff has clear title deed and possession since 2010. "
        "Seek mandatory injunction to demolish encroachment and permanent injunction "
        "against further encroachment. Include interim injunction prayer. Draft for District Court."
    ),
    "dealership": (
        "Draft a commercial suit seeking damages for illegal termination of dealership agreement. "
        "Plaintiff invested Rs.50,00,000/- capital and developed territory market over 5 years. "
        "Termination was arbitrary with only 15 days notice instead of 6 months required. "
        "Claim: loss of profit Rs.25,00,000/-, goodwill Rs.15,00,000/-, unsold stock Rs.10,00,000/-. "
        "Draft with breach of contract pleading for Commercial Court."
    ),
    "specific_performance": (
        "Draft a suit for specific performance of agreement to sell immovable property. "
        "Plaintiff entered into agreement to sell dated 15.06.2024 with Defendant for purchase "
        "of residential flat No. 301, Green Heights Apartments, HSR Layout, Bangalore for "
        "Rs.85,00,000/-. Plaintiff paid earnest money of Rs.10,00,000/-. "
        "Defendant now refuses to execute sale deed despite Plaintiff being ready and willing. "
        "Claim specific performance with alternative prayer for refund. Draft for District Court."
    ),
}


def _as_dict(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    fn = getattr(val, "model_dump", None)
    return fn() if callable(fn) else {}


async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "money_recovery"
    if name not in SCENARIOS:
        print(f"Unknown: {name}. Available: {list(SCENARIOS.keys())}")
        sys.exit(1)

    query = SCENARIOS[name]
    print(f"[PIPELINE] Running scenario: {name}")
    print(f"[PIPELINE] Query: {query[:80]}...")

    from app.agents.drafting_agents.drafting_graph import get_drafting_graph
    graph = get_drafting_graph()

    t0 = time.perf_counter()
    result = _as_dict(await graph.ainvoke({"user_request": query}))
    elapsed = time.perf_counter() - t0

    # Extract draft
    final_block = _as_dict(result.get("final_draft"))
    artifacts = final_block.get("draft_artifacts") or []
    draft_text = ""
    if artifacts:
        first = artifacts[0] if isinstance(artifacts[0], dict) else _as_dict(artifacts[0])
        draft_text = (first.get("text") or "").strip()
    else:
        draft_block = _as_dict(result.get("draft"))
        draft_arts = draft_block.get("draft_artifacts") or []
        if draft_arts:
            first = draft_arts[0] if isinstance(draft_arts[0], dict) else _as_dict(draft_arts[0])
            draft_text = (first.get("text") or "").strip()

    # Extract metadata
    intake = _as_dict(result.get("intake"))
    review_block = _as_dict(result.get("review"))
    review_data = _as_dict(review_block.get("review"))
    blocking = review_data.get("blocking_issues") or []

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save draft text
    draft_path = OUTPUT_DIR / f"bench_{name}_pipeline_{ts}.txt"
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(draft_text)

    # Save metadata
    meta = {
        "scenario": name,
        "source": "pipeline",
        "elapsed_s": round(elapsed, 1),
        "char_count": len(draft_text),
        "cause_type": intake.get("cause_type", ""),
        "doc_type": intake.get("doc_type", ""),
        "blocking_issues": len(blocking),
        "timestamp": ts,
    }
    meta_path = OUTPUT_DIR / f"bench_{name}_pipeline_{ts}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[PIPELINE] Done: {elapsed:.1f}s | {len(draft_text)} chars | Blocking: {len(blocking)}")
    print(f"[PIPELINE] Saved: {draft_path}")
    print(f"[PIPELINE] Cause type: {intake.get('cause_type', 'unknown')}")


if __name__ == "__main__":
    asyncio.run(main())
