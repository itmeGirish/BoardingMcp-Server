"""v4.0 Dual Scenario Test — Two legal scenarios with detailed scoring.

Scenario A: Specific Performance of Sale Agreement (property)
Scenario B: Breach of Contract + Damages (business services)

Runs both through the v4.0 pipeline and scores each against
scenario-specific checklists (30 checks each).

Run:  pytest tests/drafting/test_v4_dual_scenario.py -v -s
      python tests/drafting/test_v4_dual_scenario.py   (standalone)
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, ".")


# ===========================================================================
# SCENARIO A: Specific Performance of Sale Agreement
# ===========================================================================

SCENARIO_A = (
    "Draft a plaint for specific performance of a sale agreement. "
    "The plaintiff Anita Sharma, aged 52, resident of Indiranagar, Bengaluru, "
    "entered into an Agreement to Sell dated 10.01.2024 with the defendant "
    "Rajesh Reddy, aged 60, resident of HSR Layout, Bengaluru, for purchase of "
    "a residential flat No. 302, 3rd Floor, Sunshine Apartments, Koramangala, "
    "Bengaluru, measuring 1200 sq ft, for a total consideration of Rs.85,00,000/-. "
    "The plaintiff paid an advance of Rs.25,00,000/- via RTGS "
    "(UTR: HDFC20240110987654) on the date of agreement. "
    "The balance of Rs.60,00,000/- was to be paid on or before 10.07.2024 "
    "against execution of the sale deed. The plaintiff was always ready and "
    "willing to perform her part. On 05.06.2024, the defendant sent a letter "
    "refusing to execute the sale deed, claiming he received a higher offer. "
    "The plaintiff issued a legal notice dated 20.06.2024 calling upon the "
    "defendant to execute the sale deed. The defendant refused. "
    "Evidence: Agreement to Sell (original), RTGS receipt, legal notice "
    "with postal receipt, defendant's refusal letter. "
    "File in City Civil Court, Bengaluru."
)

SCENARIO_A_NAME = "Specific Performance of Sale Agreement"


def score_scenario_a(text: str) -> List[Dict[str, str]]:
    """30-point checklist for specific performance plaint."""
    checks = []
    tl = text.lower()

    def add(cat, name, passed, detail=""):
        checks.append({"category": cat, "check": name,
                        "result": "PASS" if passed else "FAIL", "detail": detail})

    # STRUCTURAL (8)
    add("STRUCT", "court_heading",
        "court" in tl and ("civil" in tl or "judge" in tl), "Court name")
    add("STRUCT", "title_plaint",
        "plaint" in tl or "suit" in tl, "Document titled as plaint/suit")
    add("STRUCT", "parties_named",
        "anita" in tl and "rajesh" in tl, "Both parties named")
    add("STRUCT", "party_roles",
        "plaintiff" in tl and "defendant" in tl, "Party roles assigned")
    add("STRUCT", "jurisdiction",
        "jurisdiction" in tl, "Jurisdiction section present")
    add("STRUCT", "facts_section",
        "fact" in tl, "Facts section present")
    add("STRUCT", "prayer_section",
        "prayer" in tl or "wherefore" in tl, "Prayer section")
    add("STRUCT", "verification",
        "verif" in tl, "Verification clause")

    # FACTUAL (8)
    add("FACT", "property_described",
        ("flat" in tl or "apartment" in tl or "302" in text) and ("1200" in text or "sq" in tl),
        "Property described (flat/area)")
    add("FACT", "total_consideration",
        "85,00,000" in text or "85 lakh" in tl or "eighty" in tl,
        "Rs.85L consideration stated")
    add("FACT", "advance_paid",
        "25,00,000" in text or "25 lakh" in tl or "twenty" in tl,
        "Rs.25L advance paid")
    add("FACT", "balance_amount",
        "60,00,000" in text or "60 lakh" in tl or "sixty" in tl or "balance" in tl,
        "Balance Rs.60L mentioned")
    add("FACT", "agreement_date",
        "10.01.2024" in text or "10/01/2024" in text or "january" in tl or "10th" in tl,
        "Agreement date 10.01.2024")
    add("FACT", "refusal_mentioned",
        "refus" in tl or "higher offer" in tl or "declined" in tl,
        "Defendant's refusal narrated")
    add("FACT", "ready_willing",
        "ready and willing" in tl or "ready & willing" in tl or "always ready" in tl,
        "Ready and willing averment")
    add("FACT", "legal_notice",
        "legal notice" in tl or "notice" in tl,
        "Legal notice mentioned")

    # LEGAL (8)
    add("LEGAL", "specific_relief_act",
        "specific relief" in tl or "specific performance" in tl,
        "Specific Relief Act / specific performance cited")
    add("LEGAL", "section_cited",
        bool(re.search(r"section\s+\d+", tl)),
        "At least one statutory section cited")
    add("LEGAL", "cause_of_action",
        "cause of action" in tl,
        "Cause of action section")
    add("LEGAL", "limitation_pleaded",
        "limitation" in tl,
        "Limitation period addressed")
    add("LEGAL", "valuation_court_fee",
        "valuat" in tl or "court fee" in tl,
        "Valuation / court fee section")
    add("LEGAL", "interest_or_mesne",
        "interest" in tl or "mesne" in tl or "damages" in tl,
        "Interest/mesne profits/damages claimed")
    add("LEGAL", "prayer_specific_performance",
        ("specific performance" in tl and ("prayer" in tl or "decree" in tl or "direct" in tl)),
        "Prayer seeks specific performance decree")
    add("LEGAL", "prayer_sale_deed",
        "sale deed" in tl and ("execut" in tl or "direct" in tl),
        "Prayer for execution of sale deed")

    # HALLUCINATION (6)
    add("HALLU", "no_air_citation",
        not bool(re.search(r"\bAIR\s+\d{4}\s+\w+\s+\d+", text)),
        "No fabricated AIR")
    add("HALLU", "no_scc_citation",
        not bool(re.search(r"\bSCC\s+\d{4}\s+\w+\s+\d+", text)),
        "No fabricated SCC")
    add("HALLU", "no_invented_amounts",
        "10,00,000" not in text and "50,00,000" not in text,
        "No invented amounts (10L/50L never in facts)")
    add("HALLU", "no_invented_names",
        "xyz" not in tl and "abc" not in tl and "john" not in tl,
        "No placeholder names")
    add("HALLU", "no_drafting_notes",
        "to be verified" not in tl and "tbd" not in tl and "insert here" not in tl,
        "No drafting-notes language")
    add("HALLU", "placeholders_reasonable",
        text.count("{{") <= 12,
        f"Placeholders: {text.count('{{')}")

    return checks


# ===========================================================================
# SCENARIO B: Breach of Contract + Damages (Business Services)
# ===========================================================================

SCENARIO_B = (
    "Draft a plaint for recovery of damages for breach of contract. "
    "The plaintiff TechSoft Solutions Pvt Ltd, a company registered under the "
    "Companies Act, having its registered office at MG Road, Bengaluru, "
    "represented by its Director Priya Menon, aged 40. "
    "The defendant CloudBridge Systems LLP, a limited liability partnership "
    "having its office at Whitefield, Bengaluru, represented by its "
    "Designated Partner Vikram Singh, aged 48. "
    "On 01.02.2024, the plaintiff entered into a Software Development Agreement "
    "with the defendant for development of an ERP system for a contract value "
    "of Rs.45,00,000/-. The plaintiff paid Rs.20,00,000/- as first milestone "
    "payment via NEFT (UTR: ICIC20240201456789) on 01.02.2024. "
    "The defendant was to deliver the first module by 01.05.2024. "
    "The defendant failed to deliver any module by the deadline and "
    "abandoned the project on 15.06.2024 without returning the advance. "
    "The plaintiff suffered additional loss of Rs.12,00,000/- due to "
    "delay in operations caused by non-delivery. "
    "The plaintiff claims total damages of Rs.32,00,000/- (Rs.20,00,000 refund "
    "+ Rs.12,00,000 consequential damages). Interest at 18% per annum. "
    "Evidence: Software Development Agreement, NEFT receipt, email correspondence "
    "showing abandonment, loss assessment report by auditor. "
    "The plaintiff issued a legal notice dated 01.07.2024. "
    "File in Commercial Court, Bengaluru."
)

SCENARIO_B_NAME = "Breach of Contract — Damages (Business)"


def score_scenario_b(text: str) -> List[Dict[str, str]]:
    """30-point checklist for breach of contract / damages plaint."""
    checks = []
    tl = text.lower()

    def add(cat, name, passed, detail=""):
        checks.append({"category": cat, "check": name,
                        "result": "PASS" if passed else "FAIL", "detail": detail})

    # STRUCTURAL (8)
    add("STRUCT", "court_heading",
        "court" in tl and ("commercial" in tl or "civil" in tl or "judge" in tl),
        "Court name (Commercial/Civil)")
    add("STRUCT", "title_plaint",
        "plaint" in tl or "suit" in tl, "Titled as plaint/suit")
    add("STRUCT", "plaintiff_company",
        "techsoft" in tl or "tech soft" in tl or "plaintiff" in tl,
        "Plaintiff company named")
    add("STRUCT", "defendant_company",
        "cloudbridge" in tl or "cloud bridge" in tl or "defendant" in tl,
        "Defendant company named")
    add("STRUCT", "jurisdiction",
        "jurisdiction" in tl, "Jurisdiction section")
    add("STRUCT", "facts_section",
        "fact" in tl, "Facts section")
    add("STRUCT", "prayer_section",
        "prayer" in tl or "wherefore" in tl, "Prayer section")
    add("STRUCT", "verification",
        "verif" in tl, "Verification clause")

    # FACTUAL (8)
    add("FACT", "contract_value",
        "45,00,000" in text or "45 lakh" in tl or "forty" in tl,
        "Rs.45L contract value")
    add("FACT", "advance_paid",
        "20,00,000" in text or "20 lakh" in tl or "twenty" in tl,
        "Rs.20L advance paid")
    add("FACT", "consequential_damages",
        "12,00,000" in text or "12 lakh" in tl or "consequential" in tl or "loss" in tl,
        "Rs.12L consequential damages / loss")
    add("FACT", "total_claim",
        "32,00,000" in text or "32 lakh" in tl or "total" in tl,
        "Total claim Rs.32L or breakdown stated")
    add("FACT", "software_agreement",
        "software" in tl or "erp" in tl or "agreement" in tl,
        "Software/ERP agreement mentioned")
    add("FACT", "abandonment",
        "abandon" in tl or "failed to deliver" in tl or "non-delivery" in tl,
        "Project abandonment narrated")
    add("FACT", "neft_evidence",
        "neft" in tl or "bank transfer" in tl or "utr" in tl,
        "NEFT/bank transfer evidence")
    add("FACT", "legal_notice",
        "legal notice" in tl or "notice" in tl,
        "Legal notice mentioned")

    # LEGAL (8)
    add("LEGAL", "contract_act",
        "contract act" in tl or "indian contract" in tl or "breach" in tl,
        "Indian Contract Act / breach cited")
    add("LEGAL", "section_cited",
        bool(re.search(r"section\s+\d+", tl)),
        "At least one statutory section")
    add("LEGAL", "cause_of_action",
        "cause of action" in tl,
        "Cause of action section")
    add("LEGAL", "limitation_pleaded",
        "limitation" in tl,
        "Limitation addressed")
    add("LEGAL", "valuation_court_fee",
        "valuat" in tl or "court fee" in tl,
        "Valuation / court fee")
    add("LEGAL", "interest_claimed",
        "interest" in tl and ("18%" in text or "18 per" in tl or "eighteen" in tl),
        "18% interest claimed")
    add("LEGAL", "damages_in_prayer",
        ("damages" in tl or "32,00,000" in text or "decree" in tl) and "prayer" in tl,
        "Prayer seeks damages decree")
    add("LEGAL", "refund_claimed",
        "refund" in tl or "return" in tl or "20,00,000" in text,
        "Refund of advance claimed")

    # HALLUCINATION (6)
    add("HALLU", "no_air_citation",
        not bool(re.search(r"\bAIR\s+\d{4}\s+\w+\s+\d+", text)),
        "No fabricated AIR")
    add("HALLU", "no_scc_citation",
        not bool(re.search(r"\bSCC\s+\d{4}\s+\w+\s+\d+", text)),
        "No fabricated SCC")
    add("HALLU", "no_invented_amounts",
        "50,00,000" not in text and "10,00,000" not in text,
        "No invented amounts")
    add("HALLU", "no_invented_names",
        "xyz" not in tl and "abc" not in tl and "john" not in tl,
        "No placeholder names")
    add("HALLU", "no_drafting_notes",
        "to be verified" not in tl and "tbd" not in tl and "insert here" not in tl,
        "No drafting-notes language")
    add("HALLU", "placeholders_reasonable",
        text.count("{{") <= 12,
        f"Placeholders: {text.count('{{')}")

    return checks


# ===========================================================================
# Pipeline runner + reporting
# ===========================================================================

def _fmt_scorecard(name: str, checks: List[Dict], elapsed: float, text: str, stage_times: Dict) -> str:
    """Format a rich scorecard string."""
    passed = sum(1 for c in checks if c["result"] == "PASS")
    total = len(checks)
    pct = (passed / total * 100) if total else 0

    lines = []
    lines.append("=" * 72)
    lines.append(f"  {name}")
    lines.append("=" * 72)
    lines.append(f"  Speed:        {elapsed:.1f}s total pipeline")
    lines.append(f"  Draft length: {len(text)} chars")
    lines.append(f"  Placeholders: {text.count('{{')}")
    lines.append(f"  Score:        {passed}/{total} ({pct:.0f}%)")
    lines.append("")

    # Stage timing
    lines.append("  STAGE TIMING:")
    for stage, t in stage_times.items():
        lines.append(f"    {stage:.<30s} {t:>6.1f}s")
    lines.append("")

    # Grouped results
    categories = {"STRUCT": "STRUCTURAL", "FACT": "FACTUAL",
                  "LEGAL": "LEGAL", "HALLU": "HALLUCINATION"}
    for prefix, label in categories.items():
        cat_checks = [c for c in checks if c["category"] == prefix]
        cat_pass = sum(1 for c in cat_checks if c["result"] == "PASS")
        lines.append(f"  {label} ({cat_pass}/{len(cat_checks)})")
        for c in cat_checks:
            icon = "+" if c["result"] == "PASS" else "X"
            lines.append(f"    [{icon}] {c['check']}: {c['detail']}")
        lines.append("")

    lines.append("=" * 72)
    return "\n".join(lines), passed, total, pct


async def _run_scenario(graph, scenario: str, name: str, scorer):
    """Run one scenario and return results dict."""
    print(f"\n  Running: {name}")
    print(f"  {'.' * 50}")

    t0 = time.perf_counter()
    result = await graph.ainvoke({"user_request": scenario})
    elapsed = time.perf_counter() - t0

    # Extract draft text
    draft = result.get("final_draft") or result.get("draft")
    if not draft:
        print(f"  ERROR: No draft produced! Errors: {result.get('errors', [])}")
        return None

    artifacts = draft.get("draft_artifacts", []) if isinstance(draft, dict) else []
    if not artifacts:
        d = getattr(draft, "model_dump", lambda: {})()
        artifacts = d.get("draft_artifacts", [])

    if not artifacts:
        print(f"  ERROR: No artifacts!")
        return None

    first = artifacts[0]
    text = first.get("text", "") if isinstance(first, dict) else getattr(first, "text", "")

    # Collect stage timing from logs (approximate from result metadata)
    stage_times = {}
    # Parse what we can from the state
    stage_times["Total"] = elapsed

    # Score
    checks = scorer(text)
    passed = sum(1 for c in checks if c["result"] == "PASS")
    total = len(checks)
    pct = (passed / total * 100) if total else 0

    return {
        "name": name,
        "scenario": scenario,
        "elapsed": elapsed,
        "text": text,
        "text_length": len(text),
        "placeholders": text.count("{{"),
        "checks": checks,
        "passed": passed,
        "total": total,
        "pct": pct,
        "structural_issues": result.get("structural_gate", {}),
        "citation_issues": result.get("citation_issues", []),
        "evidence_issues": result.get("evidence_anchoring_issues", []),
        "errors": result.get("errors", []),
    }


def _print_comparison(results: List[Dict]):
    """Print side-by-side comparison table."""
    print("\n")
    print("=" * 80)
    print("  COMPARISON: v4.0 PIPELINE — TWO SCENARIOS")
    print("=" * 80)
    print("")
    print(f"  {'Metric':<35s} | {'Scenario A':>18s} | {'Scenario B':>18s}")
    print(f"  {'-'*35}-+-{'-'*18}-+-{'-'*18}")

    a, b = results[0], results[1]
    rows = [
        ("Speed (seconds)", f"{a['elapsed']:.1f}s", f"{b['elapsed']:.1f}s"),
        ("Draft length (chars)", str(a['text_length']), str(b['text_length'])),
        ("Placeholders", str(a['placeholders']), str(b['placeholders'])),
        ("TOTAL SCORE", f"{a['passed']}/{a['total']} ({a['pct']:.0f}%)",
                        f"{b['passed']}/{b['total']} ({b['pct']:.0f}%)"),
    ]

    # Category scores
    for prefix, label in [("STRUCT", "Structural"), ("FACT", "Factual"),
                           ("LEGAL", "Legal"), ("HALLU", "Hallucination")]:
        a_cat = [c for c in a["checks"] if c["category"] == prefix]
        b_cat = [c for c in b["checks"] if c["category"] == prefix]
        a_p = sum(1 for c in a_cat if c["result"] == "PASS")
        b_p = sum(1 for c in b_cat if c["result"] == "PASS")
        rows.append((f"  {label}", f"{a_p}/{len(a_cat)}", f"{b_p}/{len(b_cat)}"))

    for label, va, vb in rows:
        print(f"  {label:<35s} | {va:>18s} | {vb:>18s}")

    print("")

    # Failures detail
    for r in results:
        fails = [c for c in r["checks"] if c["result"] == "FAIL"]
        if fails:
            print(f"  FAILURES in {r['name'][:40]}:")
            for f in fails:
                print(f"    [X] {f['check']}: {f['detail']}")
            print("")

    print("=" * 80)


async def main():
    """Run both scenarios and print results."""
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph
    graph = get_drafting_graph()

    print("\n" + "=" * 80)
    print("  v4.0 DUAL SCENARIO TEST")
    print("  Scenario A: Specific Performance of Sale Agreement")
    print("  Scenario B: Breach of Contract — Damages (Business)")
    print("=" * 80)

    total_start = time.perf_counter()

    # Run scenarios sequentially
    result_a = await _run_scenario(graph, SCENARIO_A, SCENARIO_A_NAME, score_scenario_a)
    result_b = await _run_scenario(graph, SCENARIO_B, SCENARIO_B_NAME, score_scenario_b)

    total_elapsed = time.perf_counter() - total_start

    results = []
    for r in [result_a, result_b]:
        if r is None:
            continue
        # Print individual scorecard
        scorecard, passed, total, pct = _fmt_scorecard(
            r["name"], r["checks"], r["elapsed"], r["text"], {"Total": r["elapsed"]},
        )
        print(f"\n{scorecard}")
        results.append(r)

    if len(results) == 2:
        _print_comparison(results)

    # Save output
    output_dir = Path("research/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"v4_dual_{ts}.json"
    try:
        serializable = {
            "timestamp": ts,
            "total_elapsed": round(total_elapsed, 1),
            "scenarios": [],
        }
        for r in results:
            serializable["scenarios"].append({
                "name": r["name"],
                "elapsed": round(r["elapsed"], 1),
                "text_length": r["text_length"],
                "placeholders": r["placeholders"],
                "score": f"{r['passed']}/{r['total']} ({r['pct']:.0f}%)",
                "checks": r["checks"],
                "draft_text": r["text"][:8000],
                "errors": r["errors"],
            })
        output_file.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  Output saved: {output_file}")
    except Exception as e:
        print(f"\n  Could not save: {e}")

    print(f"\n  TOTAL TIME: {total_elapsed:.1f}s for both scenarios")
    return results


# Pytest entry point
import pytest

@pytest.mark.asyncio
async def test_dual_scenario():
    results = await main()
    assert len(results) == 2
    for r in results:
        assert r["pct"] >= 50, f"{r['name']}: {r['pct']:.0f}% < 50%"


if __name__ == "__main__":
    asyncio.run(main())
