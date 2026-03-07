"""v4.0 Live Pipeline Test — full end-to-end with real LLM calls.

Runs the complete v4.0 exemplar-guided pipeline with a money recovery
scenario and scores the output against a 22-point accuracy checklist.

Run:  pytest tests/drafting/test_v4_live_pipeline.py -v -s --timeout=600
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

import pytest

sys.path.insert(0, ".")

# ---------------------------------------------------------------------------
# Test Scenario: Rs.15L Hand Loan Recovery (proven benchmark)
# ---------------------------------------------------------------------------

SCENARIO = (
    "Draft a plaint for recovery of Rs.15,00,000 given as a hand loan. "
    "The plaintiff Ram Kumar, aged 45, resident of Jayanagar, Bengaluru, "
    "advanced Rs.15,00,000 to the defendant Suresh Patel, aged 38, resident of "
    "Koramangala, Bengaluru, on 15.03.2024 via NEFT bank transfer "
    "(UTR: AXIB20240315123456). There was no written agreement. "
    "The defendant acknowledged the loan via WhatsApp messages. "
    "Despite repeated oral demands and a legal notice dated 01.07.2024, "
    "the defendant has failed to repay. The plaintiff claims interest at 12% "
    "per annum from the date of default (20.06.2024). "
    "File in City Civil Court, Bengaluru."
)


# ---------------------------------------------------------------------------
# 22-Point Accuracy Checklist
# ---------------------------------------------------------------------------

def _score_draft(text: str, state: Dict[str, Any]) -> List[Dict[str, str]]:
    """Score draft against 22 checks. Returns list of {check, result, detail}."""
    checks: List[Dict[str, str]] = []
    tl = text.lower()

    def add(name: str, passed: bool, detail: str = ""):
        checks.append({"check": name, "result": "PASS" if passed else "FAIL", "detail": detail})

    # --- STRUCTURAL (7) ---
    add("S1_court_heading", "court" in tl and ("civil" in tl or "judge" in tl),
        "Court name present")
    add("S2_title", "plaint" in tl,
        "Document title present")
    add("S3_parties",
        "ram" in tl and "suresh" in tl and ("plaintiff" in tl and "defendant" in tl),
        "Both parties named with roles")
    add("S4_jurisdiction_section", "jurisdiction" in tl,
        "Jurisdiction section present")
    add("S5_facts_section",
        bool(re.search(r"fact", tl)),
        "Facts section present")
    add("S6_prayer_section", "prayer" in tl or "wherefore" in tl,
        "Prayer section present")
    add("S7_verification",
        "verif" in tl and ("order vi" in tl or "order 6" in tl or "cpc" in tl or "true" in tl),
        "Verification clause present")

    # --- FACTUAL ACCURACY (5) ---
    add("F1_amount_correct",
        "15,00,000" in text or "15 lakh" in tl or "1500000" in text or "fifteen lakh" in tl,
        "Rs.15,00,000 principal amount")
    add("F2_hand_loan_stated", "hand loan" in tl or "loan" in tl,
        "Hand loan / loan mentioned")
    add("F3_neft_reference",
        "neft" in tl or "bank transfer" in tl or "utr" in tl,
        "NEFT/bank transfer referenced")
    add("F4_no_written_agreement",
        "no written" in tl or "oral" in tl or "without" in tl,
        "No written agreement disclosed")
    add("F5_whatsapp_evidence",
        "whatsapp" in tl or "message" in tl,
        "WhatsApp evidence mentioned")

    # --- LEGAL ACCURACY (6) ---
    add("L1_cause_of_action",
        "cause of action" in tl,
        "Cause of action section")
    add("L2_limitation_pleaded",
        "limitation" in tl,
        "Limitation section present")
    add("L3_limitation_article",
        bool(re.search(r"article\s+\d+", tl)),
        "Limitation article cited (any)")
    add("L4_interest_claimed",
        "interest" in tl and ("12%" in text or "12 per" in tl or "twelve" in tl),
        "12% interest claim")
    add("L5_valuation_court_fee",
        "valuat" in tl or "court fee" in tl,
        "Valuation/court fee section")
    add("L6_legal_basis",
        bool(re.search(r"section\s+\d+", tl)),
        "At least one statutory section cited")

    # --- HALLUCINATION CHECKS (4) ---
    add("H1_no_fabricated_case_law",
        not bool(re.search(r"\bAIR\s+\d{4}\s+\w+\s+\d+", text)),
        "No fabricated AIR citations")
    add("H2_no_fabricated_scc",
        not bool(re.search(r"\bSCC\s+\d{4}\s+\w+\s+\d+", text)),
        "No fabricated SCC citations")
    add("H3_no_invented_names",
        "xyz" not in tl and "abc" not in tl and "john doe" not in tl,
        "No invented placeholder names")
    add("H4_placeholders_used_correctly",
        text.count("{{") <= 15,
        f"Reasonable placeholder count ({text.count('{{')})")

    return checks


def _print_scorecard(checks: List[Dict[str, str]], elapsed: float, text: str):
    """Print a formatted scorecard."""
    passed = sum(1 for c in checks if c["result"] == "PASS")
    total = len(checks)
    pct = (passed / total * 100) if total else 0

    print("\n" + "=" * 70)
    print(f"  v4.0 PIPELINE SCORECARD — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    print(f"  Speed:    {elapsed:.1f}s total pipeline")
    print(f"  Accuracy: {passed}/{total} ({pct:.0f}%)")
    print(f"  Draft:    {len(text)} chars")
    print(f"  Placeholders: {text.count('{{')}")
    print("-" * 70)

    # Group by category
    categories = {"S": "STRUCTURAL", "F": "FACTUAL", "L": "LEGAL", "H": "HALLUCINATION"}
    for prefix, label in categories.items():
        cat_checks = [c for c in checks if c["check"].startswith(prefix)]
        cat_pass = sum(1 for c in cat_checks if c["result"] == "PASS")
        print(f"\n  {label} ({cat_pass}/{len(cat_checks)})")
        for c in cat_checks:
            icon = "+" if c["result"] == "PASS" else "X"
            print(f"    [{icon}] {c['check']}: {c['detail']}")

    print("\n" + "=" * 70)
    return passed, total, pct


# ---------------------------------------------------------------------------
# Live Test
# ---------------------------------------------------------------------------

@pytest.mark.timeout(600)
class TestV4LivePipeline:
    """Full v4.0 pipeline run with real LLM calls."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from app.agents.drafting_agents.drafting_graph import get_drafting_graph
        self.graph = get_drafting_graph()

    @pytest.mark.asyncio
    async def test_money_recovery_plaint_full_pipeline(self):
        """Run full v4.0 pipeline and score output."""
        print(f"\n{'='*70}")
        print(f"  v4.0 LIVE PIPELINE TEST — Money Recovery Rs.15L")
        print(f"{'='*70}")

        t0 = time.perf_counter()

        state = {"user_request": SCENARIO}
        result = await self.graph.ainvoke(state)

        elapsed = time.perf_counter() - t0

        # Extract draft text
        draft = result.get("final_draft") or result.get("draft")
        assert draft is not None, "No draft produced"

        if isinstance(draft, dict):
            artifacts = draft.get("draft_artifacts", [])
        else:
            artifacts = getattr(draft, "draft_artifacts", [])
            if not artifacts:
                d = getattr(draft, "model_dump", lambda: {})()
                artifacts = d.get("draft_artifacts", [])

        assert len(artifacts) > 0, "No draft artifacts"

        first = artifacts[0]
        text = first.get("text", "") if isinstance(first, dict) else getattr(first, "text", "")
        assert len(text) > 200, f"Draft too short ({len(text)} chars)"

        # Print draft excerpt
        print(f"\n  Draft length: {len(text)} chars")
        print(f"  First 500 chars:\n{'~'*50}")
        print(text[:500])
        print(f"{'~'*50}")

        # Score
        checks = _score_draft(text, result)
        passed, total, pct = _print_scorecard(checks, elapsed, text)

        # Print pipeline metadata
        print(f"\n  PIPELINE METADATA:")
        if result.get("structural_issues"):
            si = result["structural_issues"]
            print(f"    structural_issues: {len(si)} ({sum(1 for i in si if i.get('severity')=='ERROR')} errors)")
        if result.get("citation_issues"):
            ci = result["citation_issues"]
            print(f"    citation_issues: {len(ci)} ({sum(1 for i in ci if i.get('severity')=='ERROR')} errors)")
        if result.get("evidence_anchoring_issues"):
            ei = result["evidence_anchoring_issues"]
            print(f"    evidence_anchoring_issues: {len(ei)}")
        if result.get("review"):
            rv = result["review"]
            if isinstance(rv, dict):
                rv_data = rv.get("review", rv)
            else:
                rv_data = getattr(rv, "review", {})
                if hasattr(rv_data, "model_dump"):
                    rv_data = rv_data.model_dump()
            blocking = rv_data.get("blocking_issues", []) if isinstance(rv_data, dict) else []
            print(f"    review_blocking: {len(blocking)}")
        errors = result.get("errors") or []
        if errors:
            print(f"    errors: {errors}")

        # Save output for analysis
        output_dir = Path("research/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"v4_live_{ts}.json"
        try:
            # Serialize what we can
            serializable = {
                "scenario": SCENARIO,
                "elapsed_seconds": round(elapsed, 1),
                "draft_length": len(text),
                "placeholder_count": text.count("{{"),
                "scorecard": checks,
                "score": f"{passed}/{total} ({pct:.0f}%)",
                "draft_text": text[:5000],
                "structural_issues": result.get("structural_issues", []),
                "citation_issues": result.get("citation_issues", []),
                "evidence_anchoring_issues": result.get("evidence_anchoring_issues", []),
                "errors": errors,
            }
            output_file.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\n  Output saved: {output_file}")
        except Exception as e:
            print(f"\n  Could not save output: {e}")

        # Assertions
        assert pct >= 60, f"Accuracy too low: {pct:.0f}% (need >= 60%)"
        assert elapsed < 400, f"Too slow: {elapsed:.0f}s (limit 400s)"

        print(f"\n  RESULT: {pct:.0f}% accuracy in {elapsed:.1f}s")


# ---------------------------------------------------------------------------
# Standalone runner (no pytest required)
# ---------------------------------------------------------------------------

async def _run_standalone():
    """Run the live test outside pytest for quick iteration."""
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph
    graph = get_drafting_graph()

    print(f"\n{'='*70}")
    print(f"  v4.0 STANDALONE LIVE TEST — Money Recovery Rs.15L")
    print(f"{'='*70}")

    t0 = time.perf_counter()
    result = await graph.ainvoke({"user_request": SCENARIO})
    elapsed = time.perf_counter() - t0

    draft = result.get("final_draft") or result.get("draft")
    if not draft:
        print("  ERROR: No draft produced!")
        print(f"  Errors: {result.get('errors', [])}")
        return

    artifacts = draft.get("draft_artifacts", []) if isinstance(draft, dict) else []
    if not artifacts:
        print("  ERROR: No artifacts!")
        return

    text = artifacts[0].get("text", "") if isinstance(artifacts[0], dict) else ""
    checks = _score_draft(text, result)
    _print_scorecard(checks, elapsed, text)


if __name__ == "__main__":
    asyncio.run(_run_standalone())
