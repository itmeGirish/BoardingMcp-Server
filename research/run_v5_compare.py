"""
v4.0 vs v5.0 comparison — runs same scenario with both pipelines and compares.

Usage: agent_steer/Scripts/python.exe research/run_v5_compare.py [scenario]

Scenarios: money_recovery, partition, injunction, dealership, defamation
Default: partition (the worst-performing scenario on v4.0)

Toggles DRAFTING_V5_FREETEXT_ENABLED at runtime to test both pipelines.
"""
from __future__ import annotations

import asyncio
import json
import os
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

# ── Scenarios ────────────────────────────────────────────────────────────────

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
    "defamation": (
        "Draft a suit for damages for defamation. The Defendant published false and defamatory "
        "statements about the Plaintiff on social media claiming the Plaintiff committed fraud "
        "in business dealings. The statements were shared over 500 times causing severe "
        "reputational damage. Plaintiff is a reputed businessman. "
        "Claim compensatory damages of Rs.10,00,000/- and exemplary damages of Rs.5,00,000/-. "
        "Include plea for mandatory injunction to take down the posts. "
        "Draft for City Civil Court."
    ),
}


def _as_dict(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    fn = getattr(val, "model_dump", None)
    return fn() if callable(fn) else {}


# ── Generic quality scoring (works for any doc_type) ─────────────────────────

def _score_draft(text: str, scenario: str) -> dict:
    """Score draft quality — generic checks that apply to ALL document types."""
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {
        # Structure
        "Court heading present": has(r"in the (?:court|city civil court|district court|high court|commercial court)|court_name"),
        "Title/caption present": has(r"s\s*u\s*i\s*t\s+f\s*o\s*r|suit\s+for|plaint\s+for|application\s+for|petition|partition|damages\s+claim"),
        "Parties section present": has(r"plaintiff|petitioner|applicant"),
        "Facts section present": has(r"facts|statement\s+of\s+facts"),
        "Legal basis present": has(r"legal\s+basis|grounds|law\s+applicable"),
        "Cause of action present": has(r"cause\s+of\s+action"),
        "Prayer present": has(r"prayer|relief|wherefore"),
        "Verification present": has(r"verif"),
        "Continuous paragraph numbering": bool(re.findall(r"(?:^|\n)\s*\d+\.\s", text)),
        "Annexure references": has(r"annexure"),
        # Legal quality
        "No fabricated case law": not has(r"\d{4}\s+scc\s+\d+") and not has(r"air\s+\d{4}"),
        "No and/or": not has(r"\band/or\b"),
        "No drafting-notes language": (
            not has(r"to\s+be\s+verif(?:ied|y)")
            and not has(r"\bplaceholder\b(?!\s*})")
            and not has(r"\b(?:tbd|tbc|todo)\b")
        ),
        "Advocate block present": has(r"advocate|counsel|lawyer"),
        # Substance (scenario-adaptive)
        "Relevant facts present": len(text) > 1000,
        "Multiple paragraphs (narrative)": len(re.findall(r"\.\s+", t)) >= 10,
    }

    # Scenario-specific checks
    if scenario == "partition":
        checks.update({
            "Genealogy/family tree": has(r"genealog|family\s+tree|pedigree|lineage"),
            "Schedule of properties": has(r"schedule|property\s+details|survey\s+no"),
            "Co-owner/coparcener": has(r"co-?owner|coparcener|joint\s+family|hindu\s+undivided"),
            "Share/portion mentioned": has(r"1/3|one.?third|equal\s+share|respective\s+share"),
            "Mesne profits": has(r"mesne\s+profit"),
            "Commissioner prayer": has(r"commission"),
            "No wrong limitation article": not has(r"article\s+(?:65|55|47|113)\s+of\s+the\s+limitation"),
        })
    elif scenario == "money_recovery":
        checks.update({
            "Amount Rs.20L stated": has(r"20.00.000|20,00,000|2000000|twenty\s+lakh"),
            "Section 65 cited": has(r"section\s+65"),
            "Failure of consideration": has(r"failure\s+of\s+consideration"),
            "Interest claimed": has(r"interest"),
            "Limitation article (47/55/113 or placeholder)": (
                has(r"article\s+(?:47|55|113)") or has(r"\{\{limitation")
            ),
        })
    elif scenario == "injunction":
        checks.update({
            "Encroachment mentioned": has(r"encroach"),
            "Title/possession stated": has(r"title|possession"),
            "Mandatory injunction": has(r"mandatory\s+injunction|demolish"),
            "Permanent injunction": has(r"permanent\s+injunction"),
            "Interim/temporary injunction": has(r"interim|temporary|ad\s+interim"),
        })
    elif scenario == "dealership":
        checks.update({
            "Investment amount": has(r"50.00.000|50,00,000|fifty\s+lakh"),
            "Notice period breach": has(r"notice|15\s+day"),
            "Loss of profit": has(r"loss\s+of\s+profit|loss\s+of\s+earning"),
            "Goodwill claimed": has(r"goodwill"),
            "Breach of contract": has(r"breach\s+of\s+contract|breach\s+of\s+agreement"),
            "Commercial Court heading": has(r"commercial\s+court|commercial\s+division"),
            "Section 12A compliance": has(r"section\s+12.?a|pre.?institution\s+mediation"),
            "Statement of Truth": has(r"statement\s+of\s+truth"),
            "Damages schedule": has(r"particulars?\s+of\s+damages|damages?\s+schedule"),
            "Section 73 cited": has(r"section\s+73"),
            "No Section 55 misapplied": not has(r"section\s+55\s+(?:of\s+)?(?:the\s+)?indian\s+contract"),
            "No Section 14 SRA cited": not has(r"section\s+14\s+(?:of\s+)?(?:the\s+)?specific\s+relief"),
        })
    elif scenario == "defamation":
        checks.update({
            "Social media mentioned": has(r"social\s+media|facebook|twitter|instagram"),
            "Reputation damage": has(r"reputat|defam"),
            "Compensatory damages": has(r"compensat"),
            "Exemplary/punitive damages": has(r"exemplary|punitive"),
            "Take down/remove prayer": has(r"take\s+down|remove|delete|injunction"),
        })

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "score": round(passed / total * 10, 1),
    }


def _extract_draft_text(result: dict) -> str:
    """Get draft text from pipeline result."""
    # Try final_draft first
    final = _as_dict(result.get("final_draft"))
    arts = final.get("draft_artifacts") or []
    if arts:
        first = arts[0] if isinstance(arts[0], dict) else _as_dict(arts[0])
        text = (first.get("text") or "").strip()
        if text:
            return text

    # Fallback to draft
    draft = _as_dict(result.get("draft"))
    arts = draft.get("draft_artifacts") or []
    if arts:
        first = arts[0] if isinstance(arts[0], dict) else _as_dict(arts[0])
        return (first.get("text") or "").strip()

    return ""


def _count_placeholders(text: str) -> list:
    """Find all {{PLACEHOLDER}} patterns in text."""
    return re.findall(r"\{\{[A-Z_]+\}\}", text)


# ── Main ─────────────────────────────────────────────────────────────────────

async def run_one(query: str, scenario: str, version: str) -> dict:
    """Run a single pipeline invocation."""
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph

    graph = get_drafting_graph()
    t0 = time.perf_counter()
    result = _as_dict(await graph.ainvoke({"user_request": query}))
    elapsed = time.perf_counter() - t0

    draft_text = _extract_draft_text(result)
    placeholders = _count_placeholders(draft_text)
    score = _score_draft(draft_text, scenario)

    # Review info
    review = _as_dict(_as_dict(result.get("review")).get("review"))
    blocking = review.get("blocking_issues") or []

    # Limitation info
    enrichment = _as_dict(result.get("mandatory_provisions"))
    lim = _as_dict(enrichment.get("limitation"))

    return {
        "version": version,
        "scenario": scenario,
        "elapsed_s": round(elapsed, 1),
        "draft_length": len(draft_text),
        "draft_text": draft_text,
        "score": score,
        "placeholders": placeholders,
        "placeholder_count": len(placeholders),
        "blocking_issues": len(blocking),
        "limitation_article": lim.get("article", "NOT_SET"),
        "limitation_source": lim.get("source", "unknown"),
        "raw_result": result,
    }


async def main():
    scenario_name = sys.argv[1] if len(sys.argv) > 1 else "partition"
    if scenario_name not in SCENARIOS:
        print(f"Unknown scenario: {scenario_name}")
        print(f"Available: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)

    query = SCENARIOS[scenario_name]

    print("=" * 70)
    print(f"  v5.0 PIPELINE TEST — {scenario_name.upper()}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(f"\nQuery: {query[:100]}...\n")

    # ── Run v5.0 ─────────────────────────────────────────────────────────
    print("─" * 70)
    print("  RUNNING v5.0 (free-text)")
    print("─" * 70)
    r = await run_one(query, scenario_name, "v5.0")
    print(f"  Done: {r['elapsed_s']}s | score={r['score']['score']}/10 | "
          f"placeholders={r['placeholder_count']} | blocking={r['blocking_issues']} | "
          f"limitation={r['limitation_article']}")

    # ── Results ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)
    print(f"  Quality score:     {r['score']['score']}/10 ({r['score']['passed']}/{r['score']['total']} checks)")
    print(f"  Time:              {r['elapsed_s']}s")
    print(f"  Draft length:      {r['draft_length']} chars")
    print(f"  Placeholders:      {r['placeholder_count']}")
    print(f"  Blocking issues:   {r['blocking_issues']}")
    print(f"  Limitation:        {r['limitation_article']} (source: {r['limitation_source']})")

    # ── Failed checks ─────────────────────────────────────────────────
    failed = [k for k, v in r["score"]["checks"].items() if not v]
    if failed:
        print(f"\n  FAILED CHECKS:")
        for f in failed:
            print(f"    - {f}")
    else:
        print(f"\n  ALL CHECKS PASSED")

    # ── Save results ──────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"v5_test_{scenario_name}_{ts}.json"
    save_data = {
        "scenario": scenario_name,
        "query": query,
        "timestamp": ts,
        "result": {k: v for k, v in r.items() if k != "raw_result"},
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)

    draft_path = OUTPUT_DIR / f"v5_test_{scenario_name}_{ts}.txt"
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(r["draft_text"])

    print(f"\n  Results saved -> {out_path}")
    print(f"  Draft saved  -> {draft_path}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
