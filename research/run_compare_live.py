"""
Live pipeline run for dealership damages comparison.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

QUERY = (
    "Draft a commercial suit seeking damages for illegal termination of dealership agreement. "
    "Plaintiff invested substantial capital and developed territory market. "
    "Termination was arbitrary and contrary to agreement terms. "
    "Claim compensation for loss of profit, goodwill and unsold stock. "
    "Draft with proper breach of contract pleading."
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


async def main():
    import time as _time
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph

    print("=" * 70)
    print("PIPELINE RUN — Dealership Damages Scenario")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    graph = get_drafting_graph()
    t_start = _time.perf_counter()
    result = _as_dict(await graph.ainvoke({"user_request": QUERY}))
    total_elapsed = _time.perf_counter() - t_start
    print(f"\nTOTAL PIPELINE TIME: {total_elapsed:.1f}s")

    # Extract final draft
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

    # Extract review
    review_block = _as_dict(result.get("review"))
    review_data = _as_dict(review_block.get("review"))
    blocking = review_data.get("blocking_issues") or []

    # Extract enrichment info
    mandatory = _as_dict(result.get("mandatory_provisions"))
    proc_provisions = mandatory.get("procedural_provisions") or []
    verified_provisions = mandatory.get("verified_provisions") or []
    proc_context = (mandatory.get("procedural_context") or "")[:500]

    print(f"\nSOURCE: {source}")
    print(f"DRAFT LENGTH: {len(draft_text)} chars")
    print(f"BLOCKING ISSUES: {len(blocking)}")
    print(f"PROCEDURAL PROVISIONS: {len(proc_provisions)}")
    print(f"VERIFIED PROVISIONS: {len(verified_provisions)}")
    print(f"\n{'='*70}")
    print("DRAFT TEXT:")
    print("="*70)
    print(draft_text)
    print(f"\n{'='*70}")

    if blocking:
        print("\nBLOCKING ISSUES:")
        for i, b in enumerate(blocking, 1):
            if isinstance(b, dict):
                print(f"  [{i}] [{b.get('severity','?')}] {b.get('issue','')}")

    if proc_provisions:
        print("\nPROCEDURAL PROVISIONS FOUND:")
        for p in proc_provisions:
            if isinstance(p, dict):
                print(f"  - {p.get('section','')} of {p.get('act','')}")

    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"compare_pipeline_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
