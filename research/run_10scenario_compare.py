"""
10-Scenario Civil Draft Comparison: Pipeline vs Claude Direct.

Tests 10 diverse civil scenarios through:
  1. Full pipeline (v5.0 free-text)
  2. Claude direct (single LLM call, no pipeline)

Scores both outputs using a universal legal quality checker,
then produces a side-by-side comparison report.

Usage:
    agent_steer/Scripts/python.exe research/run_10scenario_compare.py
    agent_steer/Scripts/python.exe research/run_10scenario_compare.py --scenario partition
    agent_steer/Scripts/python.exe research/run_10scenario_compare.py --claude-only
    agent_steer/Scripts/python.exe research/run_10scenario_compare.py --pipeline-only
"""
from __future__ import annotations

import argparse
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

# ═══════════════════════════════════════════════════════════════════════════════
# 10 DIVERSE CIVIL SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIOS = {
    # 1. Money Recovery (Section 65 ICA)
    "money_recovery": {
        "query": (
            "Draft a suit for recovery of Rs.20,00,000/- paid as advance for a business transaction "
            "which failed due to Defendant's default. "
            "Plead total failure of consideration under Section 65 of Indian Contract Act. "
            "Claim refund with interest and costs. "
            "Include cause of action paragraph, valuation, court fee, and verification clause. "
            "Draft suitable for filing before the District Court."
        ),
        "expected_acts": ["Indian Contract Act", "Section 65"],
        "expected_sections": ["FACTS", "CAUSE OF ACTION", "PRAYER", "VERIFICATION"],
        "cause_type": "failure_of_consideration",
    },

    # 2. Partition Suit
    "partition": {
        "query": (
            "Draft a suit for partition and separate possession of ancestral joint family property "
            "situated at Bangalore. The Plaintiff and Defendants are Hindu co-owners who inherited "
            "the property from their deceased father. The property includes a residential house at "
            "No. 42, 3rd Cross, Jayanagar, Bangalore measuring 2400 sq.ft. and agricultural land "
            "at Survey No. 85, Anekal Taluk, Bangalore Rural measuring 2 acres. "
            "The Defendants are denying the Plaintiff's rightful 1/3rd share and refusing to partition. "
            "Include genealogy table, schedule of properties, and prayer for appointment of Commissioner. "
            "Draft for City Civil Court, Bangalore."
        ),
        "expected_acts": ["Hindu Succession Act", "Code of Civil Procedure"],
        "expected_sections": ["GENEALOGY", "SCHEDULE OF PROPERTY", "PRAYER"],
        "cause_type": "partition",
    },

    # 3. Permanent Injunction
    "injunction": {
        "query": (
            "Draft a suit for permanent injunction to restrain the Defendant from constructing "
            "on Plaintiff's land. Defendant is an adjacent land owner who encroached 200 sq.ft. "
            "and started construction. Plaintiff has clear title deed and possession since 2010. "
            "Seek mandatory injunction to demolish encroachment and permanent injunction "
            "against further encroachment. Include interim injunction prayer. Draft for District Court."
        ),
        "expected_acts": ["Specific Relief Act", "Section 38", "Section 39"],
        "expected_sections": ["PLAINTIFF'S RIGHT", "PRAYER", "VERIFICATION"],
        "cause_type": "permanent_injunction",
    },

    # 4. Dealership Damages
    "dealership": {
        "query": (
            "Draft a commercial suit seeking damages for illegal termination of dealership agreement. "
            "Plaintiff invested Rs.50,00,000/- capital and developed territory market over 5 years. "
            "Termination was arbitrary with only 15 days notice instead of 6 months required. "
            "Claim: loss of profit Rs.25,00,000/-, goodwill Rs.15,00,000/-, unsold stock Rs.10,00,000/-. "
            "Draft with breach of contract pleading for Commercial Court."
        ),
        "expected_acts": ["Indian Contract Act", "Section 73", "Commercial Courts Act"],
        "expected_sections": ["AGREEMENT DETAILS", "DAMAGES", "PRAYER"],
        "cause_type": "breach_dealership_franchise",
    },

    # 5. Specific Performance
    "specific_performance": {
        "query": (
            "Draft a suit for specific performance of agreement to sell immovable property. "
            "Plaintiff entered into agreement to sell dated 15.06.2024 with Defendant for purchase "
            "of residential flat No. 301, Green Heights Apartments, HSR Layout, Bangalore for "
            "Rs.85,00,000/-. Plaintiff paid earnest money of Rs.10,00,000/-. "
            "Defendant now refuses to execute sale deed despite Plaintiff being ready and willing. "
            "Claim specific performance with alternative prayer for refund. Draft for District Court."
        ),
        "expected_acts": ["Specific Relief Act", "Section 10", "Section 16"],
        "expected_sections": ["READINESS AND WILLINGNESS", "SCHEDULE OF PROPERTY", "PRAYER"],
        "cause_type": "specific_performance",
    },

    # 6. Defamation
    "defamation": {
        "query": (
            "Draft a civil suit for damages for defamation. The Defendant published false and "
            "defamatory statements about the Plaintiff on social media (Facebook and Twitter) on "
            "10.01.2026, alleging that the Plaintiff is involved in financial fraud and cheating. "
            "The statements were viewed by over 5000 people and caused severe damage to Plaintiff's "
            "business reputation. Plaintiff lost 3 major clients worth Rs.15,00,000/- in business. "
            "Claim damages of Rs.25,00,000/- and permanent injunction against repetition. "
            "Draft for District Court."
        ),
        "expected_acts": ["Law of Torts", "Defamation"],
        "expected_sections": ["DEFAMATORY STATEMENT", "PUBLICATION", "PRAYER"],
        "cause_type": "defamation",
    },

    # 7. Recovery of Possession
    "recovery_possession": {
        "query": (
            "Draft a suit for recovery of possession of immovable property. Plaintiff is the owner "
            "of a commercial property at No. 15, MG Road, Bangalore. The Defendant was a licensee "
            "whose licence was revoked on 01.06.2025. Despite revocation notice, Defendant continues "
            "to occupy the premises. Claim recovery of possession and mesne profits at Rs.50,000/- "
            "per month from date of revocation. Draft for City Civil Court."
        ),
        "expected_acts": ["Specific Relief Act", "Section 5", "Code of Civil Procedure"],
        "expected_sections": ["TITLE AND OWNERSHIP", "SCHEDULE OF PROPERTY", "PRAYER"],
        "cause_type": "recovery_of_possession",
    },

    # 8. Breach of Construction Agreement
    "construction_breach": {
        "query": (
            "Draft a suit for damages for breach of construction agreement. Plaintiff engaged "
            "Defendant (contractor) to construct a residential house at Survey No. 45, Whitefield, "
            "Bangalore for Rs.1,20,00,000/- with completion deadline of 31.12.2025. "
            "Defendant abandoned work after receiving Rs.80,00,000/- with only 60% work completed. "
            "Cost of completion by another contractor estimated at Rs.70,00,000/-. "
            "Claim damages for breach including cost overrun and delay. Draft for District Court."
        ),
        "expected_acts": ["Indian Contract Act", "Section 73"],
        "expected_sections": ["AGREEMENT DETAILS", "CONSTRUCTION STATUS", "DAMAGES", "PRAYER"],
        "cause_type": "breach_construction",
    },

    # 9. Declaration of Title
    "declaration_title": {
        "query": (
            "Draft a suit for declaration of title to immovable property. Plaintiff purchased "
            "property at Survey No. 120, Yelahanka Hobli, Bangalore North from one Mr. Ramesh "
            "through registered sale deed dated 10.03.2020. The Defendant claims title based on "
            "an unregistered agreement and is creating cloud on Plaintiff's title by threatening "
            "to sell the same property to third parties. Seek declaration and consequential injunction. "
            "Draft for District Court."
        ),
        "expected_acts": ["Specific Relief Act", "Section 34"],
        "expected_sections": ["CHAIN OF TITLE", "SCHEDULE OF PROPERTY", "PRAYER"],
        "cause_type": "declaration_title",
    },

    # 10. Eviction
    "eviction": {
        "query": (
            "Draft an eviction petition under Karnataka Rent Act. Landlord seeks eviction of tenant "
            "from a commercial premises at No. 88, Commercial Street, Bangalore. "
            "Ground: bona fide personal need of landlord to start own business. "
            "Tenant has been paying rent of Rs.25,000/- per month. Tenancy since 01.01.2018. "
            "Landlord issued notice to quit on 01.01.2026 giving 6 months notice. "
            "Draft for Court exercising jurisdiction under Karnataka Rent Act."
        ),
        "expected_acts": ["Karnataka Rent Act", "Transfer of Property Act"],
        "expected_sections": ["TENANCY DETAILS", "STATUTORY GROUND", "NOTICE", "PRAYER"],
        "cause_type": "eviction",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# UNIVERSAL QUALITY SCORER
# ═══════════════════════════════════════════════════════════════════════════════

def score_draft(text: str, scenario: dict) -> dict:
    """Score a draft on 25 universal quality criteria."""
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {}

    # ── STRUCTURE (8 checks) ────────────────────────────────────────────────
    checks["S1: Title/cause heading present"] = has(r"in the court of|before the")
    checks["S2: Parties section"] = has(r"plaintiff|petitioner") and has(r"defendant|respondent")
    checks["S3: Facts section present"] = has(r"facts|brief facts|statement of facts")
    checks["S4: Cause of action"] = has(r"cause of action")
    checks["S5: Prayer/relief section"] = has(r"prayer|relief|wherefore")
    checks["S6: Verification clause"] = has(r"verif")
    checks["S7: Advocate block or place/date"] = has(r"advocate|counsel|place|through")
    checks["S8: Continuous para numbering"] = bool(re.findall(r"(?:^|\n)\s*\d+\.\s", text)) and len(re.findall(r"(?:^|\n)\s*\d+\.\s", text)) >= 5

    # ── LEGAL SUBSTANCE (7 checks) ─────────────────────────────────────────
    checks["L1: Expected act(s) cited"] = any(has(re.escape(a.lower())) for a in scenario.get("expected_acts", []))
    checks["L2: Jurisdiction pleaded"] = has(r"jurisdict|territorial|pecuniary|section\s+(?:9|15|16|19|20)")
    checks["L3: Limitation addressed"] = has(r"limitation|article\s+\d+|within\s+(?:the\s+)?(?:period|time)")
    checks["L4: Valuation stated"] = has(r"valuat|suit\s+is\s+valued|purposes?\s+of\s+(?:jurisdiction|court\s+fee)")
    checks["L5: Court fee mentioned"] = has(r"court\s+fee")
    checks["L6: No fabricated case law"] = not has(r"\d{4}\s+scc\s+\d+") and not has(r"air\s+\d{4}\s+sc")
    checks["L7: Relief specificity (3+ prayers)"] = (
        len(re.findall(r"\([a-z]\)", t)) >= 3
        or len(re.findall(r"(?:^|\n)\s*(?:[ivx]+\.|[a-z]\)|\d+\.\s*(?:that|a\s+decree|direct))", text, re.I)) >= 3
    )

    # ── DRAFTING QUALITY (10 checks) ───────────────────────────────────────
    checks["Q1: Narrative facts (not skeleton)"] = len(re.findall(r"\.\s+", t)) >= 12
    checks["Q2: Facts-law separation"] = True  # generous default
    facts_m = re.search(r"facts?\s+of\s+the\s+case\s+(.*?)(?:legal|cause\s+of|ground|jurisdiction)", t, re.DOTALL)
    if facts_m:
        checks["Q2: Facts-law separation"] = not bool(re.search(r"section\s+\d+\s+of\s+the", facts_m.group(1)))
    checks["Q3: No drafting-notes language"] = (
        not has(r"to\s+be\s+verif(?:ied|y)") and not has(r"\bplaceholder\b(?!\s*})") and not has(r"\btbd\b")
    )
    checks["Q4: Interest rate/basis stated"] = has(r"interest") and (has(r"\d+\s*%|per\s+(?:cent|annum)") or has(r"section\s+34\s+cpc|commercial\s+rate"))
    checks["Q5: Placeholder for unknowns"] = has(r"\{\{") or not has(r"mr\.\s+xyz|john\s+doe|abc\s+company")
    checks["Q6: Proper legal terminology"] = has(r"plaint|decree|suit|cause of action|prayer")
    checks["Q7: No and/or usage"] = not has(r"\band/or\b")
    checks["Q8: Annexure/document references"] = has(r"annexure|exhibit|document")
    checks["Q9: Draft length adequate (>2000 chars)"] = len(text) > 2000
    checks["Q10: Expected key sections present"] = sum(
        1 for s in scenario.get("expected_sections", [])
        if has(re.escape(s.lower()))
    ) >= len(scenario.get("expected_sections", [])) * 0.5

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "score": round(passed / total * 10, 1),
        "percent": round(passed / total * 100, 1),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def _as_dict(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    fn = getattr(val, "model_dump", None)
    return fn() if callable(fn) else {}


async def run_pipeline(scenario_name: str, query: str) -> dict:
    """Run query through the full drafting pipeline."""
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph

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

    # Extract classification
    intake_block = _as_dict(result.get("intake"))
    cause_type = intake_block.get("cause_type", "unknown")
    doc_type = intake_block.get("doc_type", "unknown")

    return {
        "draft_text": draft_text,
        "elapsed_s": round(elapsed, 1),
        "source": source,
        "blocking_issues": len(blocking),
        "cause_type": cause_type,
        "doc_type": doc_type,
        "char_count": len(draft_text),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLAUDE DIRECT RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

CLAUDE_SYSTEM = (
    "You are a senior Indian litigation lawyer with 25 years of courtroom practice. "
    "Draft the requested legal document exactly as it would appear when filed in an Indian court. "
    "Include all section headings (ALL CAPS), continuous paragraph numbering, "
    "verification clause, and advocate block. "
    "Use {{PLACEHOLDER_NAME}} format for any missing details like names, dates, addresses. "
    "Do NOT fabricate case citations (AIR, SCC, ILR). Use only statutory provisions. "
    "Output plain text only — not markdown, not JSON."
)


async def run_claude_direct(scenario_name: str, query: str) -> dict:
    """Run query through Claude/OpenAI directly — no pipeline."""
    from app.config import settings

    t0 = time.perf_counter()

    draft_text = ""
    model_used = ""
    tokens_in = 0
    tokens_out = 0

    # Try Anthropic if key exists, else OpenAI
    anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            model_used = "claude-sonnet-4-20250514"
            response = client.messages.create(
                model=model_used,
                max_tokens=8000,
                system=CLAUDE_SYSTEM,
                messages=[{"role": "user", "content": query}],
                temperature=0.3,
            )
            draft_text = response.content[0].text if response.content else ""
            tokens_in = response.usage.input_tokens if response.usage else 0
            tokens_out = response.usage.output_tokens if response.usage else 0
        except Exception as e1:
            print(f"    Anthropic failed ({e1}), falling back to OpenAI...")
            anthropic_key = ""  # trigger OpenAI fallback

    if not anthropic_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            model_used = "gpt-4.1"
            response = client.chat.completions.create(
                model=model_used,
                messages=[
                    {"role": "system", "content": CLAUDE_SYSTEM},
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                max_tokens=8000,
            )
            draft_text = response.choices[0].message.content or ""
            tokens_in = response.usage.prompt_tokens if response.usage else 0
            tokens_out = response.usage.completion_tokens if response.usage else 0
        except Exception as e2:
            print(f"    OpenAI failed ({e2})")
            draft_text = ""
            model_used = "FAILED"

    elapsed = time.perf_counter() - t0

    return {
        "draft_text": draft_text,
        "elapsed_s": round(elapsed, 1),
        "model": model_used,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "char_count": len(draft_text),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str, help="Run single scenario")
    parser.add_argument("--pipeline-only", action="store_true")
    parser.add_argument("--claude-only", action="store_true")
    args = parser.parse_args()

    scenarios_to_run = {args.scenario: SCENARIOS[args.scenario]} if args.scenario else SCENARIOS
    run_pipeline_flag = not args.claude_only
    run_claude_flag = not args.pipeline_only

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 80)
    print("  10-SCENARIO CIVIL DRAFT COMPARISON: PIPELINE vs CLAUDE DIRECT")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Scenarios: {len(scenarios_to_run)}")
    print(f"  Pipeline: {'YES' if run_pipeline_flag else 'SKIP'}")
    print(f"  Claude:   {'YES' if run_claude_flag else 'SKIP'}")
    print("=" * 80)

    results = {}

    for i, (name, scenario) in enumerate(scenarios_to_run.items(), 1):
        print(f"\n{'─' * 80}")
        print(f"  [{i}/{len(scenarios_to_run)}] SCENARIO: {name.upper()}")
        print(f"  Query: {scenario['query'][:80]}...")
        print(f"{'─' * 80}")

        result = {"scenario": name, "query": scenario["query"]}

        # ── Pipeline ────────────────────────────────────────────────────
        if run_pipeline_flag:
            print(f"\n  [PIPELINE] Running...")
            try:
                pipe_result = await run_pipeline(name, scenario["query"])
                pipe_score = score_draft(pipe_result["draft_text"], scenario)
                result["pipeline"] = {
                    **pipe_result,
                    "score": pipe_score,
                }
                print(f"  [PIPELINE] Done: {pipe_result['elapsed_s']}s | {pipe_result['char_count']} chars | Score: {pipe_score['score']}/10 ({pipe_score['passed']}/{pipe_score['total']})")

                # Print failed checks
                failed = [k for k, v in pipe_score["checks"].items() if not v]
                if failed:
                    print(f"  [PIPELINE] Failed: {', '.join(failed)}")
            except Exception as e:
                print(f"  [PIPELINE] ERROR: {e}")
                result["pipeline"] = {"error": str(e)}

        # ── Claude Direct ───────────────────────────────────────────────
        if run_claude_flag:
            print(f"\n  [CLAUDE] Running...")
            try:
                claude_result = await run_claude_direct(name, scenario["query"])
                claude_score = score_draft(claude_result["draft_text"], scenario)
                result["claude"] = {
                    **claude_result,
                    "score": claude_score,
                }
                print(f"  [CLAUDE] Done: {claude_result['elapsed_s']}s | {claude_result['char_count']} chars | Score: {claude_score['score']}/10 ({claude_score['passed']}/{claude_score['total']})")

                # Print failed checks
                failed = [k for k, v in claude_score["checks"].items() if not v]
                if failed:
                    print(f"  [CLAUDE] Failed: {', '.join(failed)}")
            except Exception as e:
                print(f"  [CLAUDE] ERROR: {e}")
                result["claude"] = {"error": str(e)}

        # ── Comparison ──────────────────────────────────────────────────
        if run_pipeline_flag and run_claude_flag and "error" not in result.get("pipeline", {}) and "error" not in result.get("claude", {}):
            ps = result["pipeline"]["score"]["score"]
            cs = result["claude"]["score"]["score"]
            diff = ps - cs
            winner = "PIPELINE" if diff > 0 else "CLAUDE" if diff < 0 else "TIE"
            result["comparison"] = {"pipeline_score": ps, "claude_score": cs, "diff": round(diff, 1), "winner": winner}
            print(f"\n  >>> WINNER: {winner} (Pipeline {ps} vs Claude {cs}, diff={diff:+.1f})")

        results[name] = result

    # ═══════════════════════════════════════════════════════════════════════
    # SUMMARY REPORT
    # ═══════════════════════════════════════════════════════════════════════
    print(f"\n\n{'=' * 80}")
    print("  SUMMARY REPORT")
    print(f"{'=' * 80}")

    if run_pipeline_flag and run_claude_flag:
        print(f"\n  {'SCENARIO':<25} {'PIPELINE':>10} {'CLAUDE':>10} {'DIFF':>8} {'WINNER':>10}")
        print(f"  {'─' * 25} {'─' * 10} {'─' * 10} {'─' * 8} {'─' * 10}")

        pipe_total = 0
        claude_total = 0
        pipe_wins = 0
        claude_wins = 0
        ties = 0

        for name, r in results.items():
            comp = r.get("comparison", {})
            ps = comp.get("pipeline_score", "ERR")
            cs = comp.get("claude_score", "ERR")
            diff = comp.get("diff", 0)
            winner = comp.get("winner", "ERR")

            if isinstance(ps, (int, float)) and isinstance(cs, (int, float)):
                pipe_total += ps
                claude_total += cs
                if winner == "PIPELINE":
                    pipe_wins += 1
                elif winner == "CLAUDE":
                    claude_wins += 1
                else:
                    ties += 1

            print(f"  {name:<25} {ps:>10} {cs:>10} {diff:>+8.1f} {winner:>10}")

        n = len([r for r in results.values() if "comparison" in r])
        if n > 0:
            print(f"\n  {'AVERAGE':<25} {pipe_total/n:>10.1f} {claude_total/n:>10.1f}")
            print(f"\n  Pipeline wins: {pipe_wins} | Claude wins: {claude_wins} | Ties: {ties}")

        # ── Identify gaps ───────────────────────────────────────────────
        print(f"\n\n{'=' * 80}")
        print("  GAP ANALYSIS: WHERE PIPELINE LOSES TO CLAUDE")
        print(f"{'=' * 80}")

        for name, r in results.items():
            comp = r.get("comparison", {})
            if comp.get("winner") == "CLAUDE":
                pipe_checks = r.get("pipeline", {}).get("score", {}).get("checks", {})
                claude_checks = r.get("claude", {}).get("score", {}).get("checks", {})

                # Checks where pipeline fails but Claude passes
                gaps = [k for k in pipe_checks if not pipe_checks[k] and claude_checks.get(k, False)]
                if gaps:
                    print(f"\n  {name.upper()} (Pipeline {comp['pipeline_score']} vs Claude {comp['claude_score']}):")
                    for g in gaps:
                        print(f"    - {g}")

        # ── What's needed to beat Claude ────────────────────────────────
        print(f"\n\n{'=' * 80}")
        print("  RECOMMENDATIONS TO BEAT CLAUDE")
        print(f"{'=' * 80}")

        # Aggregate all pipeline failures across scenarios
        all_pipe_failures = {}
        for name, r in results.items():
            pipe_checks = r.get("pipeline", {}).get("score", {}).get("checks", {})
            for check, passed in pipe_checks.items():
                if not passed:
                    all_pipe_failures.setdefault(check, []).append(name)

        if all_pipe_failures:
            sorted_failures = sorted(all_pipe_failures.items(), key=lambda x: -len(x[1]))
            print(f"\n  Most common pipeline failures (fix these first):\n")
            for check, scenarios_list in sorted_failures:
                print(f"    [{len(scenarios_list)}/10] {check}")
                print(f"           Scenarios: {', '.join(scenarios_list)}")
        else:
            print("\n  Pipeline passes all checks across all scenarios!")

    # ═══════════════════════════════════════════════════════════════════════
    # SAVE RESULTS
    # ═══════════════════════════════════════════════════════════════════════

    # Save full results (without draft text to keep file manageable)
    save_data = {}
    for name, r in results.items():
        save_entry = {"scenario": name, "query": r.get("query", "")}
        if "pipeline" in r:
            p = dict(r["pipeline"])
            p.pop("draft_text", None)
            save_entry["pipeline"] = p
        if "claude" in r:
            c = dict(r["claude"])
            c.pop("draft_text", None)
            save_entry["claude"] = c
        if "comparison" in r:
            save_entry["comparison"] = r["comparison"]
        save_data[name] = save_entry

    out_path = OUTPUT_DIR / f"10scenario_compare_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Results saved → {out_path}")

    # Save individual draft texts for review
    for name, r in results.items():
        if "pipeline" in r and "draft_text" in r["pipeline"]:
            draft_path = OUTPUT_DIR / f"10sc_{name}_pipeline_{ts}.txt"
            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(r["pipeline"]["draft_text"])

        if "claude" in r and "draft_text" in r["claude"]:
            draft_path = OUTPUT_DIR / f"10sc_{name}_claude_{ts}.txt"
            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(r["claude"]["draft_text"])

    print(f"  Draft texts saved → {OUTPUT_DIR}/10sc_*_{ts}.txt")
    print(f"\n  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
