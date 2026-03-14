"""
Score benchmark drafts: Pipeline vs Claude Code.
Reads bench_*_pipeline_*.txt and bench_*_claude.txt from output/ and scores them.

Usage: python research/score_benchmark.py
"""
from __future__ import annotations
import re, sys, json
from pathlib import Path
from datetime import datetime

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
        "expected_acts": ["Specific Relief Act", "Section 38"],
        "expected_sections": ["PLAINTIFF", "PRAYER", "VERIFICATION"],
    },
    "dealership": {
        "expected_acts": ["Indian Contract Act", "Section 73"],
        "expected_sections": ["AGREEMENT", "DAMAGES", "PRAYER"],
    },
    "specific_performance": {
        "expected_acts": ["Specific Relief Act", "Section 10"],
        "expected_sections": ["READINESS", "SCHEDULE OF PROPERTY", "PRAYER"],
    },
}


def score_draft(text: str, scenario: dict) -> dict:
    t = " ".join(text.lower().split())
    def has(p): return bool(re.search(p, t))

    checks = {}
    # STRUCTURE (8)
    checks["S1: Court heading"] = has(r"in the court of|before the")
    checks["S2: Parties"] = has(r"plaintiff|petitioner") and has(r"defendant|respondent")
    checks["S3: Facts section"] = has(r"facts|brief facts|statement of facts")
    checks["S4: Cause of action"] = has(r"cause of action")
    checks["S5: Prayer section"] = has(r"prayer|relief|wherefore")
    checks["S6: Verification"] = has(r"verif")
    checks["S7: Advocate block"] = has(r"advocate|counsel|place|through")
    checks["S8: Para numbering (5+)"] = len(re.findall(r"(?:^|\n)\s*\d+\.\s", text)) >= 5

    # LEGAL SUBSTANCE (7)
    checks["L1: Expected acts cited"] = any(has(re.escape(a.lower())) for a in scenario.get("expected_acts", []))
    checks["L2: Jurisdiction pleaded"] = has(r"jurisdict|territorial|pecuniary|section\s+(?:9|15|16|19|20)")
    checks["L3: Limitation addressed"] = has(r"limitation|article\s+\d+|within\s+(?:the\s+)?(?:period|time)")
    checks["L4: Valuation stated"] = has(r"valuat|suit\s+is\s+valued|purposes?\s+of")
    checks["L5: Court fee mentioned"] = has(r"court\s+fee")
    checks["L6: No fabricated case law"] = not has(r"\d{4}\s+scc\s+\d+") and not has(r"air\s+\d{4}\s+sc")
    checks["L7: Relief specificity (3+ prayers)"] = (
        len(re.findall(r"\([a-z]\)", t)) >= 3
        or len(re.findall(r"(?:^|\n)\s*(?:[ivx]+\.|[a-z]\)|\d+\.\s*(?:that|a\s+decree|direct))", text, re.I)) >= 3
    )

    # QUALITY (10)
    checks["Q1: Narrative facts (12+ sentences)"] = len(re.findall(r"\.\s+", t)) >= 12
    checks["Q2: Facts-law separation"] = True
    fm = re.search(r"facts?\s+of\s+the\s+case\s+(.*?)(?:legal|cause\s+of|ground|jurisdiction)", t, re.DOTALL)
    if fm:
        checks["Q2: Facts-law separation"] = not bool(re.search(r"section\s+\d+\s+of\s+the", fm.group(1)))
    checks["Q3: No drafting-notes lang"] = not has(r"to\s+be\s+verif(?:ied|y)") and not has(r"\btbd\b")
    checks["Q4: Interest basis stated"] = has(r"interest") and (has(r"\d+\s*%|per\s+(?:cent|annum)") or has(r"section\s+34|commercial\s+rate"))
    checks["Q5: Placeholders for unknowns"] = has(r"\{\{") or not has(r"mr\.\s+xyz|john\s+doe")
    checks["Q6: Proper legal terminology"] = has(r"plaint|decree|suit|cause of action|prayer")
    checks["Q7: No and/or"] = not has(r"\band/or\b")
    checks["Q8: Document references"] = has(r"annexure|exhibit|document")
    checks["Q9: Adequate length (>2000)"] = len(text) > 2000
    checks["Q10: Key sections present"] = sum(
        1 for s in scenario.get("expected_sections", []) if has(re.escape(s.lower()))
    ) >= len(scenario.get("expected_sections", [])) * 0.5

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {"checks": checks, "passed": passed, "total": total, "score": round(passed / total * 10, 1)}


def find_latest_file(pattern: str) -> Path | None:
    matches = sorted(OUTPUT_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def main():
    print("=" * 80)
    print("  BENCHMARK SCORING: PIPELINE vs CLAUDE CODE (Opus 4.6)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    results = {}
    for name, scenario in SCENARIOS.items():
        pipe_file = find_latest_file(f"bench_{name}_pipeline_*.txt")
        claude_file = find_latest_file(f"bench_{name}_claude.txt")

        pipe_text = pipe_file.read_text(encoding="utf-8") if pipe_file else ""
        claude_text = claude_file.read_text(encoding="utf-8") if claude_file else ""

        pipe_score = score_draft(pipe_text, scenario) if pipe_text else None
        claude_score = score_draft(claude_text, scenario) if claude_text else None

        results[name] = {
            "pipeline": pipe_score,
            "claude": claude_score,
            "pipe_chars": len(pipe_text),
            "claude_chars": len(claude_text),
        }

    # Print summary table
    print(f"\n  {'SCENARIO':<25} {'PIPELINE':>10} {'CLAUDE':>10} {'DIFF':>8} {'WINNER':>10}")
    print(f"  {'─' * 25} {'─' * 10} {'─' * 10} {'─' * 8} {'─' * 10}")

    pipe_total = 0; claude_total = 0; n = 0
    pipe_wins = 0; claude_wins = 0; ties = 0

    for name, r in results.items():
        ps = r["pipeline"]["score"] if r["pipeline"] else "N/A"
        cs = r["claude"]["score"] if r["claude"] else "N/A"
        if isinstance(ps, (int, float)) and isinstance(cs, (int, float)):
            diff = ps - cs
            winner = "PIPELINE" if diff > 0 else "CLAUDE" if diff < 0 else "TIE"
            pipe_total += ps; claude_total += cs; n += 1
            if winner == "PIPELINE": pipe_wins += 1
            elif winner == "CLAUDE": claude_wins += 1
            else: ties += 1
            print(f"  {name:<25} {ps:>10.1f} {cs:>10.1f} {diff:>+8.1f} {winner:>10}")
        else:
            print(f"  {name:<25} {str(ps):>10} {str(cs):>10} {'':>8} {'MISSING':>10}")

    if n:
        print(f"\n  {'AVERAGE':<25} {pipe_total/n:>10.1f} {claude_total/n:>10.1f} {(pipe_total-claude_total)/n:>+8.1f}")
        print(f"\n  Pipeline wins: {pipe_wins} | Claude wins: {claude_wins} | Ties: {ties}")

    # Gap analysis
    print(f"\n\n{'=' * 80}")
    print("  DETAILED GAP ANALYSIS")
    print(f"{'=' * 80}")

    all_pipe_failures = {}
    all_claude_failures = {}
    gaps_pipe_loses = {}  # checks where pipeline fails but claude passes

    for name, r in results.items():
        if not r["pipeline"] or not r["claude"]:
            continue
        pc = r["pipeline"]["checks"]
        cc = r["claude"]["checks"]
        for check in pc:
            if not pc[check]:
                all_pipe_failures.setdefault(check, []).append(name)
            if not cc.get(check, True):
                all_claude_failures.setdefault(check, []).append(name)
            if not pc[check] and cc.get(check, False):
                gaps_pipe_loses.setdefault(check, []).append(name)

    if gaps_pipe_loses:
        print(f"\n  WHERE PIPELINE LOSES TO CLAUDE (pipeline fails, Claude passes):\n")
        for check, scens in sorted(gaps_pipe_loses.items(), key=lambda x: -len(x[1])):
            print(f"    [{len(scens)}/5] {check}")
            print(f"           in: {', '.join(scens)}")

    if all_pipe_failures:
        print(f"\n  ALL PIPELINE FAILURES:\n")
        for check, scens in sorted(all_pipe_failures.items(), key=lambda x: -len(x[1])):
            print(f"    [{len(scens)}/5] {check}")
            print(f"           in: {', '.join(scens)}")

    if all_claude_failures:
        print(f"\n  ALL CLAUDE FAILURES:\n")
        for check, scens in sorted(all_claude_failures.items(), key=lambda x: -len(x[1])):
            print(f"    [{len(scens)}/5] {check}")
            print(f"           in: {', '.join(scens)}")

    # Recommendations
    print(f"\n\n{'=' * 80}")
    print("  RECOMMENDATIONS TO BEAT CLAUDE 4.6")
    print(f"{'=' * 80}")

    if gaps_pipe_loses:
        print("\n  Priority fixes (pipeline loses to Claude here):\n")
        for check, scens in sorted(gaps_pipe_loses.items(), key=lambda x: -len(x[1])):
            cat = check.split(":")[0]
            detail = check.split(":")[1].strip() if ":" in check else check
            if cat.startswith("S"):
                fix = "Fix in postprocess.py or draft prompt"
            elif cat.startswith("L"):
                fix = "Fix in civil.py LKB or enrichment node"
            else:
                fix = "Fix in draft prompt or review node"
            print(f"    {check}")
            print(f"      -> {fix}")
            print(f"      -> Affects: {', '.join(scens)}")
    else:
        print("\n  Pipeline matches or beats Claude on all checks!")

    # Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = OUTPUT_DIR / f"benchmark_scores_{ts}.json"
    save_data = {}
    for name, r in results.items():
        save_data[name] = {
            "pipeline_score": r["pipeline"]["score"] if r["pipeline"] else None,
            "claude_score": r["claude"]["score"] if r["claude"] else None,
            "pipeline_chars": r["pipe_chars"],
            "claude_chars": r["claude_chars"],
            "pipeline_checks": r["pipeline"]["checks"] if r["pipeline"] else {},
            "claude_checks": r["claude"]["checks"] if r["claude"] else {},
        }
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2)
    print(f"\n  Scores saved -> {save_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
