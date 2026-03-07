"""
Head-to-head benchmark: glm-5:cloud vs qwen3.5:cloud for REVIEW node.
Same draft → two different review models → compare speed, accuracy, judgment.
"""
from __future__ import annotations

import asyncio
import json
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
    "Draft with proper breach of contract pleading."
)


def _as_dict(val):
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    fn = getattr(val, "model_dump", None)
    return fn() if callable(fn) else {}


async def run_review_with_model(model_name: str, state: dict) -> dict:
    """Run ONLY the review node with a specific model, reusing existing pipeline state."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_ollama import ChatOllama

    from app.config import logger, settings
    from app.agents.drafting_agents.nodes._utils import (
        _as_dict as node_as_dict,
        _as_json,
        build_court_fee_context,
        build_legal_research_context,
        extract_json_from_text,
    )
    from app.agents.drafting_agents.prompts import REVIEW_USER_PROMPT, build_review_system_prompt
    from app.agents.drafting_agents.states import ReviewNode

    print(f"\n  {'='*60}")
    print(f"  REVIEW MODEL: {model_name}")
    print(f"  {'='*60}")

    # Build the review model
    model = ChatOllama(model=model_name, temperature=0.3, reasoning=True)

    classify = node_as_dict(state.get("classify"))
    rag = node_as_dict(state.get("rag"))
    draft = node_as_dict(state.get("draft"))
    court_fee = node_as_dict(state.get("court_fee"))
    legal_research = node_as_dict(state.get("legal_research"))
    user_request = (state.get("user_request") or "").strip()

    drafts = draft.get("draft_artifacts", []) if isinstance(draft.get("draft_artifacts"), list) else []
    all_chunks = rag.get("chunks") or []
    review_rag_limit = max(settings.DRAFTING_REVIEW_RAG_LIMIT, settings.DRAFTING_DRAFT_RAG_LIMIT)
    review_chunks = list(all_chunks[:review_rag_limit])

    court_fee_context = build_court_fee_context(court_fee, settings.DRAFTING_WEBSEARCH_SOURCE_URLS)
    legal_research_context = build_legal_research_context(legal_research, settings.DRAFTING_WEBSEARCH_SOURCE_URLS)

    mandatory_provisions = node_as_dict(state.get("mandatory_provisions"))
    procedural_context = (mandatory_provisions.get("procedural_context") or "").strip()
    if procedural_context:
        if legal_research_context:
            legal_research_context += "\n\nPROCEDURAL REQUIREMENTS:\n" + procedural_context
        else:
            legal_research_context = "PROCEDURAL REQUIREMENTS:\n" + procedural_context

    user_payload = REVIEW_USER_PROMPT.format(
        user_request=user_request,
        doc_type=classify.get("doc_type", ""),
        law_domain=classify.get("law_domain", ""),
        rules=_as_json((rag.get("rules") or [])[:settings.DRAFTING_REVIEW_RAG_LIMIT]),
        rag_chunks=_as_json(review_chunks),
        cited=_as_json(drafts[0].get("citations_used", []) if drafts else []),
        court_fee_context=court_fee_context,
        legal_research_context=legal_research_context,
        drafts=_as_json(drafts),
    )

    inline_fix_enabled = settings.DRAFTING_REVIEW_INLINE_FIX
    system_prompt = build_review_system_prompt(inline_fix=inline_fix_enabled)

    # Measure prompt size
    prompt_chars = len(system_prompt) + len(user_payload)
    print(f"  Prompt size: {prompt_chars:,} chars")
    print(f"  RAG chunks: {len(review_chunks)}")
    print(f"  Draft size: {len(drafts[0].get('text', '')) if drafts else 0:,} chars")

    # Attempt structured output
    structured_llm = model.with_structured_output(ReviewNode)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_payload),
    ]

    t0 = time.perf_counter()
    try:
        response = structured_llm.invoke(messages)
        result = node_as_dict(response)
        elapsed = time.perf_counter() - t0
        success = True
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        print(f"  STRUCTURED OUTPUT FAILED ({elapsed:.1f}s): {exc}")
        # Try raw
        try:
            t1 = time.perf_counter()
            raw_response = model.invoke(messages)
            raw_text = getattr(raw_response, "content", "") or ""
            parsed = extract_json_from_text(raw_text)
            if parsed and "review" not in parsed and "review_pass" in parsed:
                parsed = {"review": parsed}
            result = parsed or {}
            elapsed = time.perf_counter() - t0
            success = bool(parsed)
            print(f"  RAW FALLBACK: {'OK' if success else 'FAILED'} ({time.perf_counter()-t1:.1f}s)")
        except Exception as raw_exc:
            elapsed = time.perf_counter() - t0
            result = {}
            success = False
            print(f"  RAW FALLBACK ALSO FAILED: {raw_exc}")

    # Extract review data
    review_data = result.get("review") or result
    blocking = review_data.get("blocking_issues") or []
    non_blocking = review_data.get("non_blocking_issues") or []
    review_pass = review_data.get("review_pass", None)
    final_artifacts = review_data.get("final_artifacts") or []
    has_inline_fix = bool(final_artifacts and any(
        (a.get("text") if isinstance(a, dict) else getattr(a, "text", "")).strip()
        for a in final_artifacts
    ))

    legal_blocking = [i for i in blocking if (i.get("severity") if isinstance(i, dict) else getattr(i, "severity", "")) == "legal"]
    fmt_blocking = [i for i in blocking if (i.get("severity") if isinstance(i, dict) else getattr(i, "severity", "")) == "formatting"]

    print(f"\n  RESULTS:")
    print(f"  Time:              {elapsed:.1f}s")
    print(f"  Success:           {success}")
    print(f"  Review pass:       {review_pass}")
    print(f"  Blocking issues:   {len(blocking)} (legal={len(legal_blocking)}, formatting={len(fmt_blocking)})")
    print(f"  Non-blocking:      {len(non_blocking)}")
    print(f"  Inline fix:        {has_inline_fix}")
    if has_inline_fix:
        fix_text = ""
        for a in final_artifacts:
            t = (a.get("text") if isinstance(a, dict) else getattr(a, "text", "")) or ""
            if t.strip():
                fix_text = t
                break
        print(f"  Inline fix length: {len(fix_text):,} chars")

    if blocking:
        print(f"\n  BLOCKING ISSUES:")
        for i, b in enumerate(blocking, 1):
            if isinstance(b, dict):
                print(f"    [{i}] [{b.get('severity','?')}] {str(b.get('issue',''))[:120]}")
            else:
                sev = getattr(b, "severity", "?")
                iss = getattr(b, "issue", "")
                print(f"    [{i}] [{sev}] {str(iss)[:120]}")

    if non_blocking:
        print(f"\n  NON-BLOCKING ISSUES (first 5):")
        for i, nb in enumerate(non_blocking[:5], 1):
            if isinstance(nb, dict):
                print(f"    [{i}] {str(nb.get('issue',''))[:120]}")
            else:
                print(f"    [{i}] {str(getattr(nb, 'issue', ''))[:120]}")

    return {
        "model": model_name,
        "elapsed": elapsed,
        "success": success,
        "review_pass": review_pass,
        "blocking_count": len(blocking),
        "legal_blocking": len(legal_blocking),
        "fmt_blocking": len(fmt_blocking),
        "non_blocking_count": len(non_blocking),
        "has_inline_fix": has_inline_fix,
        "blocking": [
            {"severity": (b.get("severity") if isinstance(b, dict) else getattr(b, "severity", "")),
             "issue": str(b.get("issue") if isinstance(b, dict) else getattr(b, "issue", ""))[:200]}
            for b in blocking
        ],
    }


def _as_json(obj):
    return json.dumps(obj, ensure_ascii=False, default=str)


async def main():
    from app.agents.drafting_agents.drafting_graph import get_drafting_graph
    from app.config import settings

    print("=" * 70)
    print("  REVIEW MODEL BENCHMARK: glm-5:cloud vs qwen3.5:cloud")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Step 1: Run pipeline up to draft (skip review) to get shared state
    print("\n  Step 1: Running pipeline to generate draft state...")
    # Temporarily skip review
    orig_skip = settings.DRAFTING_SKIP_REVIEW
    settings.DRAFTING_SKIP_REVIEW = True

    graph = get_drafting_graph()
    t0 = time.perf_counter()
    result = await graph.ainvoke({"user_request": QUERY})
    result = _as_dict(result)
    pipeline_time = time.perf_counter() - t0
    print(f"  Pipeline (no review): {pipeline_time:.1f}s")

    # Restore
    settings.DRAFTING_SKIP_REVIEW = orig_skip

    # Check draft exists
    draft = _as_dict(result.get("draft"))
    artifacts = draft.get("draft_artifacts") or []
    if artifacts:
        first = artifacts[0] if isinstance(artifacts[0], dict) else _as_dict(artifacts[0])
        draft_text = (first.get("text") or "").strip()
        print(f"  Draft: {len(draft_text):,} chars")
    else:
        print("  ERROR: No draft generated!")
        return

    # Step 2: Run review with each model
    models = ["glm-5:cloud", "qwen3.5:cloud"]
    results = []

    for model_name in models:
        r = await run_review_with_model(model_name, result)
        results.append(r)

    # Step 3: Comparison table
    print(f"\n\n{'='*70}")
    print("  HEAD-TO-HEAD COMPARISON")
    print(f"{'='*70}")
    print()

    r1 = results[0]
    r2 = results[1]

    rows = [
        ("Model", r1["model"], r2["model"]),
        ("Time", f"{r1['elapsed']:.1f}s", f"{r2['elapsed']:.1f}s"),
        ("Structured output OK", str(r1["success"]), str(r2["success"])),
        ("Review pass", str(r1["review_pass"]), str(r2["review_pass"])),
        ("Blocking issues", str(r1["blocking_count"]), str(r2["blocking_count"])),
        ("  Legal", str(r1["legal_blocking"]), str(r2["legal_blocking"])),
        ("  Formatting", str(r1["fmt_blocking"]), str(r2["fmt_blocking"])),
        ("Non-blocking issues", str(r1["non_blocking_count"]), str(r2["non_blocking_count"])),
        ("Inline fix generated", str(r1["has_inline_fix"]), str(r2["has_inline_fix"])),
    ]

    print(f"  {'Metric':<30} {'glm-5:cloud':<20} {'qwen3.5:cloud':<20}")
    print("  " + "-" * 68)
    for label, v1, v2 in rows:
        print(f"  {label:<30} {v1:<20} {v2:<20}")

    # Save results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = {"pipeline_time": pipeline_time, "draft_chars": len(draft_text), "results": results}
    out_path = OUTPUT_DIR / f"review_benchmark_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Saved → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
