from __future__ import annotations
import asyncio
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import streamlit as st

from app.agents.drafting_agents.drafting_graph import get_drafting_graph


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    return {}


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(coro)).result()


def _drafting_graph_version() -> str:
    root = Path(__file__).resolve().parents[1] / "app" / "agents" / "drafting_agents"
    parts: list[str] = []
    for path in sorted(root.rglob("*.py")):
        try:
            parts.append(f"{path.as_posix()}:{path.stat().st_mtime_ns}")
        except OSError:
            continue
    joined = "|".join(parts).encode("utf-8")
    return hashlib.sha1(joined).hexdigest()[:16]


@st.cache_resource
def _load_graph(version: str):
    _ = version
    return get_drafting_graph()


def _extract_full_draft(result: dict[str, Any]) -> tuple[str, str, str, list[dict[str, Any]]]:
    final_block = _as_dict(result.get("final_draft"))
    final_artifacts = final_block.get("draft_artifacts") or []
    if final_artifacts and isinstance(final_artifacts, list):
        first = _as_dict(final_artifacts[0])
        title = str(first.get("title") or "Final Draft").strip()
        text = str(first.get("text") or "").strip()
        placeholders = first.get("placeholders_used") or []
        if text:
            return title, text, "final_draft", placeholders

    review_block = _as_dict(result.get("review"))
    review_data = _as_dict(review_block.get("review"))
    reviewed_artifacts = review_data.get("final_artifacts") or []
    if reviewed_artifacts and isinstance(reviewed_artifacts, list):
        first = _as_dict(reviewed_artifacts[0])
        title = str(first.get("title") or "Final Draft").strip()
        text = str(first.get("text") or "").strip()
        placeholders = first.get("placeholders_used") or []
        if text:
            return title, text, "review.final_artifacts", placeholders

    draft_block = _as_dict(result.get("draft"))
    artifacts = draft_block.get("draft_artifacts") or []
    if artifacts and isinstance(artifacts, list):
        first = _as_dict(artifacts[0])
        title = str(first.get("title") or "Final Draft").strip()
        text = str(first.get("text") or "").strip()
        placeholders = first.get("placeholders_used") or []
        if text:
            return title, text, "draft", placeholders

    return "Final Draft", "Unable to generate a draft from the current response.", "none", []


# ---------------------------------------------------------------------------
# v7.0 Analysis Functions
# ---------------------------------------------------------------------------

def _run_complexity_scoring(query: str) -> dict:
    from app.agents.drafting_agents.routing.complexity import compute_complexity
    from app.agents.drafting_agents.routing.model_router import route_model
    score, tier = compute_complexity(query)
    route = route_model(tier)
    return {
        "score": score,
        "tier": tier,
        "model": route.model,
        "temperature": route.temperature,
        "source": route.source,
    }


def _run_v7_gates(draft_text: str, query: str, result: dict) -> dict:
    from app.agents.drafting_agents.gates.theory_anchoring import (
        legal_theory_anchoring_gate,
    )
    from app.agents.drafting_agents.gates.procedural_prerequisites import (
        procedural_prerequisites_gate,
    )
    from app.agents.drafting_agents.lkb import lookup

    classify = _as_dict(result.get("classify"))
    cause_type = classify.get("cause_type", "")
    doc_type = classify.get("doc_type", "")
    law_domain = classify.get("law_domain", "Civil")

    lkb_entry = lookup(law_domain, cause_type) if cause_type else None

    enrichment = _as_dict(result.get("mandatory_provisions"))
    verified = enrichment.get("verified_provisions", [])

    theory = legal_theory_anchoring_gate(
        draft=draft_text,
        lkb_entry=lkb_entry,
        verified_provisions=verified,
        user_request=query,
    )

    prereq = procedural_prerequisites_gate(
        draft=draft_text,
        doc_type=doc_type,
        intake_text=str(_as_dict(result.get("intake"))),
        user_request=query,
    )

    return {
        "theory": {
            "passed": theory.passed,
            "found": theory.theories_found,
            "anchored": theory.theories_anchored,
            "unanchored": theory.theories_unanchored,
            "flags": theory.flags,
        },
        "prereq": {
            "passed": prereq.passed,
            "checks": [
                {
                    "id": c.id,
                    "description": c.description,
                    "in_intake": c.found_in_intake,
                    "in_draft": c.found_in_draft,
                    "placeholder": c.placeholder_inserted,
                }
                for c in prereq.checks
            ],
            "flags": prereq.flags,
        },
    }


def _score_accuracy(text: str) -> dict:
    t = " ".join(text.lower().split())

    def has(p):
        return bool(re.search(p, t))

    checks = {
        "Court heading": has(r"(?:commercial|district)\s+(?:court|division|judge)"),
        "Parties (plaintiff + defendant)": has(r"plaintiff") and has(r"defendant"),
        "Jurisdiction section": has(r"jurisdiction"),
        "Facts section": has(r"facts\s+of\s+the\s+case|facts\s+in\s+brief"),
        "Legal basis / grounds": has(r"legal\s+basis|legal\s+grounds|grounds\s+for"),
        "Cause of action": has(r"cause\s+of\s+action"),
        "Prayer / relief": has(r"prayer|relief\s+sought"),
        "Verification clause": has(r"verif"),
        "Valuation + court fee": has(r"valuat") and has(r"court\s+fee"),
        "Paragraph numbering": len(re.findall(r"(?:^|\n)\s*\d+\.", text)) >= 5,
        "Annexure labels": has(r"annexure"),
        "No fabricated case citations": not has(r"\d{4}\s+scc\s+\d+") and not has(r"air\s+\d{4}"),
        "Interest claimed": has(r"interest"),
        "Costs claimed": has(r"cost"),
        "No and/or usage": not has(r"\band/or\b"),
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "score": round(passed / total * 10, 1),
    }


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

def _generate_draft(query: str, max_attempts: int = 1):
    last_title = "Final Draft"
    last_text = "Unable to generate a draft from the current response."
    last_source = "none"
    last_placeholders: list[dict[str, Any]] = []
    last_result: dict[str, Any] = {}

    graph_version = _drafting_graph_version()
    t0 = time.perf_counter()
    for attempt in range(1, max_attempts + 1):
        graph = _load_graph(graph_version)
        result = _run_async(graph.ainvoke({"user_request": query}))
        result = _as_dict(result)
        title, draft_text, source, placeholders = _extract_full_draft(result)

        last_title = title
        last_text = draft_text
        last_source = source
        last_placeholders = placeholders
        last_result = result

        if source == "final_draft":
            elapsed = time.perf_counter() - t0
            result["_ui_meta"] = {"attempts": attempt, "source": source, "elapsed_s": round(elapsed, 1)}
            return title, draft_text, source, placeholders, result

    elapsed = time.perf_counter() - t0
    last_result["_ui_meta"] = {"attempts": max_attempts, "source": last_source, "elapsed_s": round(elapsed, 1)}
    return last_title, last_text, last_source, last_placeholders, last_result


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Legal Drafting Agent v7.0", layout="wide", page_icon="--")
    st.title("Legal Drafting Agent")
    st.caption("v7.0 Ironclad -- Court-ready Indian legal documents with hallucination protection")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = {}
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""
    if "last_draft" not in st.session_state:
        st.session_state.last_draft = ""
    if "last_analysis" not in st.session_state:
        st.session_state.last_analysis = {}

    # -- Sidebar --
    with st.sidebar:
        st.subheader("Controls")
        if st.button("Reload Graph", use_container_width=True):
            _load_graph.clear()
            st.success("Graph cache cleared.")
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_result = {}
            st.session_state.last_query = ""
            st.session_state.last_draft = ""
            st.session_state.last_analysis = {}
            st.rerun()

        st.divider()
        st.subheader("Quick Scenarios")
        scenarios = {
            "Dealership Termination": (
                "Draft a commercial suit seeking damages for illegal termination of dealership agreement. "
                "Plaintiff invested substantial capital and developed territory market. "
                "Termination was arbitrary and contrary to agreement terms. "
                "Claim compensation for loss of profit, goodwill and unsold stock. "
                "Draft with proper breach of contract pleadings."
            ),
            "Money Recovery (Loan)": (
                "Draft a suit for recovery of Rs.20,00,000/- paid as advance for a business transaction "
                "which failed due to Defendant's default. Plead total failure of consideration under "
                "Section 65 of Indian Contract Act. Claim refund with interest and costs."
            ),
            "Partition Suit": (
                "Draft a partition suit. Joint Hindu family property consisting of agricultural land "
                "and residential house. Three co-owners. Plaintiff's 1/3rd share to be separated. "
                "Include genealogy table and schedule of property."
            ),
            "Defamation": (
                "Draft a civil suit for defamation. Defendant published false and defamatory statements "
                "about Plaintiff on social media causing damage to reputation and business. "
                "Claim damages and permanent injunction."
            ),
            "Injunction": (
                "Draft a suit for permanent injunction restraining Defendant from interfering with "
                "Plaintiff's peaceful possession of property. Include interim relief prayer."
            ),
        }
        for name, scenario_query in scenarios.items():
            if st.button(name, use_container_width=True, key=f"scenario_{name}"):
                st.session_state["_pending_query"] = scenario_query
                st.rerun()

        st.divider()
        show_debug = st.checkbox("Show Raw State", value=False)
        show_v7_analysis = st.checkbox("Show v7.0 Analysis", value=True)

        # -- v7.0 Analysis Panel --
        if show_v7_analysis and st.session_state.last_analysis:
            analysis = st.session_state.last_analysis

            st.divider()
            st.subheader("v7.0 Analysis")

            # Complexity
            cx = analysis.get("complexity", {})
            if cx:
                tier_color = {"SIMPLE": "green", "MEDIUM": "orange", "COMPLEX": "red"}.get(cx["tier"], "gray")
                st.markdown(f"**Complexity:** {cx['score']}/12 :{tier_color}[{cx['tier']}]")
                st.markdown(f"**Model:** `{cx['model']}`")
                st.markdown(f"**Temp:** {cx['temperature']}")

            # Timing
            meta = analysis.get("meta", {})
            if meta:
                st.markdown(f"**Pipeline:** {meta.get('elapsed_s', '?')}s")
                st.markdown(f"**Draft:** {len(st.session_state.last_draft)} chars")

            # Accuracy
            acc = analysis.get("accuracy", {})
            if acc:
                st.divider()
                st.markdown(f"### Score: {acc['score']}/10")
                st.markdown(f"{acc['passed']}/{acc['total']} checks pass")
                for check, passed in acc.get("checks", {}).items():
                    icon = "+" if passed else "x"
                    st.markdown(f"{'  :green' if passed else '  :red'}[{icon} {check}]")

            # Theory Anchoring
            theory = analysis.get("gates", {}).get("theory", {})
            if theory:
                st.divider()
                st.markdown("### Theory Anchoring")
                st.markdown(f"{'  :green[PASS]' if theory['passed'] else '  :red[FAIL]'}")
                if theory["found"]:
                    st.markdown(f"**Found:** {', '.join(theory['found'])}")
                if theory["anchored"]:
                    st.markdown(f"**Anchored:** {', '.join(theory['anchored'])}")
                if theory["unanchored"]:
                    st.markdown(f"**Unanchored:** {', '.join(theory['unanchored'])}")
                for flag in theory.get("flags", []):
                    st.warning(flag, icon="!")

            # Procedural Prerequisites
            prereq = analysis.get("gates", {}).get("prereq", {})
            if prereq and prereq.get("checks"):
                st.divider()
                st.markdown("### Prerequisites")
                for c in prereq["checks"]:
                    confirmed = c["in_intake"] or c["in_draft"]
                    icon = "+" if confirmed else "x"
                    color = "green" if confirmed else "red"
                    st.markdown(f":{color}[{icon} {c['description']}]")

            # Review
            review_info = analysis.get("review", {})
            if review_info:
                st.divider()
                blocking = review_info.get("blocking", [])
                st.markdown(f"### Review ({len(blocking)} issues)")
                if blocking:
                    for b in blocking:
                        if isinstance(b, dict):
                            st.error(f"{b.get('severity','?').upper()}: {b.get('issue','')}")
                        else:
                            st.error(str(b))
                else:
                    st.success("No blocking issues")

    # -- Chat history --
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # -- Input --
    pending = st.session_state.pop("_pending_query", None)
    query = pending or st.chat_input("Describe the legal document you need drafted...")
    if not query:
        return

    st.session_state.messages.append({"role": "user", "content": query})
    st.session_state.last_query = query
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        # Stage 0: Complexity
        with st.spinner("Analyzing complexity..."):
            complexity = _run_complexity_scoring(query)

        tier_label = {"SIMPLE": "Simple", "MEDIUM": "Medium", "COMPLEX": "Complex"}.get(complexity["tier"], "?")
        st.info(f"Complexity: **{complexity['score']}/12** ({tier_label}) | Model: `{complexity['model']}`")

        # Pipeline
        with st.spinner(f"Drafting with {complexity['model']}... This may take 1-3 minutes."):
            try:
                title, draft_text, source, placeholders, result = _generate_draft(query)
                elapsed = result.get("_ui_meta", {}).get("elapsed_s", "?")

                # Show draft
                st.markdown(f"### {title}")
                st.markdown(draft_text)
                st.caption(f"Source: `{source}` | Time: {elapsed}s | {len(draft_text)} chars")

                if source != "final_draft":
                    st.warning("Final reviewed draft not available. Showing fallback.")
                    errors = result.get("errors")
                    if errors:
                        st.error(f"Errors: {errors}")

                if isinstance(placeholders, list) and placeholders:
                    with st.expander(f"Placeholders ({len(placeholders)})"):
                        for ph in placeholders:
                            if isinstance(ph, dict):
                                st.markdown(f"- `{{{{{ph.get('key', '')}}}}}` -- {ph.get('reason', '')}")
                            else:
                                st.markdown(f"- `{ph}`")

                # v7.0 Gates
                with st.spinner("Running v7.0 verification gates..."):
                    gates = _run_v7_gates(draft_text, query, result)
                    accuracy = _score_accuracy(draft_text)

                # Review info
                review_block = _as_dict(result.get("review"))
                review_data = _as_dict(review_block.get("review"))
                blocking = review_data.get("blocking_issues") or []

                # Store analysis
                st.session_state.last_analysis = {
                    "complexity": complexity,
                    "accuracy": accuracy,
                    "gates": gates,
                    "review": {"blocking": blocking},
                    "meta": {"elapsed_s": elapsed},
                }
                st.session_state.last_draft = draft_text
                st.session_state.last_result = result

                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Accuracy", f"{accuracy['score']}/10")
                col2.metric("Theory Gate", "PASS" if gates["theory"]["passed"] else "FAIL")
                col3.metric("Prerequisites", "PASS" if gates["prereq"]["passed"] else "CHECK")
                col4.metric("Time", f"{elapsed}s")

                # Downloads
                dcol1, dcol2 = st.columns(2)
                dcol1.download_button(
                    label="Download Draft (.txt)",
                    data=draft_text,
                    file_name="draft_output.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
                dcol2.download_button(
                    label="Download State (.json)",
                    data=json.dumps(result, ensure_ascii=False, indent=2, default=str),
                    file_name="draft_state.json",
                    mime="application/json",
                    use_container_width=True,
                )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"### {title}\n\n{draft_text}",
                })

            except Exception as exc:
                error_text = f"Error: {type(exc).__name__}: {exc}"
                st.error(error_text)
                st.session_state.messages.append({"role": "assistant", "content": error_text})

    if show_debug and st.session_state.last_result:
        st.divider()
        st.subheader("Raw Graph State")
        st.json(st.session_state.last_result)


if __name__ == "__main__":
    main()
