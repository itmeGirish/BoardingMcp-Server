"""
Compare: Draft Agent (pipeline) vs Claude Direct for possession scenario.
Runs both, saves outputs, prints execution times.

Usage: agent_steer/Scripts/python.exe research/run_possession_compare.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

QUERY = (
    "Draft a civil suit for recovery of possession of immovable property. "
    "Plaintiff is owner of the property and Defendant is in unauthorized occupation "
    "after expiry of permissive possession/lease. "
    "Defendant refusing to vacate despite legal notice. "
    "Seek recovery of possession, mesne profits, and costs."
)


def _as_dict(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if hasattr(val, "dict"):
        return val.dict()
    if hasattr(val, "model_dump"):
        return val.model_dump()
    return {}


async def run_pipeline():
    """Run the full draft agent pipeline."""
    from app.agents.drafting_agents.drafting_graph import drafting_graph

    print("=" * 80)
    print("DRAFT AGENT (pipeline)")
    print("=" * 80)

    t0 = time.perf_counter()
    result = await drafting_graph.ainvoke({"user_request": QUERY})
    elapsed = time.perf_counter() - t0

    draft = _as_dict(result.get("draft"))
    artifacts = draft.get("draft_artifacts", [])
    text = artifacts[0].get("text", "") if artifacts else ""

    # Get classify info
    classify = _as_dict(result.get("classify"))
    cause_type = classify.get("cause_type", "unknown")
    doc_type = classify.get("doc_type", "unknown")

    print(f"\nDoc type: {doc_type}")
    print(f"Cause type: {cause_type}")
    print(f"Time: {elapsed:.1f}s")
    print(f"Chars: {len(text)}")
    print(f"\n{'─' * 60}")
    print(text[:8000])
    print(f"{'─' * 60}")

    # Check errors
    errors = result.get("errors", [])
    if errors:
        print(f"\nErrors: {errors}")

    return text, elapsed


async def run_claude_direct():
    """Run Claude/qwen direct — no pipeline, no RAG, no LKB."""
    from app.services.llm_service import draft_ollama_model

    print("\n" + "=" * 80)
    print("DIRECT LLM (no pipeline)")
    print("=" * 80)

    model = draft_ollama_model.resolve_model()

    system_prompt = (
        "You are a senior Indian litigation lawyer with 25 years of courtroom practice. "
        "Draft the complete legal document exactly as it would appear when filed in court. "
        "Include all section headings (ALL CAPS), continuous paragraph numbering, "
        "verification clause, and advocate block. "
        "Output plain text only. Use {{PLACEHOLDER}} for missing details."
    )

    from langchain_core.messages import SystemMessage, HumanMessage

    t0 = time.perf_counter()
    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=QUERY),
    ])
    elapsed = time.perf_counter() - t0

    text = getattr(response, "content", "") or ""

    print(f"\nTime: {elapsed:.1f}s")
    print(f"Chars: {len(text)}")
    print(f"\n{'─' * 60}")
    print(text[:8000])
    print(f"{'─' * 60}")

    return text, elapsed


async def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Run both
    pipeline_text, pipeline_time = await run_pipeline()
    direct_text, direct_time = await run_claude_direct()

    # Save outputs
    result = {
        "query": QUERY,
        "timestamp": ts,
        "pipeline": {
            "text": pipeline_text,
            "time_s": round(pipeline_time, 1),
            "chars": len(pipeline_text),
        },
        "direct": {
            "text": direct_text,
            "time_s": round(direct_time, 1),
            "chars": len(direct_text),
        },
    }

    out_json = OUTPUT_DIR / f"possession_compare_{ts}.json"
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # Save texts separately for easy reading
    (OUTPUT_DIR / f"possession_pipeline_{ts}.txt").write_text(
        pipeline_text, encoding="utf-8"
    )
    (OUTPUT_DIR / f"possession_direct_{ts}.txt").write_text(
        direct_text, encoding="utf-8"
    )

    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print(f"Pipeline: {pipeline_time:.1f}s | {len(pipeline_text)} chars")
    print(f"Direct:   {direct_time:.1f}s | {len(direct_text)} chars")
    print(f"\nSaved to: {out_json}")


if __name__ == "__main__":
    asyncio.run(main())
