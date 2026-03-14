"""Score and compare 7 Pipeline vs Claude 4.6 drafts."""
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_DIR = Path(__file__).parent / "output"

SCENARIOS = {
    "money_recovery": {
        "expected_acts": ["Indian Contract Act", "Section 65"],
        "expected_sections": ["FACTS", "CAUSE OF ACTION", "PRAYER", "VERIFICATION"],
    },
    "partition": {
        "expected_acts": ["Hindu Succession Act", "Code of Civil Procedure"],
        "expected_sections": ["GENEALOGY", "SCHEDULE OF PROPERTY", "PRAYER"],
    },
    "injunction": {
        "expected_acts": ["Specific Relief Act", "Section 38", "Section 39"],
        "expected_sections": ["PLAINTIFF'S RIGHT", "PRAYER", "VERIFICATION"],
    },
    "dealership": {
        "expected_acts": ["Indian Contract Act", "Section 73", "Commercial Courts Act"],
        "expected_sections": ["AGREEMENT DETAILS", "DAMAGES", "PRAYER"],
    },
    "specific_performance": {
        "expected_acts": ["Specific Relief Act", "Section 10", "Section 16"],
        "expected_sections": ["READINESS AND WILLINGNESS", "SCHEDULE OF PROPERTY", "PRAYER"],
    },
    "defamation": {
        "expected_acts": ["Law of Torts", "Defamation"],
        "expected_sections": ["DEFAMATORY STATEMENT", "PUBLICATION", "PRAYER"],
    },
    "recovery_possession": {
        "expected_acts": ["Specific Relief Act", "Section 5", "Code of Civil Procedure"],
        "expected_sections": ["TITLE AND OWNERSHIP", "SCHEDULE OF PROPERTY", "PRAYER"],
    },
}


def score_draft(text: str, scenario: dict) -> dict:
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {}
    checks["S1: Title/cause heading present"] = has(r"in the court of|before the")
    checks["S2: Parties section"] = has(r"plaintiff|petitioner") and has(r"defendant|respondent")
    checks["S3: Facts section present"] = has(r"facts|brief facts|statement of facts")
    checks["S4: Cause of action"] = has(r"cause of action")
    checks["S5: Prayer/relief section"] = has(r"prayer|relief|wherefore")
    checks["S6: Verification clause"] = has(r"verif")
    checks["S7: Advocate block or place/date"] = has(r"advocate|counsel|place|through")
    checks["S8: Continuous para numbering"] = (
        bool(re.findall(r"(?:^|\n)\s*\d+\.\s", text))
        and len(re.findall(r"(?:^|\n)\s*\d+\.\s", text)) >= 5
    )
    checks["L1: Expected act(s) cited"] = any(
        has(re.escape(a.lower())) for a in scenario.get("expected_acts", [])
    )
    checks["L2: Jurisdiction pleaded"] = has(
        r"jurisdict|territorial|pecuniary|section\s+(?:9|15|16|19|20)"
    )
    checks["L3: Limitation addressed"] = has(
        r"limitation|article\s+\d+|within\s+(?:the\s+)?(?:period|time)"
    )
    checks["L4: Valuation stated"] = has(
        r"valuat|suit\s+is\s+valued|purposes?\s+of\s+(?:jurisdiction|court\s+fee)"
    )
    checks["L5: Court fee mentioned"] = has(r"court\s+fee")
    checks["L6: No fabricated case law"] = not has(r"\d{4}\s+scc\s+\d+") and not has(
        r"air\s+\d{4}\s+sc"
    )
    checks["L7: Relief specificity (3+ prayers)"] = (
        len(re.findall(r"\([a-z]\)", t)) >= 3
        or len(
            re.findall(
                r"(?:^|\n)\s*(?:[ivx]+\.|[a-z]\)|\d+\.\s*(?:that|a\s+decree|direct))",
                text,
                re.I,
            )
        )
        >= 3
    )
    checks["Q1: Narrative facts (not skeleton)"] = len(re.findall(r"\.\s+", t)) >= 12
    checks["Q2: Facts-law separation"] = True
    facts_m = re.search(
        r"facts?\s+of\s+the\s+case\s+(.*?)(?:legal|cause\s+of|ground|jurisdiction)",
        t,
        re.DOTALL,
    )
    if facts_m:
        checks["Q2: Facts-law separation"] = not bool(
            re.search(r"section\s+\d+\s+of\s+the", facts_m.group(1))
        )
    checks["Q3: No drafting-notes language"] = (
        not has(r"to\s+be\s+verif(?:ied|y)")
        and not has(r"\bplaceholder\b(?!\s*})")
        and not has(r"\btbd\b")
    )
    checks["Q4: Interest rate/basis stated"] = has(r"interest") and (
        has(r"\d+\s*%|per\s+(?:cent|annum)")
        or has(r"section\s+34\s+cpc|commercial\s+rate")
    )
    checks["Q5: Placeholder for unknowns"] = has(r"\{\{") or not has(
        r"mr\.\s+xyz|john\s+doe|abc\s+company"
    )
    checks["Q6: Proper legal terminology"] = has(r"plaint|decree|suit|cause of action|prayer")
    checks["Q7: No and/or usage"] = not has(r"\band/or\b")
    checks["Q8: Annexure/document references"] = has(r"annexure|exhibit|document")
    checks["Q9: Draft length adequate (>2000 chars)"] = len(text) > 2000
    checks["Q10: Expected key sections present"] = (
        sum(1 for s in scenario.get("expected_sections", []) if has(re.escape(s.lower())))
        >= len(scenario.get("expected_sections", [])) * 0.5
    )

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "score": round(passed / total * 10, 1),
        "percent": round(passed / total * 100, 1),
    }


def main():
    print("=" * 80)
    print("  7-SCENARIO COMPARISON: PIPELINE (v5.1) vs CLAUDE OPUS 4.6")
    print("=" * 80)

    results = {}

    for name, scenario in SCENARIOS.items():
        pipe_path = OUTPUT_DIR / f"pipeline_{name}_latest.txt"
        claude_path = OUTPUT_DIR / f"claude46_{name}.txt"

        pipe_text = pipe_path.read_text(encoding="utf-8").strip() if pipe_path.exists() else ""
        claude_text = claude_path.read_text(encoding="utf-8").strip() if claude_path.exists() else ""

        pipe_score = score_draft(pipe_text, scenario)
        claude_score = score_draft(claude_text, scenario)

        ps = pipe_score["score"]
        cs = claude_score["score"]
        diff = round(ps - cs, 1)
        winner = "PIPELINE" if diff > 0 else "CLAUDE-4.6" if diff < 0 else "TIE"

        results[name] = {
            "pipeline": {"chars": len(pipe_text), "score": ps, "passed": pipe_score["passed"], "total": pipe_score["total"], "checks": pipe_score["checks"]},
            "claude46": {"chars": len(claude_text), "score": cs, "passed": claude_score["passed"], "total": claude_score["total"], "checks": claude_score["checks"]},
            "diff": diff,
            "winner": winner,
        }

    # Print table
    print(f"\n  {'SCENARIO':<25} {'PIPELINE':>10} {'CLAUDE-4.6':>12} {'DIFF':>8} {'WINNER':>12}")
    print(f"  {'─' * 25} {'─' * 10} {'─' * 12} {'─' * 8} {'─' * 12}")

    pipe_total = 0
    claude_total = 0
    pipe_wins = 0
    claude_wins = 0
    ties = 0

    for name, r in results.items():
        ps = r["pipeline"]["score"]
        cs = r["claude46"]["score"]
        diff = r["diff"]
        winner = r["winner"]
        pipe_total += ps
        claude_total += cs
        if winner == "PIPELINE":
            pipe_wins += 1
        elif winner == "CLAUDE-4.6":
            claude_wins += 1
        else:
            ties += 1
        print(f"  {name:<25} {ps:>10.1f} {cs:>12.1f} {diff:>+8.1f} {winner:>12}")

    n = len(results)
    print(f"\n  {'AVERAGE':<25} {pipe_total/n:>10.1f} {claude_total/n:>12.1f} {(pipe_total-claude_total)/n:>+8.1f}")
    print(f"\n  Pipeline wins: {pipe_wins} | Claude-4.6 wins: {claude_wins} | Ties: {ties}")

    # Gap analysis
    print(f"\n\n{'=' * 80}")
    print("  GAP ANALYSIS")
    print(f"{'=' * 80}")

    for name, r in results.items():
        pipe_checks = r["pipeline"]["checks"]
        claude_checks = r["claude46"]["checks"]

        pipe_gaps = [k for k in pipe_checks if not pipe_checks[k] and claude_checks.get(k, False)]
        claude_gaps = [k for k in claude_checks if not claude_checks[k] and pipe_checks.get(k, False)]

        if pipe_gaps or claude_gaps:
            print(f"\n  {name.upper()} (Pipeline {r['pipeline']['score']} vs Claude {r['claude46']['score']}):")
            if pipe_gaps:
                print(f"    Pipeline missing: {', '.join(pipe_gaps)}")
            if claude_gaps:
                print(f"    Claude missing:   {', '.join(claude_gaps)}")

    # Save
    out_path = OUTPUT_DIR / "comparison_pipeline_vs_claude46.json"
    # Remove checks for cleaner JSON
    save_data = {}
    for name, r in results.items():
        save_data[name] = {
            "pipeline": {"chars": r["pipeline"]["chars"], "score": r["pipeline"]["score"], "passed": r["pipeline"]["passed"], "total": r["pipeline"]["total"]},
            "claude46": {"chars": r["claude46"]["chars"], "score": r["claude46"]["score"], "passed": r["claude46"]["passed"], "total": r["claude46"]["total"]},
            "diff": r["diff"],
            "winner": r["winner"],
        }
    with open(out_path, "w") as f:
        json.dump(save_data, f, indent=2)
    print(f"\n\n  Results saved → {out_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
