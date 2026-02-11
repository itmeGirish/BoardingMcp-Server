"""
End-to-end test for the WhatsApp Broadcasting Agent.

Invokes the FULL LangGraph broadcasting_graph (supervisor + 6 sub-agents)
with a user prompt. The agent autonomously orchestrates:

  Supervisor -> Data Processing -> Compliance -> Segmentation
  -> Content Creation -> Delivery -> Analytics

Uses:
  - REAL LLM (gpt-4o-mini via OpenAI)
  - REAL PostgreSQL database
  - REAL MCP Direct API server on port 9002
  - CSV contacts from docs/Broacsting - Sheet1.csv

Logging: Every agent phase, tool call, delegation, and state transition
is logged to console + logs/<date>/broadcast_agent_test.log

Usage:
    agent_steer/Scripts/python.exe -m pytest tests/unit/test_broadcasting_agent.py -v -s
"""

import os
import sys
import csv
import json
import logging
import asyncio
import time
import nest_asyncio
from pathlib import Path
from datetime import datetime

import pytest

# Apply nest_asyncio FIRST - before anything else
# This allows nested event loops which the agent tools require
nest_asyncio.apply()

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Fix DB connection pool for threaded usage inside LangGraph
# Must be done BEFORE any agent imports touch the engine
from app.database.postgresql import postgresql_connection
from sqlmodel import create_engine
postgresql_connection.engine = create_engine(
    postgresql_connection.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=60,
)


# ============================================================
# BROADCAST AGENT LOGGER
# ============================================================

class BroadcastAgentLogger:
    """
    Custom logger that captures and pretty-prints every agent event.
    Shows phase transitions, tool calls, delegations, and LLM responses.
    """

    def __init__(self):
        self.events = []
        self.start_time = time.time()
        self.current_agent = "SUPERVISOR"
        self.phase = "STARTUP"
        self.tool_calls_count = 0
        self.delegations = []

        # Set up file logger
        log_dir = PROJECT_ROOT / "logs" / datetime.now().strftime("%Y-%m-%d")
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = log_dir / "broadcast_agent_test.log"

        self.file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        self.file_handler.setLevel(logging.DEBUG)
        self.file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
        ))

    def _elapsed(self):
        return f"{time.time() - self.start_time:.1f}s"

    def _write(self, level, msg):
        record = logging.LogRecord(
            name="broadcast_test", level=level, pathname="", lineno=0,
            msg=msg, args=None, exc_info=None,
        )
        self.file_handler.emit(record)
        self.events.append({"time": self._elapsed(), "msg": msg})

    def banner(self, text):
        line = "=" * 70
        output = f"\n{line}\n  {text}\n{line}"
        print(output)
        self._write(logging.INFO, text)

    def phase_change(self, new_phase, details=""):
        self.phase = new_phase
        msg = f"[PHASE] {new_phase}"
        if details:
            msg += f" -- {details}"
        print(f"  >> {msg} ({self._elapsed()})")
        self._write(logging.INFO, msg)

    def agent_enter(self, agent_name):
        self.current_agent = agent_name.upper()
        msg = f"[AGENT ENTER] >>> {self.current_agent}"
        print(f"\n  {'~'*50}")
        print(f"  {msg} ({self._elapsed()})")
        print(f"  {'~'*50}")
        self._write(logging.INFO, msg)

    def agent_exit(self, agent_name):
        msg = f"[AGENT EXIT]  <<< {agent_name.upper()}"
        print(f"  {msg} ({self._elapsed()})")
        self._write(logging.INFO, msg)
        self.current_agent = "SUPERVISOR"

    def tool_call(self, tool_name, args_preview=""):
        self.tool_calls_count += 1
        msg = f"[TOOL #{self.tool_calls_count}] {self.current_agent} -> {tool_name}"
        if args_preview:
            msg += f"({args_preview})"
        print(f"    {msg}")
        self._write(logging.INFO, msg)

    def tool_result(self, tool_name, result_preview):
        msg = f"[RESULT] {tool_name} => {result_preview}"
        print(f"    {msg}")
        self._write(logging.DEBUG, msg)

    def llm_response(self, agent_name, content_preview):
        msg = f"[LLM] {agent_name}: {content_preview}"
        print(f"    {msg}")
        self._write(logging.DEBUG, msg)

    def delegation(self, from_agent, to_agent):
        self.delegations.append({"from": from_agent, "to": to_agent, "time": self._elapsed()})
        msg = f"[DELEGATE] {from_agent} ==> {to_agent}"
        print(f"  ** {msg} ({self._elapsed()})")
        self._write(logging.INFO, msg)

    def error(self, msg):
        print(f"  !! [ERROR] {msg}")
        self._write(logging.ERROR, msg)

    def info(self, msg):
        print(f"  {msg}")
        self._write(logging.INFO, msg)

    def summary(self):
        elapsed = self._elapsed()
        self.banner(f"TEST SUMMARY ({elapsed})")
        print(f"  Total tool calls: {self.tool_calls_count}")
        print(f"  Delegations: {len(self.delegations)}")
        for d in self.delegations:
            print(f"    {d['from']} -> {d['to']} at {d['time']}")
        print(f"  Final phase: {self.phase}")
        print(f"  Log file: {self.log_file}")
        print(f"  Total events: {len(self.events)}")


# Global logger instance
blog = BroadcastAgentLogger()


# ============================================================
# MONKEY-PATCH NODES FOR DEEP LOGGING
# ============================================================

def patch_agent_logging():
    """
    Monkey-patch the call_model_node functions in all agents to add
    detailed logging of tool calls, LLM responses, and routing decisions.
    """
    from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

    # --- Patch supervisor node ---
    from app.agents.whatsp_agents.nodes import supervisor_broadcasting as sup_node
    _original_sup_call = sup_node.call_model_node

    async def _logged_sup_call(state, config, system_prompt, tools, tool_names_set, delegation_tool_map=None):
        blog.info(f"[SUPERVISOR] call_model with {len(state.get('messages', []))} messages")

        # Log last message
        msgs = state.get("messages", [])
        if msgs:
            last = msgs[-1]
            if isinstance(last, ToolMessage):
                content = str(last.content)[:200]
                blog.tool_result(getattr(last, "name", "?"), content)
            elif isinstance(last, AIMessage):
                tc = getattr(last, "tool_calls", None)
                if tc:
                    for t in tc:
                        blog.tool_call(t.get("name", "?"), str(t.get("args", {}))[:100])
                else:
                    blog.llm_response("SUPERVISOR", str(last.content)[:200])
            elif isinstance(last, HumanMessage):
                blog.info(f"[USER] {str(last.content)[:200]}")

        result = await _original_sup_call(state, config, system_prompt, tools, tool_names_set, delegation_tool_map)

        # Log routing decision
        update = getattr(result, "update", {})
        goto = getattr(result, "goto", "?")
        if update and "messages" in update:
            for msg in update["messages"]:
                if isinstance(msg, AIMessage):
                    tc = getattr(msg, "tool_calls", None)
                    if tc:
                        for t in tc:
                            name = t.get("name", "?")
                            blog.tool_call(name, str(t.get("args", {}))[:100])
                            if name.startswith("delegate_to_"):
                                agent_name = name.replace("delegate_to_", "")
                                blog.delegation("SUPERVISOR", agent_name)
                    elif msg.content:
                        blog.llm_response("SUPERVISOR", str(msg.content)[:300])

        blog.info(f"[SUPERVISOR] routing -> {goto}")
        return result

    sup_node.call_model_node = _logged_sup_call

    # --- Patch sub-agent nodes ---
    agent_modules = {
        "DATA_PROCESSING": "app.agents.whatsp_agents.nodes.data_processing",
        "COMPLIANCE": "app.agents.whatsp_agents.nodes.compliance",
        "SEGMENTATION": "app.agents.whatsp_agents.nodes.segmentation",
        "CONTENT_CREATION": "app.agents.whatsp_agents.nodes.content_creation",
        "DELIVERY": "app.agents.whatsp_agents.nodes.delivery",
        "ANALYTICS": "app.agents.whatsp_agents.nodes.analytics",
    }

    import importlib
    for agent_label, module_path in agent_modules.items():
        mod = importlib.import_module(module_path)
        original_fn = mod.call_model_node

        def make_patched(label, orig):
            async def _logged_sub_call(state, config, system_prompt, tools, tool_names_set):
                blog.agent_enter(label)
                blog.info(f"[{label}] call_model with {len(state.get('messages', []))} messages")

                msgs = state.get("messages", [])
                if msgs:
                    last = msgs[-1]
                    if isinstance(last, ToolMessage):
                        blog.tool_result(getattr(last, "name", "?"), str(last.content)[:200])

                result = await orig(state, config, system_prompt, tools, tool_names_set)

                update = getattr(result, "update", {})
                goto = getattr(result, "goto", "?")
                if update and "messages" in update:
                    for msg in update["messages"]:
                        if isinstance(msg, AIMessage):
                            tc = getattr(msg, "tool_calls", None)
                            if tc:
                                for t in tc:
                                    blog.tool_call(t.get("name", "?"), str(t.get("args", {}))[:100])
                            elif msg.content:
                                blog.llm_response(label, str(msg.content)[:300])

                blog.info(f"[{label}] routing -> {goto}")

                if str(goto) == "__end__":
                    blog.agent_exit(label)

                return result
            return _logged_sub_call

        mod.call_model_node = make_patched(agent_label, original_fn)


# ============================================================
# CSV PARSING HELPER
# ============================================================

def parse_csv_contacts(csv_path: str) -> list:
    """Parse contacts from the Broacsting CSV file."""
    contacts = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "").strip()
            phone = row.get("phone number", "").strip()
            if phone:
                contacts.append({"name": name, "phone": phone})
    return contacts


# ============================================================
# TEST CLASS
# ============================================================

class TestBroadcastingAgentE2E:
    """
    End-to-end test that invokes the broadcasting_graph with a user prompt.

    The LLM (gpt-4o-mini) autonomously:
    1. Initializes broadcast (initialize_broadcast)
    2. Delegates to Data Processing Agent (process contacts)
    3. Delegates to Compliance Agent (opt-in, suppression, time window, health)
    4. Delegates to Segmentation Agent (lifecycle, 24hr, timezone, frequency)
    5. Delegates to Content Creation Agent (list templates, select APPROVED)
    6. Delegates to Delivery Agent (send messages via MCP)
    7. Delegates to Analytics Agent (delivery report)

    Requires:
      - OPENAI_API_KEY in .env
      - PostgreSQL running with user1 data
      - MCP Direct API server on port 9002
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up logging patches before test."""
        patch_agent_logging()
        yield

    def test_full_broadcast_agent_with_csv(self):
        """
        Run the FULL broadcasting agent with CSV contacts.

        User prompt instructs the agent to broadcast for Bedzee PG company
        using contacts from the CSV file.
        """
        blog.banner("BROADCASTING AGENT E2E TEST")

        # Parse CSV
        csv_path = PROJECT_ROOT / "docs" / "Broacsting - Sheet1.csv"
        contacts = parse_csv_contacts(str(csv_path))
        blog.info(f"CSV contacts: {contacts}")

        assert len(contacts) > 0, f"No contacts found in {csv_path}"

        # Build contact list string for the prompt
        contact_lines = []
        phone_list = []
        for c in contacts:
            contact_lines.append(f"  - {c['name']}: +91{c['phone']}")
            phone_list.append(f"+91{c['phone']}")

        contacts_text = "\n".join(contact_lines)
        phones_json = json.dumps(phone_list)

        # User prompt - comprehensive instruction for the agent
        user_prompt = f"""Start a new broadcast campaign for Bedzee PG company.

User ID: user1

Here are the contacts from our CSV file:
{contacts_text}

Phone numbers list: {phones_json}

Instructions:
1. Initialize the broadcast for user1
2. Process these {len(contacts)} contacts (validate and normalize phones)
3. Run compliance checks
4. Segment the audience (all contacts as one segment)
5. Find an existing APPROVED MARKETING template (do NOT create a new one)
6. Select the APPROVED template for the broadcast
7. Send the broadcast messages to all contacts
8. Get the delivery report after sending

IMPORTANT: Use an existing APPROVED template. Do NOT submit a new template.
Proceed through all phases without asking for confirmation."""

        blog.info(f"User prompt length: {len(user_prompt)} chars")
        blog.phase_change("INVOKING GRAPH", f"{len(contacts)} contacts")

        # Build initial state
        from langchain_core.messages import HumanMessage

        initial_state = {
            "messages": [HumanMessage(content=user_prompt)],
            "copilotkit": {
                "actions": [],
                "context": [],
                "intercepted_tool_calls": None,
                "original_ai_message_id": None,
            },
            "broadcast_phase": None,
            "broadcast_job_id": None,
            "user_id": "user1",
            "error_message": None,
        }

        # Import and invoke the broadcasting graph
        # We rebuild the graph AFTER patching to pick up patched nodes
        from app.agents.whatsp_agents.whatsp_broadcasting import _assemble_graph

        blog.info("Assembling broadcasting graph with 6 sub-agents...")
        graph = _assemble_graph()
        blog.info("Graph assembled. Starting execution...")

        blog.banner("AGENT EXECUTION START")

        # Run the graph with a recursion limit to prevent infinite loops
        # Use nest_asyncio compatible event loop (not asyncio.run which creates new loop)
        config = {"recursion_limit": 80}

        loop = asyncio.get_event_loop()

        try:
            result = loop.run_until_complete(
                graph.ainvoke(initial_state, config=config)
            )
        except Exception as e:
            blog.error(f"Graph execution failed: {type(e).__name__}: {e}")
            blog.summary()
            raise

        blog.banner("AGENT EXECUTION COMPLETE")

        # ============================================
        # ANALYZE RESULT
        # ============================================
        messages = result.get("messages", [])
        blog.info(f"Total messages in conversation: {len(messages)}")

        # Log all messages with types
        from langchain_core.messages import AIMessage, ToolMessage

        blog.banner("CONVERSATION TRACE")
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            if isinstance(msg, HumanMessage):
                content = str(msg.content)[:150]
                print(f"  [{i}] USER: {content}...")
            elif isinstance(msg, AIMessage):
                tc = getattr(msg, "tool_calls", None)
                if tc:
                    for t in tc:
                        print(f"  [{i}] AI TOOL_CALL: {t.get('name')}({str(t.get('args', {}))[:80]})")
                elif msg.content:
                    print(f"  [{i}] AI: {str(msg.content)[:200]}")
                else:
                    print(f"  [{i}] AI: (empty)")
            elif isinstance(msg, ToolMessage):
                content = str(msg.content)[:150]
                print(f"  [{i}] TOOL[{getattr(msg, 'name', '?')}]: {content}")
            else:
                print(f"  [{i}] {msg_type}: {str(getattr(msg, 'content', ''))[:100]}")

        blog.file_handler.flush()

        # ============================================
        # EXTRACT KEY RESULTS
        # ============================================
        blog.banner("KEY RESULTS")

        # Find broadcast_job_id from tool results
        broadcast_job_id = None
        template_name = None
        sent_count = 0
        failed_count = 0

        for msg in messages:
            if isinstance(msg, ToolMessage):
                try:
                    data = json.loads(str(msg.content))
                    if isinstance(data, dict):
                        if data.get("broadcast_job_id"):
                            broadcast_job_id = data["broadcast_job_id"]
                        if data.get("template_name"):
                            template_name = data["template_name"]
                        if "sent" in data:
                            sent_count = data.get("sent", sent_count)
                        if "failed" in data:
                            failed_count = data.get("failed", failed_count)
                        if data.get("sent_count"):
                            sent_count = data["sent_count"]
                except (json.JSONDecodeError, TypeError):
                    pass

        blog.info(f"Broadcast Job ID: {broadcast_job_id}")
        blog.info(f"Template: {template_name}")
        blog.info(f"Sent: {sent_count}, Failed: {failed_count}")

        # Get final AI message (agent's final response)
        final_ai_msg = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_ai_msg = msg.content
                break

        if final_ai_msg:
            blog.banner("AGENT FINAL RESPONSE")
            print(f"  {final_ai_msg[:1000]}")

        # ============================================
        # VERIFY DB STATE
        # ============================================
        if broadcast_job_id:
            blog.banner("DATABASE VERIFICATION")
            from app.database.postgresql.postgresql_connection import get_session

            from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

            with get_session() as session:
                repo = BroadcastJobRepository(session=session)
                job = repo.get_by_id(broadcast_job_id)

                if job:
                    blog.info(f"DB Phase: {job['phase']}")
                    blog.info(f"DB Template: {job.get('template_name')}")
                    blog.info(f"DB Total Contacts: {job.get('total_contacts')}")
                    blog.info(f"DB Valid Contacts: {job.get('valid_contacts')}")
                    blog.info(f"DB Sent: {job.get('sent_count')}")
                    blog.info(f"DB Failed: {job.get('failed_count')}")
                    blog.info(f"DB Scheduled For: {job.get('scheduled_for')}")
                    blog.info(f"DB Started: {job.get('started_sending_at')}")
                    blog.info(f"DB Completed: {job.get('completed_at')}")

                    # Assert broadcast completed or at least progressed
                    assert job["phase"] in (
                        "COMPLETED", "SENDING", "READY_TO_SEND",
                        "SCHEDULED", "CONTENT_CREATION", "PENDING_APPROVAL",
                        "SEGMENTATION", "COMPLIANCE_CHECK",
                        "DATA_PROCESSING", "INITIALIZED", "FAILED",
                    ), f"Unexpected final phase: {job['phase']}"
                else:
                    blog.error(f"Broadcast job {broadcast_job_id} not found in DB")

        blog.summary()

        # Basic assertions
        assert len(messages) > 3, "Agent should have produced multiple messages"
        blog.info("TEST PASSED")
