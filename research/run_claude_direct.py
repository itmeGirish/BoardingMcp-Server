"""
Claude/GPT direct draft — no pipeline, no RAG, no enrichment.
Pure LLM output for comparison with v4.0 and v5.0.

Usage: agent_steer/Scripts/python.exe research/run_claude_direct.py [scenario]
"""
from __future__ import annotations

import asyncio
import json
import os
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
    "partition": (
        "Draft a suit for partition and separate possession of ancestral joint family property "
        "situated at Bangalore. The Plaintiff and Defendants are Hindu co-owners who inherited "
        "the property from their deceased father. The property includes a residential house at "
        "No. 42, 3rd Cross, Jayanagar, Bangalore measuring 2400 sq.ft. and agricultural land "
        "at Survey No. 85, Anekal Taluk, Bangalore Rural measuring 2 acres. "
        "The Defendants are denying the Plaintiff's rightful 1/3rd share and refusing to partition. "
        "Claim mesne profits for exclusion from possession. "
        "Include genealogy table, schedule of properties, and prayer for appointment of Commissioner. "
        "Draft suitable for filing before the City Civil Court, Bangalore."
    ),
    "injunction": (
        "Draft a suit for permanent injunction to restrain the Defendant from constructing "
        "on Plaintiff's property. The Defendant is an adjacent land owner who has encroached "
        "upon 200 sq.ft. of Plaintiff's land and started construction. "
        "Plaintiff has clear title deed and possession since 2010. "
        "Seek mandatory injunction to demolish the encroachment and permanent injunction "
        "against further encroachment. Include prayer for interim injunction. "
        "Draft for District Court."
    ),
    "dealership": (
        "Draft a commercial suit seeking damages for illegal termination of dealership agreement. "
        "Plaintiff invested Rs.50,00,000/- capital and developed territory market over 5 years. "
        "Termination was arbitrary and contrary to agreement terms requiring 6 months notice. "
        "Only 15 days notice given. Claim compensation for loss of profit Rs.25,00,000/-, "
        "goodwill Rs.15,00,000/- and unsold stock Rs.10,00,000/-. "
        "Draft with proper breach of contract pleading for Commercial Court."
    ),
}

SYSTEM_PROMPT = (
    "You are a senior Indian litigation lawyer with 25 years of courtroom practice. "
    "Draft the requested legal document exactly as it would appear when filed in an Indian court. "
    "Include all section headings (ALL CAPS), continuous paragraph numbering, "
    "verification clause, and advocate block. "
    "Use {{PLACEHOLDER_NAME}} format for any missing details like names, dates, addresses. "
    "Do NOT fabricate case citations (AIR, SCC, ILR). Use only statutory provisions. "
    "Output plain text only."
)


async def main():
    scenario_name = sys.argv[1] if len(sys.argv) > 1 else "partition"
    if scenario_name not in SCENARIOS:
        print(f"Unknown scenario: {scenario_name}")
        print(f"Available: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)

    query = SCENARIOS[scenario_name]

    print("=" * 70)
    print(f"  CLAUDE/GPT DIRECT DRAFT — {scenario_name.upper()}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\nQuery: {query[:100]}...\n")

    from app.config import settings
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Use the same model as draft_openai_model in the pipeline
    model_name = "gpt-4.1"

    print(f"  Model: {model_name}")
    print(f"  Calling API...\n")

    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        temperature=0.3,
        max_tokens=8000,
    )
    elapsed = time.perf_counter() - t0

    draft_text = response.choices[0].message.content or ""
    tokens_in = response.usage.prompt_tokens if response.usage else 0
    tokens_out = response.usage.completion_tokens if response.usage else 0

    print(f"  Done: {elapsed:.1f}s | tokens_in={tokens_in} | tokens_out={tokens_out}")
    print(f"  Draft length: {len(draft_text)} chars\n")
    print("=" * 70)
    print("  DRAFT OUTPUT")
    print("=" * 70)
    print(draft_text)
    print("=" * 70)

    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    draft_path = OUTPUT_DIR / f"claude_direct_{scenario_name}_{ts}.txt"
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(draft_text)

    meta_path = OUTPUT_DIR / f"claude_direct_{scenario_name}_{ts}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "scenario": scenario_name,
            "query": query,
            "model": model_name,
            "elapsed_s": round(elapsed, 1),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "draft_length": len(draft_text),
            "timestamp": ts,
        }, f, indent=2)

    print(f"\n  Draft saved → {draft_path}")
    print(f"  Meta saved → {meta_path}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
