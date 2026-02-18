"""
Legal Drafting Assistant — Simple Chatbot

Usage:
    1. Start the LangGraph server:   langgraph dev
    2. Run this app:                  streamlit run research/drafting_app.py

Just chat. Tell the agent what you need — it drafts the full document.
Drafts are auto-saved to the output/ folder.
"""

import os
import re
from datetime import datetime
import streamlit as st
import requests
import json

# ── Config ───────────────────────────────────────────────────────────
LANGGRAPH_URL = "http://localhost:2024"
GRAPH_NAME = "legal_drafting_agent"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# ── Ensure output folder exists ──────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Page Setup ───────────────────────────────────────────────────────
st.set_page_config(page_title="Legal Drafting Assistant", layout="wide")

# ── Session State ────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "draft_text" not in st.session_state:
    st.session_state["draft_text"] = ""
if "langgraph_url" not in st.session_state:
    st.session_state["langgraph_url"] = LANGGRAPH_URL
if "recommendations" not in st.session_state:
    st.session_state["recommendations"] = []
if "saved_file" not in st.session_state:
    st.session_state["saved_file"] = ""


# ── Output helpers ───────────────────────────────────────────────────
def save_draft_to_output(draft_text: str, doc_type: str = "draft") -> dict:
    """Save draft as TXT and DOCX in the output/ folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_type = re.sub(r"[^\w]", "_", doc_type.lower().strip())[:30]
    base_name = f"{safe_type}_{timestamp}"

    saved = {}

    # Save TXT
    txt_path = os.path.join(OUTPUT_DIR, f"{base_name}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(draft_text)
    saved["txt"] = txt_path

    # Save DOCX
    try:
        from docx import Document
        from docx.shared import Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1.25)
            section.right_margin = Inches(1)

        # Split draft into lines and add to doc
        lines = draft_text.split("\n")
        for line in lines:
            stripped = line.strip()
            if not stripped:
                doc.add_paragraph("")
                continue

            # Detect headings (all caps lines or lines starting with numbers)
            if stripped.isupper() and len(stripped) < 100:
                p = doc.add_heading(stripped, level=1)
            elif re.match(r"^={3,}", stripped) or re.match(r"^-{3,}", stripped):
                continue  # skip separator lines
            else:
                doc.add_paragraph(stripped)

        docx_path = os.path.join(OUTPUT_DIR, f"{base_name}.docx")
        doc.save(docx_path)
        saved["docx"] = docx_path
    except ImportError:
        pass  # python-docx not installed

    return saved


# ── API ──────────────────────────────────────────────────────────────
def _url():
    return st.session_state.get("langgraph_url", LANGGRAPH_URL)


def ensure_thread() -> str:
    if st.session_state["thread_id"]:
        return st.session_state["thread_id"]
    resp = requests.post(
        f"{_url()}/threads", json={},
        headers={"Content-Type": "application/json"}, timeout=10,
    )
    resp.raise_for_status()
    tid = resp.json()["thread_id"]
    st.session_state["thread_id"] = tid
    return tid


def send_message(user_message: str) -> dict:
    try:
        thread_id = ensure_thread()
    except Exception as e:
        return {"error": f"Cannot create thread: {e}"}

    url = f"{_url()}/threads/{thread_id}/runs/wait"
    payload = {
        "assistant_id": GRAPH_NAME,
        "input": {"messages": [{"role": "user", "content": user_message}]},
    }
    try:
        resp = requests.post(
            url, json=payload,
            headers={"Content-Type": "application/json"}, timeout=600,
        )
        if resp.status_code != 200:
            return {"error": f"Server error {resp.status_code}: {resp.text[:300]}"}

        run_state = resp.json()

        # Also fetch the full thread state (has all accumulated fields)
        try:
            state_resp = requests.get(
                f"{_url()}/threads/{thread_id}/state",
                headers={"Content-Type": "application/json"}, timeout=15,
            )
            if state_resp.status_code == 200:
                thread_state = state_resp.json()
                full_state = thread_state.get("values", thread_state)
                return parse_state(full_state)
        except Exception:
            pass

        return parse_state(run_state)
    except requests.ConnectionError:
        return {"error": "Cannot connect. Is `langgraph dev` running?"}
    except requests.Timeout:
        return {"error": "Timed out (600s). Local model may be slow."}
    except Exception as e:
        return {"error": str(e)}


def parse_state(state: dict) -> dict:
    result = {
        "draft": "",
        "assistant_message": "",
        "recommendations": [],
        "doc_type": state.get("document_type", "draft"),
        "error": None,
    }

    # 1. Extract draft from state fields (priority order)
    for key in ("export_output", "draft_v1", "final_draft"):
        blob = state.get(key) or {}
        if isinstance(blob, dict):
            text = (
                blob.get("export_content", "")
                or blob.get("draft_text", "")
                or blob.get("text_content", "")
                or blob.get("content", "")
            )
            if text and isinstance(text, str) and len(text) > 50:
                result["draft"] = text
                break

    # 2. Extract recommendations from clarification questions
    questions = state.get("clarification_questions") or []
    for q in questions:
        if isinstance(q, dict):
            field = q.get("field", "")
            question = q.get("question", q.get("text", ""))
            if field or question:
                result["recommendations"].append(f"{field}: {question}" if field else question)

    # 3. Find AI messages
    ai_messages = []
    for msg in state.get("messages", []):
        if isinstance(msg, dict):
            role = msg.get("role") or msg.get("type", "")
            content = msg.get("content", "")
            if role in ("assistant", "ai") and content and len(content) > 10:
                ai_messages.append(content)

    if ai_messages:
        result["assistant_message"] = ai_messages[-1]

        # If no draft from state fields, find the longest AI message
        if not result["draft"]:
            longest = max(ai_messages, key=len)
            if len(longest) > 200:
                result["draft"] = longest
                if longest == ai_messages[-1] and len(ai_messages) > 1:
                    result["assistant_message"] = ai_messages[-2]

    if state.get("error_message"):
        result["error"] = state["error_message"]

    return result


def reset_session():
    st.session_state["thread_id"] = None
    st.session_state["chat_history"] = []
    st.session_state["draft_text"] = ""
    st.session_state["recommendations"] = []
    st.session_state["saved_file"] = ""


# ═══════════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════════
st.title("Legal Drafting Assistant")

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.session_state["langgraph_url"] = st.text_input("Server URL", value=_url())

    if st.button("Check Server"):
        try:
            r = requests.get(f"{_url()}/ok", timeout=5)
            st.success("Connected") if r.status_code == 200 else st.error(f"Error {r.status_code}")
        except Exception:
            st.error("Cannot connect")

    st.divider()
    if st.button("New Chat", type="primary"):
        reset_session()
        st.rerun()

    if st.session_state["thread_id"]:
        st.caption(f"Session: `{st.session_state['thread_id'][:8]}...`")

    # Show saved files
    st.divider()
    st.caption("Saved Drafts")
    if os.path.exists(OUTPUT_DIR):
        files = sorted(os.listdir(OUTPUT_DIR), reverse=True)[:10]
        if files:
            for f in files:
                st.text(f)
        else:
            st.text("No drafts yet")

# ── Two columns: Chat | Draft ────────────────────────────────────────
chat_col, draft_col = st.columns([1, 1])

# ── LEFT: Chat ───────────────────────────────────────────────────────
with chat_col:
    for entry in st.session_state["chat_history"]:
        with st.chat_message(entry["role"]):
            st.markdown(entry["content"])

    user_input = st.chat_input("Tell me what document you need...")

    if user_input:
        st.session_state["chat_history"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Drafting..."):
                result = send_message(user_input)

            if result.get("error"):
                st.error(result["error"])
                st.session_state["chat_history"].append({
                    "role": "assistant", "content": f"Error: {result['error']}"
                })
            else:
                if result.get("draft"):
                    st.session_state["draft_text"] = result["draft"]

                    # Auto-save to output folder
                    doc_type = result.get("doc_type", "draft") or "draft"
                    saved = save_draft_to_output(result["draft"], doc_type)
                    if saved:
                        st.session_state["saved_file"] = saved.get("docx", saved.get("txt", ""))

                if result.get("recommendations"):
                    st.session_state["recommendations"] = result["recommendations"]

                reply = result.get("assistant_message", "")
                if result.get("draft") and not reply:
                    reply = "Draft is ready — see the right panel."
                elif not reply:
                    reply = "Working on it..."

                st.markdown(reply)
                st.session_state["chat_history"].append({"role": "assistant", "content": reply})

        st.rerun()

# ── RIGHT: Draft + Recommendations ──────────────────────────────────
with draft_col:
    draft = st.session_state.get("draft_text", "")
    recommendations = st.session_state.get("recommendations", [])
    saved_file = st.session_state.get("saved_file", "")

    if recommendations:
        with st.expander("Recommendations — Fill these for a better draft", expanded=True):
            for rec in recommendations:
                st.markdown(f"- {rec}")
        st.divider()

    st.subheader("Draft")
    if draft:
        # Show save status
        if saved_file:
            st.success(f"Auto-saved to: `{os.path.basename(saved_file)}`")

        # Highlight {{PLACEHOLDERS}} in bold
        display = re.sub(r"\{\{([A-Za-z_]+)\}\}", r"**`{{\1}}`**", draft)
        st.markdown(display)

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "Download TXT",
                data=draft,
                file_name="legal_draft.txt",
                mime="text/plain",
            )
        with col2:
            # Provide DOCX download if file exists
            if saved_file and saved_file.endswith(".docx") and os.path.exists(saved_file):
                with open(saved_file, "rb") as f:
                    st.download_button(
                        "Download DOCX",
                        data=f.read(),
                        file_name=os.path.basename(saved_file),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
        with col3:
            placeholders = re.findall(r"\{\{([A-Za-z_]+)\}\}", draft)
            if placeholders:
                st.info(f"{len(placeholders)} placeholder(s)")
    else:
        st.caption("Your draft will appear here.")
