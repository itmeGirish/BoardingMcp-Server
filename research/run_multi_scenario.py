"""
Multi-scenario draft tester — runs multiple diverse queries through the pipeline
and scores each with scenario-specific checks.

Usage:
    agent_steer/Scripts/python.exe research/run_multi_scenario.py
    agent_steer/Scripts/python.exe research/run_multi_scenario.py --scenario 2
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ── Scenarios ────────────────────────────────────────────────────────────────

SCENARIOS = {
    1: {
        "name": "Business Advance (Section 65) — baseline",
        "query": (
            "Draft a suit for recovery of Rs.20,00,000/- paid as advance for a business transaction "
            "which failed due to Defendant's default. "
            "Plead total failure of consideration under Section 65 of Indian Contract Act. "
            "Claim refund with interest and costs. "
            "Include cause of action paragraph with accrual date, continuing nature of cause of action, "
            "valuation, court fee, and proper verification clause. "
            "Draft suitable for filing before the District Court."
        ),
    },
    2: {
        "name": "Cheque Bounce / Dishonour Recovery",
        "query": (
            "Draft a civil suit for recovery of Rs.10,00,000/- where the Defendant issued a cheque "
            "dated 15.01.2025 for Rs.10,00,000/- drawn on State Bank of India which was dishonoured "
            "on presentation with endorsement 'Insufficient Funds'. "
            "A legal notice under Section 138 of the Negotiable Instruments Act was sent on 01.02.2025 "
            "but the Defendant failed to pay within 15 days. "
            "Plead under Section 138 NI Act and also claim civil recovery with interest at 18% per annum. "
            "Include cause of action, limitation, valuation, court fee and verification clause. "
            "Draft suitable for filing before the District Court."
        ),
    },
    3: {
        "name": "Partnership Dissolution — Account Settlement",
        "query": (
            "Draft a suit for recovery of Rs.35,00,000/- being the Plaintiff's share in a dissolved "
            "partnership firm. The Plaintiff and Defendant were partners in M/s ABC Enterprises "
            "carrying on business of construction materials. "
            "The partnership was dissolved by mutual consent on 01.06.2024. "
            "Upon dissolution, accounts were settled and the Defendant acknowledged owing Rs.35,00,000/- "
            "to the Plaintiff as his share. Despite repeated demands, the Defendant has not paid. "
            "Plead under Sections 48 and 69 of the Indian Partnership Act, 1932 and Section 65 of "
            "the Indian Contract Act, 1872. "
            "Claim interest at 12% per annum from the date of dissolution. "
            "Include cause of action, limitation, valuation and verification. "
            "Draft suitable for filing before the District Court."
        ),
    },
    4: {
        "name": "Loan Recovery — Hand Loan with Promissory Note",
        "query": (
            "Draft a suit for recovery of Rs.5,00,000/- being a hand loan given by the Plaintiff to "
            "the Defendant on 10.03.2024 evidenced by a promissory note executed by the Defendant. "
            "The loan was repayable on demand or within 6 months. The Plaintiff demanded repayment on "
            "15.09.2024 through legal notice dated 20.09.2024 but the Defendant has failed to repay. "
            "Plead under Section 73 of the Indian Contract Act for damages and recovery. "
            "Claim interest at 12% per annum from date of loan. "
            "Include cause of action, limitation, valuation, court fee and verification. "
            "Draft suitable for filing before the Civil Judge Senior Division."
        ),
    },
    5: {
        "name": "Partition of Ancestral Property — 1/3 Share",
        "query": (
            "Draft a suit for partition and separate possession of ancestral property. "
            "Plaintiff entitled to 1/3rd share. Defendant refusing amicable partition. "
            "Include genealogy table and schedule of property. "
            "Seek preliminary decree. "
            "Draft suitable for filing before the District Court."
        ),
    },
}


# ── Generic scoring (applies to ALL scenarios) ──────────────────────────────

def _check_facts_law_separation(t: str) -> bool:
    m = re.search(
        r"facts\s+of\s+the\s+case\s+(.*?)(?:legal\s+basis|cause\s+of\s+action)",
        t, re.DOTALL,
    )
    if not m:
        return True
    facts_text = m.group(1)
    return not bool(re.search(
        r"section\s+\d+\s+of\s+the\s+(?:indian|contract|evidence|limitation|specific|civil|negotiable|partnership)",
        facts_text,
    ))


def score_generic(text: str) -> dict:
    """Checks that apply to ANY money recovery plaint regardless of scenario."""
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {
        # ── Structure (universal) ──
        "[STRUCT] Has prayer section": has(r"prayer"),
        "[STRUCT] Has verification clause": has(r"verif"),
        "[STRUCT] Has valuation and court fee": has(r"valuat") and has(r"court fee"),
        "[STRUCT] Court type / court_name present": has(r"district\s+court|district\s+judge|civil\s+judge|court_name"),
        "[STRUCT] Interest claimed": has(r"interest"),
        "[STRUCT] Costs claimed": has(r"cost"),
        "[STRUCT] Has cause of action section": has(r"cause\s+of\s+action"),
        "[STRUCT] Has limitation section": has(r"limitation"),
        "[STRUCT] Has legal basis section": has(r"legal\s+basis|grounds"),
        "[STRUCT] Has facts section": has(r"facts\s+of\s+the\s+case"),
        # ── Legal quality (universal) ──
        "[LEGAL] CoA: accrual / arose stated": (
            has(r"cause\s+of\s+action.*(?:arose|accru)")
            or has(r"\{\{.*(?:date|accrual).*\}\}")
        ),
        "[LEGAL] CoA: continuing cause stated": has(r"continu"),
        "[LEGAL] Limitation article OR placeholder": (
            has(r"article\s+\d+")
            or has(r"\{\{limitation_article\}\}|\{\{limitation_period\}\}")
            or has(r"limitation\s+act")
        ),
        "[LEGAL] Annexure labels present": has(r"annexure"),
        "[LEGAL] No fabricated case law": (
            not has(r"\d{4}\s+scc\s+\d+") and not has(r"air\s+\d{4}")
        ),
        # ── Quality (universal) ──
        "[QUALITY] Narrative facts (15+ sentences)": len(re.findall(r"\.\s+", t)) >= 15,
        "[QUALITY] Facts-law separation": _check_facts_law_separation(t),
        "[QUALITY] No drafting-notes language": (
            not has(r"to\s+be\s+verif(?:ied|y)")
            and not has(r"\bplaceholder\b(?!\s*})")
            and not has(r"\b(?:tbd|tbc|todo)\b")
        ),
        "[QUALITY] No 'and/or' usage": not has(r"\band/or\b"),
        "[QUALITY] Prayer has 5+ sub-prayers": (
            len(re.findall(r"\([a-g]\)", t)) >= 5
            or len(re.findall(r"(?:^|\n)\s*\([a-g]\)", t)) >= 5
        ),
        "[QUALITY] Jurisdiction specificity": (
            has(r"resid|carries\s+on\s+business|situate")
            and has(r"pecuniary|monetary")
        ),
        "[QUALITY] Defensive pleading present": (
            has(r"no\s+part\s+performance|no\s+forfeiture|no\s+counter.?claim|no\s+set.?off|no\s+adjustment")
            or has(r"without\s+(?:any\s+)?(?:lawful\s+)?(?:authority|justification|right)")
            or (has(r"without\s+prejudice") and has(r"in\s+the\s+alternative"))
            or has(r"without\s+conferring\s+any\s+benefit")
        ),
        "[QUALITY] Interest justification": (
            has(r"commercial|wrongful(?:ly)?\s+retain|bank\s+(?:lending\s+)?rate|depriv|benefit\s+of")
        ),
    }
    return checks


# ── Scenario-specific scoring ────────────────────────────────────────────────

def score_scenario_1(text: str) -> dict:
    """Business Advance — Section 65 specific checks."""
    t = " ".join(text.lower().split())
    has = lambda p: bool(re.search(p, t))
    return {
        "[S1] Claim Rs.20,00,000": has(r"20.00.000|20,00,000|twenty\s+lakh|claim_amount"),
        "[S1] Business transaction / advance": has(r"advance|business\s+transaction"),
        "[S1] Defendant's default / breach": has(r"default|breach|fail"),
        "[S1] Total failure of consideration": has(r"failure\s+of\s+consideration|total\s+failure"),
        "[S1] Section 65 Indian Contract Act": has(r"section\s+65|s\.\s*65"),
        "[S1] Refund/restitution framing": has(r"refund|restit|repay|return"),
        "[S1] Section 73 alternative plea": has(r"section\s+73|s\.\s*73|alternative|without\s+prejudice"),
        "[S1] Legal trigger explained": (
            has(r"section\s+65.*?(?:provides?|states?|mandates?|requires?)")
            or has(r"(?:provides?|states?)\s+that\s+when")
        ),
    }


def score_scenario_2(text: str) -> dict:
    """Cheque Bounce — NI Act specific checks."""
    t = " ".join(text.lower().split())
    has = lambda p: bool(re.search(p, t))
    return {
        "[S2] Claim Rs.10,00,000": has(r"10.00.000|10,00,000|ten\s+lakh|claim_amount"),
        "[S2] Cheque mentioned": has(r"cheque|check"),
        "[S2] Dishonour / insufficient funds": has(r"dishonour|dishonor|insufficient\s+funds|bounced?"),
        "[S2] State Bank of India / bank": has(r"state\s+bank|sbi|bank"),
        "[S2] Section 138 NI Act": has(r"section\s+138|s\.\s*138|negotiable\s+instrument"),
        "[S2] Legal notice mentioned": has(r"legal\s+notice|demand\s+notice"),
        "[S2] 15-day statutory period": has(r"15\s*day|fifteen\s*day"),
        "[S2] Interest at 18%": has(r"18\s*%|18\s+per\s+(?:cent|annum)"),
    }


def score_scenario_3(text: str) -> dict:
    """Partnership Dissolution — specific checks."""
    t = " ".join(text.lower().split())
    has = lambda p: bool(re.search(p, t))
    return {
        "[S3] Claim Rs.35,00,000": has(r"35.00.000|35,00,000|thirty.?five\s+lakh|claim_amount"),
        "[S3] Partnership / firm": has(r"partner(?:ship)?|firm"),
        "[S3] Dissolution": has(r"dissolv|dissolution"),
        "[S3] Account settlement / share": has(r"account|share|settlement"),
        "[S3] M/s ABC Enterprises or firm name": has(r"abc\s+enterprises|firm\s+name|partnership_firm"),
        "[S3] Partnership Act cited": has(r"partnership\s+act|section\s+(?:48|69)"),
        "[S3] Interest at 12%": has(r"12\s*%|12\s+per\s+(?:cent|annum)"),
        "[S3] Construction materials business": has(r"construct(?:ion)?|material|building"),
    }


def score_scenario_4(text: str) -> dict:
    """Loan Recovery — Promissory Note specific checks."""
    t = " ".join(text.lower().split())
    has = lambda p: bool(re.search(p, t))
    return {
        "[S4] Claim Rs.5,00,000": has(r"5.00.000|5,00,000|five\s+lakh|claim_amount"),
        "[S4] Hand loan mentioned": has(r"hand\s+loan|loan"),
        "[S4] Promissory note": has(r"promissory\s+note|pro-?note"),
        "[S4] Repayable on demand / 6 months": has(r"on\s+demand|6\s+month|six\s+month|repayable"),
        "[S4] Section 73 Contract Act": has(r"section\s+73|s\.\s*73"),
        "[S4] Legal notice mentioned": has(r"legal\s+notice|demand\s+notice"),
        "[S4] Interest at 12%": has(r"12\s*%|12\s+per\s+(?:cent|annum)"),
        "[S4] Civil Judge Senior Division": has(r"civil\s+judge|senior\s+division|court_name"),
    }


def score_scenario_5(text: str) -> dict:
    """Partition Suit — specific checks."""
    t = " ".join(text.lower().split())
    has = lambda p: bool(re.search(p, t))
    return {
        "[S5] Partition/separate possession in title or prayer": has(r"partition|separate\s+possession"),
        "[S5] 1/3 share stated": has(r"1/3|one.?third|undivided\s+.*share"),
        "[S5] Ancestral property / joint family": has(r"ancestral|joint\s+family|coparcen|hindu\s+succession"),
        "[S5] Genealogy / family tree": has(r"genealog|family\s+tree|propositus|lineage|pedigree"),
        "[S5] Schedule of property": has(r"schedule\s+of\s+propert|property\s+schedule|survey\s+no|sy\.\s*no"),
        "[S5] Preliminary decree sought": has(r"preliminary\s+decree"),
        "[S5] Refusal of amicable partition": has(r"refus|amicable|demanded?\s+partition|demand\s+for\s+partition"),
        "[S5] NOT money recovery framing": not has(r"suit\s+for\s+recovery\s+of\s+rs"),
        "[S5] NOT Section 65 / failure of consideration": not has(r"section\s+65\s+of\s+the\s+indian\s+contract|failure\s+of\s+consideration"),
        "[S5] Property jurisdiction (Section 16 CPC or situate)": has(r"section\s+16|situate|immovable\s+property.*jurisdiction"),
    }


SCENARIO_SCORERS = {
    1: score_scenario_1,
    2: score_scenario_2,
    3: score_scenario_3,
    4: score_scenario_4,
    5: score_scenario_5,
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _as_dict(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    fn = getattr(val, "model_dump", None)
    return fn() if callable(fn) else {}


def _extract_draft(result: dict):
    final_block = _as_dict(result.get("final_draft"))
    artifacts = final_block.get("draft_artifacts") or []
    if artifacts:
        first = artifacts[0] if isinstance(artifacts[0], dict) else _as_dict(artifacts[0])
        return (first.get("text") or "").strip(), "final_draft", first.get("placeholders_used") or []

    draft_block = _as_dict(result.get("draft"))
    draft_arts = draft_block.get("draft_artifacts") or []
    if draft_arts:
        first = draft_arts[0] if isinstance(draft_arts[0], dict) else _as_dict(draft_arts[0])
        return (first.get("text") or "").strip(), "draft_fallback", first.get("placeholders_used") or []

    return "", "none", []


# ── Main ─────────────────────────────────────────────────────────────────────

async def run_scenario(scenario_id: int):
    scenario = SCENARIOS[scenario_id]
    query = scenario["query"]
    name = scenario["name"]

    print("=" * 70)
    print(f"  SCENARIO {scenario_id}: {name}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\n  Query: {query[:120]}...\n")

    import time as _time
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph

    graph = get_drafting_graph()
    t_start = _time.perf_counter()
    result = _as_dict(await graph.ainvoke({"user_request": query}))
    elapsed = _time.perf_counter() - t_start

    draft_text, source, placeholders = _extract_draft(result)

    # Review info
    review_block = _as_dict(result.get("review"))
    review_data = _as_dict(review_block.get("review"))
    review_pass = review_data.get("review_pass", None)
    blocking = review_data.get("blocking_issues") or []

    print(f"\n  PIPELINE TIME: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
    print(f"  SOURCE: {source.upper()}")
    print(f"  REVIEW: pass={review_pass} | blocking={len(blocking)}")

    # ── Print draft (first 2000 chars) ────────────────────────────────
    print(f"\n{'─' * 70}")
    preview = draft_text[:2000] + ("..." if len(draft_text) > 2000 else "")
    print(preview)
    print(f"{'─' * 70}")

    # ── Generic scoring ───────────────────────────────────────────────
    generic = score_generic(draft_text)
    generic_passed = sum(1 for v in generic.values() if v)
    generic_total = len(generic)

    # ── Scenario-specific scoring ─────────────────────────────────────
    scenario_scorer = SCENARIO_SCORERS.get(scenario_id)
    scenario_checks = scenario_scorer(draft_text) if scenario_scorer else {}
    scenario_passed = sum(1 for v in scenario_checks.values() if v)
    scenario_total = len(scenario_checks)

    all_checks = {**generic, **scenario_checks}
    total_passed = generic_passed + scenario_passed
    total_total = generic_total + scenario_total

    print(f"\n  ACCURACY SCORE — Scenario {scenario_id}")
    print("─" * 70)
    for check, passed in all_checks.items():
        status = "PASS" if passed else "FAIL"
        mark = "✓" if passed else "✗"
        print(f"  [{status}] {mark}  {check}")

    print(f"\n  GENERIC:  {generic_passed}/{generic_total}")
    print(f"  SCENARIO: {scenario_passed}/{scenario_total}")
    print(f"  TOTAL:    {total_passed}/{total_total}  ({round(total_passed / total_total * 100, 1)}%)")

    # ── Save ──────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"scenario_{scenario_id}_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Saved → {out_path}")
    print("=" * 70)

    return {
        "scenario": scenario_id,
        "name": name,
        "time": round(elapsed, 1),
        "generic": f"{generic_passed}/{generic_total}",
        "scenario_score": f"{scenario_passed}/{scenario_total}",
        "total": f"{total_passed}/{total_total}",
        "percent": round(total_passed / total_total * 100, 1),
        "review_skipped": review_pass is None and not blocking,
        "failures": [k for k, v in all_checks.items() if not v],
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, default=0, help="Run specific scenario (1-4), 0=all")
    args = parser.parse_args()

    if args.scenario:
        ids = [args.scenario]
    else:
        ids = sorted(SCENARIOS.keys())

    results = []
    for sid in ids:
        if sid not in SCENARIOS:
            print(f"Unknown scenario {sid}, skipping")
            continue
        r = await run_scenario(sid)
        results.append(r)
        print()

    # ── Summary ───────────────────────────────────────────────────────
    if len(results) > 1:
        print("\n" + "=" * 70)
        print("  MULTI-SCENARIO SUMMARY")
        print("=" * 70)
        for r in results:
            skip = "SKIP-REVIEW" if r["review_skipped"] else "REVIEWED"
            print(f"  S{r['scenario']}: {r['total']} ({r['percent']}%) | {r['time']}s | {skip} | {r['name']}")
            if r["failures"]:
                for f in r["failures"]:
                    print(f"        FAIL: {f}")
        print("=" * 70)

        avg_pct = round(sum(r["percent"] for r in results) / len(results), 1)
        avg_time = round(sum(r["time"] for r in results) / len(results), 1)
        print(f"\n  AVG ACCURACY: {avg_pct}%  |  AVG TIME: {avg_time}s")


if __name__ == "__main__":
    asyncio.run(main())
