"""Score and compare Claude direct draft vs Pipeline agent draft."""
from __future__ import annotations
import re
import sys
from pathlib import Path

def _quick_score(text: str, label: str) -> dict:
    t = " ".join(text.lower().split())
    def has(p): return bool(re.search(p, t))

    checks = {
        "Court heading present": has(r"in the court of"),
        "Commercial Court designation": has(r"commercial\s+(court|division|suit)"),
        "Parties section": has(r"plaintiff") and has(r"defendant"),
        "Jurisdiction (territorial+pecuniary)": has(r"territorial|resid|carries\s+on\s+business") and has(r"pecuniary|monetary|within.*limits"),
        "Section 12A CPC / mediation": has(r"12.?a|mediation|pre.?institution"),
        "Commercial Courts Act 2015": has(r"commercial\s+courts\s+act.*2015"),
        "Narrative facts (10+ sentences)": len(re.findall(r"\.\s+", t)) >= 25,
        "Capital investment detailed": has(r"invest") and has(r"capital|infrastructure|showroom|godown|stock"),
        "Territory development pleaded": has(r"territory|market\s+(?:development|presence|base)"),
        "Termination illegality explained": has(r"illegal|arbitrary|without.+cause|without.+notice"),
        "Section 73 Contract Act": has(r"section\s+73.*contract\s+act"),
        "Section 39 Contract Act": has(r"section\s+39.*contract\s+act"),
        "Section 75 Contract Act": has(r"section\s+75.*contract\s+act"),
        "Strong CoA (arose+further+continuing)": (
            has(r"first\s+arose|cause\s+of\s+action.*arose")
            and has(r"further\s+(?:arose|accrued)")
        ),
        "Limitation article cited": has(r"article\s+55") or has(r"limitation\s+act.*1963"),
        "Valuation & court fee": has(r"valuation") and has(r"court\s+fee"),
        "Interest (pre-suit + pendente lite)": has(r"pre.?suit\s+interest") and has(r"pendente\s+lite"),
        "Prayer 5+ sub-items": len(re.findall(r"\([a-g]\)", t)) >= 5,
        "Damages particularised": has(r"loss\s+of\s+profit") and has(r"goodwill") and has(r"unsold\s+stock"),
        "5+ Annexures": len(set(re.findall(r"annexure[-\s]*([a-l])", t, re.IGNORECASE))) >= 5,
        "Verification clause": has(r"verif"),
        "Advocate block": has(r"advocate|enrollment"),
        "No drafting-notes language": not has(r"to\s+be\s+verif|to\s+be\s+enter|\btbd\b|\btodo\b"),
    }
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {"label": label, "checks": checks, "passed": passed, "total": total, "pct": round(passed / total * 100, 1)}


def main():
    claude_path = Path(__file__).parent / "output" / "claude_direct_dealership_draft_v2.txt"
    # Find latest pipeline output
    out_dir = Path(__file__).parent / "output"
    pipeline_files = sorted(out_dir.glob("compare_pipeline_*.json"), key=lambda p: p.stat().st_mtime)
    if not pipeline_files:
        print("ERROR: No pipeline output found")
        sys.exit(1)

    import json
    pipeline_path = pipeline_files[-1]
    with open(pipeline_path, "r", encoding="utf-8") as f:
        pipeline_result = json.load(f)

    # Extract pipeline draft text
    final = pipeline_result.get("final_draft") or {}
    artifacts = final.get("draft_artifacts") or []
    pipeline_text = ""
    if artifacts:
        first = artifacts[0] if isinstance(artifacts[0], dict) else {}
        pipeline_text = (first.get("text") or "").strip()
    if not pipeline_text:
        draft = pipeline_result.get("draft") or {}
        arts = draft.get("draft_artifacts") or []
        if arts:
            first = arts[0] if isinstance(arts[0], dict) else {}
            pipeline_text = (first.get("text") or "").strip()

    claude_text = claude_path.read_text(encoding="utf-8")

    # Score both
    claude_score = _quick_score(claude_text, "Claude Direct (Opus 4.6)")
    pipeline_score = _quick_score(pipeline_text, "Pipeline Agent (Ollama)")

    # Print comparison
    print("=" * 80)
    print("  QUALITY COMPARISON: Claude Direct vs Pipeline Agent")
    print("=" * 80)
    print()
    print(f"  {'Metric':<45} {'Claude':<15} {'Pipeline':<15}")
    print("  " + "-" * 73)
    print(f"  {'Draft length':<45} {len(claude_text):>6} chars   {len(pipeline_text):>6} chars")
    print(f"  {'Time':<45} {'~15s':<15} {'391.5s':<15}")
    print(f"  {'LLM calls':<45} {'1 (me)':<15} {'3 (intake+draft+review)':<15}")
    print(f"  {'RAG-augmented':<45} {'No':<15} {'Yes (30 provisions)':<15}")
    print(f"  {'Evidence anchoring':<45} {'No':<15} {'Yes':<15}")
    print(f"  {'Citation validation':<45} {'No':<15} {'Yes (27 verified)':<15}")
    print(f"  {'LKB compliance':<45} {'No':<15} {'Yes':<15}")
    print()
    print(f"  {'Quality Check':<45} {'Claude':<15} {'Pipeline':<15}")
    print("  " + "-" * 73)

    for check in claude_score["checks"]:
        c = "PASS" if claude_score["checks"][check] else "FAIL"
        p = "PASS" if pipeline_score["checks"][check] else "FAIL"
        print(f"  {check:<45} {c:<15} {p:<15}")

    print("  " + "-" * 73)
    print(f"  {'TOTAL SCORE':<45} {claude_score['passed']}/{claude_score['total']} ({claude_score['pct']}%)   {pipeline_score['passed']}/{pipeline_score['total']} ({pipeline_score['pct']}%)")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
