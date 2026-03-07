"""
v8.1 Comparison: Pipeline Agent vs Claude Direct — Dealership Damages

Runs both drafts, scores them on 28 quality checks, and prints a side-by-side
comparison with speed/accuracy analysis.

Usage:
    agent_steer/Scripts/python.exe research/run_v8_compare.py
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

QUERY = (
    "Draft a commercial suit seeking damages for illegal termination of dealership agreement. "
    "Plaintiff invested substantial capital and developed territory market. "
    "Termination was arbitrary and contrary to agreement terms. "
    "Claim compensation for loss of profit, goodwill and unsold stock. "
    "Draft with proper breach of contract pleadings."
)

CLAUDE_SYSTEM = (
    "You are a senior Indian litigation lawyer with 25 years of courtroom practice. "
    "Draft the requested legal document exactly as it would appear when filed in an Indian court. "
    "Include all section headings (ALL CAPS), continuous paragraph numbering, "
    "verification clause, and advocate block. "
    "Use {{PLACEHOLDER_NAME}} format for any missing details like names, dates, addresses. "
    "Do NOT fabricate case citations (AIR, SCC, ILR). Use only statutory provisions. "
    "Output plain text only."
)


# ---------------------------------------------------------------------------
# Scoring (28 checks: 12 structural + 10 legal + 6 quality)
# ---------------------------------------------------------------------------

def score_dealership_draft(text: str) -> dict:
    t = " ".join(text.lower().split())
    def has(p): return bool(re.search(p, t))

    checks = {
        # ── STRUCTURAL (12) ──
        "[S1]  Court heading": has(r"in the court of"),
        "[S2]  Commercial Court designation": has(r"commercial\s+(court|division|suit)"),
        "[S3]  Parties section": has(r"plaintiff") and has(r"defendant"),
        "[S4]  Jurisdiction (territorial+pecuniary)": (
            has(r"territorial|resid|carries\s+on\s+business")
            and has(r"pecuniary|monetary|within.*limits")
        ),
        "[S5]  Section 12A / mediation": has(r"12.?a|mediation|pre.?institution"),
        "[S6]  Commercial Courts Act 2015": has(r"commercial\s+courts\s+act.*2015"),
        "[S7]  Narrative facts (25+ sentences)": len(re.findall(r"\.\s+", t)) >= 25,
        "[S8]  Capital investment detailed": has(r"invest") and has(r"capital|infrastructure|showroom|godown|stock"),
        "[S9]  Territory development pleaded": has(r"territory|market\s+(?:development|presence|base)"),
        "[S10] Termination illegality": has(r"illegal|arbitrary|without.+cause|without.+notice|contrary"),
        "[S11] Verification clause": has(r"verif"),
        "[S12] Advocate block": has(r"advocate|enrollment"),

        # ── LEGAL (10) ──
        "[L1]  Section 73 ICA (damages)": has(r"section\s+73.*contract\s+act"),
        "[L2]  Section 39 ICA (repudiation)": has(r"section\s+39.*contract\s+act") or has(r"repudiat"),
        "[L3]  Section 74 ICA (alternative)": has(r"section\s+74.*contract\s+act") or has(r"without\s+prejudice.*alternative"),
        "[L4]  Strong CoA (arose+further)": (
            has(r"first\s+arose|cause\s+of\s+action.*arose")
            and has(r"further\s+(?:arose|accrued|subsist)")
        ),
        "[L5]  Limitation Article 55 / 3 years": (
            has(r"article\s+55")
            or has(r"three\s+year.*limitation|limitation.*three\s+year")
        ),
        "[L6]  Valuation & court fee": has(r"valuation") and has(r"court\s+fee"),
        "[L7]  Interest (pendente lite)": has(r"pendente\s+lite|section\s+34\s+cpc|section\s+34.*civil"),
        "[L8]  No fabricated case citations": not has(r"\d{4}\s+scc\s+\d+") and not has(r"air\s+\d{4}"),
        "[L9]  Damages particularised (3 heads)": has(r"loss\s+of\s+profit") and has(r"goodwill") and has(r"unsold\s+stock"),
        "[L10] Mitigation pleaded": has(r"mitigat"),

        # ── QUALITY (6) ──
        "[Q1]  Prayer 5+ sub-items": len(re.findall(r"\([a-g]\)", t)) >= 5,
        "[Q2]  5+ Annexures": len(set(re.findall(r"annexure[-\s]*([a-l])", t, re.IGNORECASE))) >= 5,
        "[Q3]  No drafting-notes language": (
            not has(r"to\s+be\s+verif")
            and not has(r"\btbd\b|\btodo\b|\bplaceholder\b(?!\s*})")
        ),
        "[Q4]  Facts-law separation": not bool(re.search(
            r"facts\s+of\s+the\s+case\s+.*?section\s+\d+\s+of\s+the\s+(?:indian|contract)",
            t, re.DOTALL,
        )),
        "[Q5]  No and/or usage": not has(r"\band/or\b"),
        "[Q6]  Legal basis section": has(r"legal\s+basis|grounds?\s+of\s+(?:suit|action)"),
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "pct": round(passed / total * 100, 1),
    }


def _as_dict(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    fn = getattr(val, "model_dump", None)
    return fn() if callable(fn) else {}


# ---------------------------------------------------------------------------
# Pipeline run
# ---------------------------------------------------------------------------

async def run_pipeline() -> tuple[str, float, dict]:
    """Run drafting pipeline, return (draft_text, elapsed_seconds, raw_state)."""
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph

    graph = get_drafting_graph()
    t0 = time.perf_counter()
    result = _as_dict(await graph.ainvoke({"user_request": QUERY}))
    elapsed = time.perf_counter() - t0

    # Extract draft text
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

    return draft_text, elapsed, result


# ---------------------------------------------------------------------------
# Claude direct run
# ---------------------------------------------------------------------------

async def run_claude_direct() -> tuple[str, float]:
    """Run Claude/OpenAI direct, return (draft_text, elapsed_seconds)."""
    from app.config import settings
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    model_name = "gpt-4.1"

    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": CLAUDE_SYSTEM},
            {"role": "user", "content": QUERY},
        ],
        temperature=0.3,
        max_tokens=8000,
    )
    elapsed = time.perf_counter() - t0
    draft_text = response.choices[0].message.content or ""
    return draft_text, elapsed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print("=" * 80)
    print("  v8.1 COMPARISON: Pipeline Agent vs Claude Direct")
    print(f"  Scenario: Dealership Damages (Commercial Suit)")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"\nQuery: {QUERY[:100]}...\n")

    # --- Run both ---
    print("[1/2] Running Pipeline Agent...")
    pipeline_text, pipeline_time, pipeline_state = await run_pipeline()
    print(f"      Done: {pipeline_time:.1f}s | {len(pipeline_text)} chars\n")

    print("[2/2] Running Claude Direct (gpt-4.1)...")
    claude_text, claude_time = await run_claude_direct()
    print(f"      Done: {claude_time:.1f}s | {len(claude_text)} chars\n")

    # --- Score both ---
    pipeline_score = score_dealership_draft(pipeline_text)
    claude_score = score_dealership_draft(claude_text)

    # --- Extract pipeline metadata ---
    review_block = _as_dict(pipeline_state.get("review"))
    review_data = _as_dict(review_block.get("review"))
    blocking = review_data.get("blocking_issues") or []
    mandatory = _as_dict(pipeline_state.get("mandatory_provisions"))
    verified = mandatory.get("verified_provisions") or []
    errors = pipeline_state.get("errors") or []

    # --- Print comparison table ---
    print("=" * 80)
    print("  SIDE-BY-SIDE COMPARISON")
    print("=" * 80)
    print()
    print(f"  {'Metric':<45} {'Pipeline':<18} {'Claude Direct':<18}")
    print("  " + "-" * 78)
    print(f"  {'Time':<45} {pipeline_time:>6.1f}s          {claude_time:>6.1f}s")
    print(f"  {'Draft length':<45} {len(pipeline_text):>6} chars     {len(claude_text):>6} chars")
    print(f"  {'RAG-augmented':<45} {'Yes':>6}            {'No':>6}")
    print(f"  {'Verified provisions':<45} {len(verified):>6}            {'0':>6}")
    print(f"  {'Evidence anchoring':<45} {'Yes':>6}            {'No':>6}")
    print(f"  {'Citation validation':<45} {'Yes':>6}            {'No':>6}")
    print(f"  {'LKB compliance':<45} {'Yes':>6}            {'No':>6}")
    print(f"  {'Review blocking issues':<45} {len(blocking):>6}            {'N/A':>6}")
    print()

    print(f"  {'Quality Check':<45} {'Pipeline':<18} {'Claude Direct':<18}")
    print("  " + "-" * 78)

    pipeline_wins = 0
    claude_wins = 0
    ties = 0

    for check in pipeline_score["checks"]:
        p = pipeline_score["checks"][check]
        c = claude_score["checks"][check]
        ps = "PASS" if p else "FAIL"
        cs = "PASS" if c else "FAIL"

        if p and not c:
            pipeline_wins += 1
            marker = " <<<"
        elif c and not p:
            claude_wins += 1
            marker = "              <<<"
        else:
            ties += 1
            marker = ""

        print(f"  {check:<45} {ps:<18} {cs:<18}{marker}")

    print("  " + "-" * 78)
    print(f"  {'TOTAL SCORE':<45} {pipeline_score['passed']}/{pipeline_score['total']} ({pipeline_score['pct']}%)       {claude_score['passed']}/{claude_score['total']} ({claude_score['pct']}%)")
    print()

    print("  " + "-" * 78)
    print(f"  Pipeline wins:  {pipeline_wins} checks")
    print(f"  Claude wins:    {claude_wins} checks")
    print(f"  Ties:           {ties} checks")
    print()

    # --- Speed analysis ---
    print("=" * 80)
    print("  SPEED ANALYSIS")
    print("=" * 80)
    speedup = claude_time / pipeline_time if pipeline_time > 0 else 0
    if pipeline_time < claude_time:
        print(f"  Pipeline is {speedup:.1f}x FASTER than Claude Direct")
    elif pipeline_time > claude_time:
        print(f"  Claude Direct is {1/speedup:.1f}x FASTER than Pipeline")
    else:
        print(f"  Both took similar time")
    print(f"  Pipeline: {pipeline_time:.1f}s (includes intake + RAG + enrichment + draft + gates + review)")
    print(f"  Claude:   {claude_time:.1f}s (single API call, no validation)")
    print()

    # --- Accuracy analysis ---
    print("=" * 80)
    print("  ACCURACY ANALYSIS")
    print("=" * 80)
    diff = pipeline_score["pct"] - claude_score["pct"]
    if diff > 0:
        print(f"  Pipeline scores +{diff:.1f}% HIGHER than Claude Direct")
    elif diff < 0:
        print(f"  Claude Direct scores +{abs(diff):.1f}% HIGHER than Pipeline")
    else:
        print(f"  Both score equally")

    # Pipeline-only passes
    pipeline_only = [k for k in pipeline_score["checks"]
                     if pipeline_score["checks"][k] and not claude_score["checks"][k]]
    claude_only = [k for k in claude_score["checks"]
                   if claude_score["checks"][k] and not pipeline_score["checks"][k]]

    if pipeline_only:
        print(f"\n  Pipeline passes that Claude misses ({len(pipeline_only)}):")
        for c in pipeline_only:
            print(f"    + {c}")

    if claude_only:
        print(f"\n  Claude passes that Pipeline misses ({len(claude_only)}):")
        for c in claude_only:
            print(f"    + {c}")

    # --- Blocking issues ---
    if blocking:
        print(f"\n  Pipeline Review Issues ({len(blocking)}):")
        for i, b in enumerate(blocking, 1):
            if isinstance(b, dict):
                sev = b.get("severity", "legal")
                print(f"    [{i}] [{sev.upper()}] {b.get('issue', '')}")

    if errors:
        print(f"\n  Pipeline Errors ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")

    print()

    # --- Save outputs ---
    out = {
        "scenario": "dealership_damages",
        "query": QUERY,
        "timestamp": ts,
        "pipeline": {
            "time_s": round(pipeline_time, 1),
            "draft_chars": len(pipeline_text),
            "score": pipeline_score["passed"],
            "total": pipeline_score["total"],
            "pct": pipeline_score["pct"],
            "checks": {k: v for k, v in pipeline_score["checks"].items()},
            "blocking_issues": len(blocking),
            "verified_provisions": len(verified),
        },
        "claude_direct": {
            "time_s": round(claude_time, 1),
            "draft_chars": len(claude_text),
            "score": claude_score["passed"],
            "total": claude_score["total"],
            "pct": claude_score["pct"],
            "checks": {k: v for k, v in claude_score["checks"].items()},
        },
        "comparison": {
            "pipeline_wins": pipeline_wins,
            "claude_wins": claude_wins,
            "ties": ties,
            "score_diff_pct": round(diff, 1),
        },
    }

    json_path = OUTPUT_DIR / f"v8_compare_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    pipeline_path = OUTPUT_DIR / f"v8_compare_pipeline_{ts}.txt"
    with open(pipeline_path, "w", encoding="utf-8") as f:
        f.write(pipeline_text)

    claude_path = OUTPUT_DIR / f"v8_compare_claude_{ts}.txt"
    with open(claude_path, "w", encoding="utf-8") as f:
        f.write(claude_text)

    print(f"  Results saved → {json_path.name}")
    print(f"  Pipeline draft → {pipeline_path.name}")
    print(f"  Claude draft   → {claude_path.name}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
