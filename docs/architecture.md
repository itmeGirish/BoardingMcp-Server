# WhatsApp Broadcasting Agent - Architecture

## Overview

Multi-agent broadcast system built on **LangGraph**. One **Supervisor** orchestrates a 12-phase state machine, delegating to **6 specialized sub-agents**.

| Component | Technology |
|-----------|-----------|
| Agent Framework | LangGraph (StateGraph) |
| LLM | GPT-4o-mini (ChatOpenAI) |
| Frontend | CopilotKit (CopilotKitState) |
| MCP Protocol | FastMCP + langchain-mcp-adapters |
| Database | PostgreSQL + SQLModel |
| Async | ThreadPoolExecutor + nest_asyncio |
| Package Manager | uv (agent_steer venv) |
| API Framework | FastAPI (ASGI) |

---

## Graph Structure

```
START
  |
  v
call_model (LLM) -----> [END] (no tool calls)
  |
  v (tool call detected)
tool_node (executes tool)
  |
  v
route_after_tool
  |--- normal tool -------> call_model (loop back)
  |--- delegation tool ---> sub-agent graph ---> call_model (return)
```

**Sub-agents registered in the supervisor graph:**

| Node Name | Graph Singleton | Entry Point |
|-----------|----------------|-------------|
| `data_processing` | `data_processing_graph` | `data_processing_agent.py` |
| `compliance` | `compliance_graph` | `compliance_agent.py` |
| `segmentation` | `segmentation_graph` | `segmentation_agent.py` |
| `content_creation` | `content_creation_graph` | `content_creation_agent.py` |
| `delivery` | `delivery_graph` | `delivery_agent.py` |
| `analytics` | `analytics_graph` | `analytics_agent.py` |

---

## State Machine

| # | Phase | Transitions To | Handler |
|---|-------|---------------|---------|
| 1 | `INITIALIZED` | DATA_PROCESSING | Supervisor |
| 2 | `DATA_PROCESSING` | COMPLIANCE_CHECK, FAILED | Data Processing Agent |
| 3 | `COMPLIANCE_CHECK` | SEGMENTATION, FAILED | Compliance Agent |
| 4 | `SEGMENTATION` | CONTENT_CREATION | Segmentation Agent |
| 5 | `CONTENT_CREATION` | PENDING_APPROVAL, READY_TO_SEND | Content Creation Agent |
| 6 | `PENDING_APPROVAL` | READY_TO_SEND, CONTENT_CREATION, FAILED | Content Creation Agent |
| 7 | `READY_TO_SEND` | SENDING, CANCELLED | Supervisor |
| 8 | `SENDING` | COMPLETED, PAUSED, FAILED | Delivery Agent |
| 9 | `PAUSED` | SENDING, CANCELLED | Supervisor |
| 10 | `COMPLETED` | _(terminal)_ | Analytics Agent |
| 11 | `FAILED` | _(terminal)_ | Supervisor |
| 12 | `CANCELLED` | _(terminal)_ | Supervisor |

Transitions are enforced by `BroadcastJobRepository.ALLOWED_TRANSITIONS` at the database layer.

---

## Delegation Pattern

```
1. LLM calls delegate_to_* tool
2. call_model_node routes to tool_node
3. tool_node executes the delegation tool (returns JSON)
4. route_after_tool checks ToolMessage.name against DELEGATION_TOOL_MAP
5. Routes to the sub-agent graph node
6. Sub-agent runs its own call_model <-> tool_node loop
7. Sub-agent completes, edge returns to supervisor call_model
```

**Delegation map:**

| Delegation Tool | Routes To |
|----------------|-----------|
| `delegate_to_data_processing` | `data_processing` |
| `delegate_to_compliance` | `compliance` |
| `delegate_to_segmentation` | `segmentation` |
| `delegate_to_content_creation` | `content_creation` |
| `delegate_to_delivery` | `delivery` |
| `delegate_to_analytics` | `analytics` |

---

## File Structure

Each agent has 5 modules (state, prompt, tools, nodes, graph) plus an entry point:

```
app/agents/whatsp_agents/
  whatsp_broadcasting.py          # Supervisor entry point
  data_processing_agent.py        # Sub-agent entry points
  compliance_agent.py
  segmentation_agent.py
  content_creation_agent.py
  delivery_agent.py
  analytics_agent.py

  states/                         # Agent state definitions
    supervisor_broadcasting.py      BroadcastingAgentState, BroadcastPhase
    data_processing.py              DataProcessingAgentState
    compliance.py                   ComplianceAgentState
    segmentation.py                 SegmentationAgentState
    content_creation.py             ContentCreationAgentState
    delivery.py                     DeliveryAgentState
    analytics.py                    AnalyticsAgentState

  prompts/                        # System prompts per agent
  tools/                          # @tool functions per agent
  nodes/                          # call_model_node per agent
  graphs/                         # StateGraph factory per agent
  mcp_client/                     # MCP connection manager
```

**Sub-agent graph topology (identical for all):**

```
START --> call_model --> tool_node --> call_model --> ... --> END
```

**Dependency injection pattern (all entry points):**

```python
from functools import partial

graph = create_graph(
    state_class=AgentState,
    call_model_node_func=partial(call_model_node,
        system_prompt=SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES),
    tools=BACKEND_TOOLS,
)
```

---

## Sub-Agent Details

### 1. Data Processing Agent

| | |
|---|---|
| **Phase** | DATA_PROCESSING |
| **Tools** | 8 |
| **Flows** | Beginner (FB verify first) / Standard |

| Tool | Purpose |
|------|---------|
| `check_beginner_status` | Check `first_broadcasting` flag |
| `verify_facebook_business` | FB Business verification via MCP |
| `flip_beginner_flag` | Set `first_broadcasting=False` |
| `process_phone_list` | Validate phone numbers to E.164 |
| `process_contact_file` | Parse Excel/CSV uploads |
| `run_deduplication` | 4-stage: exact, normalized, fuzzy (Levenshtein<=1), cross-campaign |
| `score_contacts` | Quality 0-100: Phone 40%, Completeness 25%, Recency 20%, Engagement 15% |
| `get_processing_summary` | Final report |

### 2. Compliance Agent

| | |
|---|---|
| **Phase** | COMPLIANCE_CHECK |
| **Tools** | 5 |
| **Flow** | 4 sequential checks |

| Tool | Purpose |
|------|---------|
| `verify_opt_in_consent` | Check `consent_logs` for valid opt-in |
| `filter_suppression_lists` | Filter global, campaign, temporary, bounce |
| `validate_time_windows` | India 9AM-9PM, EU 8AM-9PM, US 8AM-9PM, UAE 9AM-10PM |
| `check_account_health` | Quality score + tier + status via MCP |
| `process_opt_out_keyword` | STOP, UNSUBSCRIBE, PAUSE, START handling |

### 3. Segmentation Agent

| | |
|---|---|
| **Phase** | SEGMENTATION |
| **Tools** | 6 |

| Tool | Purpose |
|------|---------|
| `classify_lifecycle_stages` | New <=7d, Engaged <=30d, Active <=60d, At-Risk 31-60d, Dormant 61-90d, Churned 90+d (excluded) |
| `detect_24hr_windows` | Free service window contacts (30-50% cost savings) |
| `cluster_by_timezone` | Group by timezone, optimal send 10AM-2PM local |
| `check_frequency_caps` | Marketing 2/week, Promotional 1/week, Combined 4/week |
| `create_audience_segments` | Build segments by lifecycle, country, or all |
| `get_segmentation_summary` | Final report |

### 4. Content Creation Agent

| | |
|---|---|
| **Phase** | CONTENT_CREATION, PENDING_APPROVAL |
| **Tools** | 8 |
| **Types** | Text, Image, Video, Document |

| Tool | Purpose |
|------|---------|
| `list_user_templates` | List from DB (filter by status/category) |
| `get_template_detail` | Fetch from MCP + sync status to DB |
| `submit_template` | Submit via MCP + store in DB |
| `check_template_status` | Poll approval via MCP + sync DB |
| `edit_template` | Edit via MCP + reset to PENDING |
| `delete_template_by_id` | Delete via MCP + soft-delete DB |
| `delete_template_by_name` | Delete via MCP + soft-delete DB |
| `select_template_for_broadcast` | Link APPROVED template to job |

**Lifecycle:** Create -> Submit -> Await Approval -> (Rejected -> Edit -> Resubmit) -> Approved -> Select

### 5. Delivery Agent

| | |
|---|---|
| **Phase** | SENDING |
| **Tools** | 6 |
| **Policy** | `send_marketing_lite_message` FIRST, `send_message` fallback |

| Tool | Purpose |
|------|---------|
| `prepare_delivery_queue` | Build 5-priority queue, check tier limits |
| `send_lite_broadcast` | **Try first** - cheaper promotional via MCP |
| `send_template_broadcast` | **Fallback** - full template via MCP (media/buttons) |
| `retry_failed_messages` | Backoff: 0s, 30s, 2m, 10m, 1hr |
| `get_delivery_summary` | Sent/delivered/failed/pending/rate |
| `mark_messages_read` | Read receipts via MCP |

**Priority queue:** 1=Urgent/OTP, 2=24hr-window, 3=Normal, 4=Low, 5=Background

**Tier limits:** Unverified=250, T1=1K, T2=10K, T3=100K, T4=Unlimited

**Errors:** Non-retryable: 131026, 131047, 131051, 131031 | Retryable: 131053, 130429

### 6. Analytics Agent

| | |
|---|---|
| **Phase** | COMPLETED (post-delivery) |
| **Tools** | 5 |
| **Note** | Cost tracking excluded (future) |

| Tool | Purpose |
|------|---------|
| `get_broadcast_delivery_report` | Job metrics from DB (sent, delivered, rates, duration) |
| `get_waba_analytics_report` | WABA analytics via MCP (today/7d/30d/90d) |
| `get_messaging_health_report` | Quality GREEN/YELLOW/RED, tier, alerts via MCP |
| `get_broadcast_history` | Cross-campaign comparison |
| `generate_optimization_recommendations` | AI recommendations for rate, quality, engagement |

**Quality alerts:** GREEN=healthy, YELLOW=reduce volume, RED=stop immediately

---

## MCP Integration

| Server | Port | Transport |
|--------|------|-----------|
| Boarding MCP | 9001 | streamable-http |
| Direct API MCP | 9002 | streamable-http |

**MCP tools used:**

| MCP Tool | Used By |
|----------|---------|
| `verify_facebook_business` | Data Processing |
| `get_recent_conversations` | Segmentation |
| `submit_whatsapp_template_message` | Content Creation |
| `get_template_by_id` | Content Creation |
| `get_templates` | Content Creation |
| `edit_template` | Content Creation |
| `delete_wa_template_by_id` | Content Creation |
| `delete_wa_template_by_name` | Content Creation |
| `send_marketing_lite_message` | Delivery |
| `send_message` | Delivery |
| `mark_message_as_read` | Delivery |
| `get_messaging_health_status` | Compliance, Delivery, Analytics |
| `get_waba_analytics` | Analytics |

**Call pattern** (ThreadPoolExecutor + nest_asyncio for ASGI compatibility):

```python
def _call_direct_api_mcp(tool_name, params):
    async def _call():
        client = MultiServerMCPClient({"DirectApiMCP": {"url": "http://127.0.0.1:9002/mcp", "transport": "streamable-http"}})
        async with client.session("DirectApiMCP") as session:
            tools = await load_mcp_tools(session)
            return parse_mcp_result(await tools[tool_name].ainvoke(params))
    loop = asyncio.new_event_loop()
    try: return loop.run_until_complete(_call())
    finally: loop.close()
```

---

## Database

**Models:**

| Model | Table | Purpose |
|-------|-------|---------|
| `BroadcastJob` | `broadcast_jobs` | Campaign state, contacts, template, progress |
| `ProcessedContact` | `processed_contacts` | Validated E.164 contacts with quality scores |
| `TemplateCreation` | `template_creations` | Template storage with status tracking |
| `ConsentLog` | `consent_logs` | Opt-in/opt-out consent records |
| `SuppressionList` | `suppression_lists` | Do-not-contact lists |

**BroadcastJob fields:** `id`, `user_id`, `project_id`, `phase`, `contacts_data` (JSON), `total_contacts`, `valid_contacts`, `invalid_contacts`, `compliance_status`, `segments_data` (JSON), `template_id`, `template_name`, `template_language`, `template_category`, `template_status`, `sent_count`, `delivered_count`, `failed_count`, `pending_count`, `error_message`, `created_at`, `updated_at`, `started_sending_at`, `completed_at`, `is_active`

**ProcessedContact fields:** `id`, `broadcast_job_id`, `user_id`, `phone_e164`, `name`, `email`, `country_code`, `quality_score` (0-100), `custom_fields` (JSON), `is_duplicate`, `duplicate_of`, `created_at`

**TemplateCreation fields:** `template_id`, `user_id`, `business_id`, `name`, `category`, `language`, `status`, `components` (JSON), `rejected_reason`, `quality_rating`, `usage_count`, `last_used_at`, `created_at`, `updated_at`, `deleted_at`

**Repository pattern:**

```python
with get_session() as session:
    repo = BroadcastJobRepository(session=session)
    job = repo.get_by_id(broadcast_job_id)
    repo.update_phase(broadcast_job_id, "SENDING")
```

**Transition validation:**

```python
ALLOWED_TRANSITIONS = {
    "INITIALIZED":      {"DATA_PROCESSING"},
    "DATA_PROCESSING":  {"COMPLIANCE_CHECK", "FAILED"},
    "COMPLIANCE_CHECK": {"SEGMENTATION", "FAILED"},
    "SEGMENTATION":     {"CONTENT_CREATION"},
    "CONTENT_CREATION": {"PENDING_APPROVAL", "READY_TO_SEND"},
    "PENDING_APPROVAL": {"READY_TO_SEND", "CONTENT_CREATION", "FAILED"},
    "READY_TO_SEND":    {"SENDING", "CANCELLED"},
    "SENDING":          {"COMPLETED", "PAUSED", "FAILED"},
    "PAUSED":           {"SENDING", "CANCELLED"},
    "COMPLETED":        set(),
    "FAILED":           set(),
    "CANCELLED":        set(),
}
```

---

## Workflow Sequence

| Step | Action | Phase |
|------|--------|-------|
| 1 | `initialize_broadcast()` - verify JWT, create job | INITIALIZED |
| 2 | `delegate_to_data_processing` - parse, validate, dedupe, score | DATA_PROCESSING |
| 3 | `delegate_to_compliance` - opt-in, suppression, time, health | COMPLIANCE_CHECK |
| 4 | `delegate_to_segmentation` - lifecycle, 24hr, timezone, frequency | SEGMENTATION |
| 5 | `delegate_to_content_creation` - template create/approve/select | CONTENT_CREATION |
| 6 | Poll template status (if pending) | PENDING_APPROVAL |
| 7 | Show summary, user confirms | READY_TO_SEND |
| 8 | `delegate_to_delivery` - lite-first, retry, track | SENDING |
| 9 | Pause/resume (if requested) | PAUSED |
| 10 | `delegate_to_analytics` - report, health, recommendations | COMPLETED |

---

## Adding a New Sub-Agent

**Step 1** - Create 5 files:

| File | Contains |
|------|----------|
| `states/new_agent.py` | `NewAgentState(CopilotKitState)` + status literals |
| `prompts/new_agent.py` | `NEW_AGENT_SYSTEM_PROMPT` |
| `tools/new_agent.py` | `@tool` functions + `BACKEND_TOOLS` export |
| `nodes/new_agent.py` | `call_model_node` (copy existing) |
| `graphs/new_agent.py` | `create_graph` factory (copy existing) |

**Step 2** - Create entry point `new_agent_agent.py`:

```python
from functools import partial
new_agent_graph = create_graph(
    state_class=NewAgentState,
    call_model_node_func=partial(call_model_node, system_prompt=..., tools=..., tool_names_set=...),
    tools=BACKEND_TOOLS,
)
```

**Step 3** - Register in `tools/supervisor_broadcasting.py`:

```python
@tool
def delegate_to_new_agent(user_id, broadcast_job_id, project_id) -> str: ...

BACKEND_TOOLS = [..., delegate_to_new_agent]
DELEGATION_TOOL_MAP = {..., "delegate_to_new_agent": "new_agent"}
```

**Step 4** - Wire in `whatsp_broadcasting.py`:

```python
from .new_agent_agent import new_agent_graph
sub_agents = {..., "new_agent": new_agent_graph}
```

**Step 5** - Export in `states/__init__.py`:

```python
from .new_agent import NewAgentState, NewAgentStatus
```

**Step 6** - Verify import chain compiles successfully.
