# Legal Drafting Agent — v5.1 (running) | v8.4 (target)

Version: 5.1 (active pipeline) | 8.4 (target architecture)
Runtime: Python 3.11+ | LangGraph | Qdrant | PostgreSQL 14+ | Ollama Cloud
Target: 9.5/10 | 2 LLM calls (clean draft) | Court-ready Indian legal documents

Full target architecture: `docs/architecture_drafting_agent_v8.4.md`

---

## 1. Design Philosophy (8 Principles)

1. **Verify, Don't Hope** — every claim traceable to source or flagged as placeholder
2. **Deterministic > LLM** — formatting, citations, compliance, court fees = deterministic. Only intake, drafting, review use LLM
3. **Generate First, Validate After** — LLM drafts freely, gates validate output
4. **Minimize Cloud Dependency** — 2 LLM calls for clean drafts. Cache aggressively
5. **Graceful Degradation, Never Block** — missing facts -> `{{PLACEHOLDER}}`, enrichment fails -> `UNKNOWN`, model throttled -> fallback chain
6. **Few-Shot > Exhaustive Rules** — one exemplar > 50 rules. Max 5 system instructions
7. **Measure Everything** — every document produces structured metrics
8. **Privacy by Default** — PII redacted before cloud calls, de-redacted after gates

When principles conflict, lower-numbered wins.

---

## 2. Pipeline (v5.1 — what's actually running)

```
STAGE 1: CONTEXT GATHERING (~12-15s, 1 LLM call)
  intake_classify (1 LLM) -> rag (4 Qdrant queries) -> enrichment (limitation + provisions + LKB + court_fee parallel)

STAGE 2: FREE-TEXT DRAFTING (~30-50s, 1 LLM call)
  draft_freetext: exemplar-guided, LKB-informed, outputs complete court-ready document

STAGE 3: DETERMINISTIC VALIDATION (~0.1s, zero LLM calls)
  Gate 1: evidence_anchoring (facts -> intake)
  Gate 2: lkb_compliance (acts, superseded laws)
  Gate 3: postprocess (formatting, numbering, spacing)
  Gate 4: citation_validator (provisions -> verified_provisions)

STAGE 4: REVIEW (~40-70s, 1 LLM call — slim payload)
  Slim context: draft text + gate errors + user request only (~7K tokens)
  Phase 1: checks | Phase 2: inline fix -> END

TOTAL: 2-3 LLM calls | ~60-120s end-to-end
```

---

## 3. Data Stores

### Active Stores
- **LKB v3.0** — 24 cause types with conditional resolution fields (`_type: "conditional"`)
- **Qdrant** — vector search, ~12,394 points, `civil` collection
- **Exemplars** — structural exemplars per cause type (~1,500 tokens each)
- **Cause-type aliases** — `_CAUSE_TYPE_ALIASES` in LKB for fuzzy cause_type matching

### Planned (v8.4)
- **statute_store** — authoritative statutory sections for citation validation
- **court_fee_pack** — curated state-wise court fee rules
- **agent_cache** — L1 in-process + L2 PostgreSQL

---

## 4. Model Assignment (current)

| Node | Model | Reasoning | Temp | When |
|------|-------|-----------|------|------|
| intake_classify | qwen3.5:cloud | OFF | 0.3 | Always |
| enrichment (limitation) | glm-4.7:cloud | OFF | 0.3 | Cache miss only |
| draft | glm-5:cloud | ON | 0.7 | Always |
| review | glm-5:cloud | ON | 0.3 | When gates flag issues |

### Fallback Chain
```
glm-5:cloud    -> glm-4.6:cloud -> OpenAI (REVIEW_LLM_MODEL)
qwen3.5:cloud  -> glm-4.6:cloud -> OpenAI
All cloud down  -> draft skeleton with all placeholders
```

### Router/Enrichment
```
OLLAMA_ROUTER_MODEL: glm-4.7:cloud (classification, routing)
OLLAMA_INTAKE_MODEL: qwen3.5:cloud (intake+classify)
OLLAMA_DRAFT_MODEL: glm-5:cloud (draft node)
OLLAMA_REVIEW_MODEL: glm-5:cloud (review node)
```

---

## 5. Verification Gates (4 gates, zero LLM)

| Gate | What it checks | Auto-fix? |
|------|---------------|-----------|
| Evidence Anchoring | Every fact traces to intake | Yes (tokens -> placeholder) |
| LKB Compliance | Primary acts cited, superseded law auto-replace | Yes (superseded) |
| Postprocess | Paragraph numbering, annexure labels, verification clause, spacing | Yes |
| Citation Validator | Every citation in verified_provisions | Flag only |

---

## 6. LKB v3.0 (with Conditional Resolution + Aliases)

```python
from app.agents.drafting_agents.lkb import lookup
entry = lookup("Civil", "recovery_of_possession")
# Returns: primary_acts, alternative_acts, limitation (conditional),
#          court_rules, damages_categories, permitted_doctrines,
#          terminology (conditional), mandatory_averments,
#          doc_type_keywords, coa_guidance

# Aliases resolve near-misses:
# "property_law" -> "recovery_of_possession"
# "money_recovery" -> "money_recovery_loan"
# "breach_contract" -> "breach_of_contract"

# Conditional fields resolved at runtime:
from app.agents.drafting_agents.lkb import resolve_entry
resolved = resolve_entry(entry, user_request_text)
# Flattens _type:"conditional" fields using keyword inference
```

---

## 7. Review Node (Slim Payload)

Review receives only:
- **Draft text** (~3K tokens) — plain text, not JSON
- **Gate errors summary** (~200 tokens) — compact, from deterministic gates
- **User request** (~200 tokens) — for fact fabrication check
- **doc_type + law_domain** (~10 tokens)

**Total context: ~3.5K tokens** (was ~15K before pruning)

Review does NOT receive: RAG chunks, court fee context, legal research context, cited chunk IDs. Gates already verified all of that deterministically.

---

## 8. Settings Pattern

- Always use `settings.FIELD_NAME` from `from app.config import settings`
- NEVER use `os.getenv()` or `load_dotenv()`
- Import: `from app.config import logger, settings`

### Key Settings
```
# Pipeline control
DRAFTING_MAX_REVIEW_CYCLES: int = 1
DRAFTING_REVIEW_INLINE_FIX: bool = True
DRAFTING_DRAFT_RAG_LIMIT: int = 15
DRAFTING_REVIEW_RAG_LIMIT: int = 5
DRAFTING_CITATION_VALIDATOR_ENABLED: bool = True
DRAFTING_SKIP_REVIEW: bool = False
TEMPLATE_ENGINE_ENABLED: bool = False  # v8.1 template engine (not active)

# Model config (in settings.py, overridable via .env)
OLLAMA_ROUTER_MODEL: str = "glm-4.7:cloud"
OLLAMA_INTAKE_MODEL: str = "qwen3.5:cloud"
OLLAMA_DRAFT_MODEL: str = "glm-5:cloud"
OLLAMA_REVIEW_MODEL: str = "glm-5:cloud"

# OpenAI fallback for review (when review uses OpenAI)
REVIEW_LLM_MODEL: Optional[str] = None
REVIEW_REASONING_EFFORT: Optional[str] = "medium"
```

---

## 9. File Map (actual)

```
app/agents/drafting_agents/
├── drafting_graph.py                    # LangGraph StateGraph wiring
├── nodes/
│   ├── intake_classify.py               # Stage 1: merged intake + classify
│   ├── ragDomain.py                     # Stage 1: Qdrant retrieval
│   ├── enrichment.py                    # Stage 1: limitation + provisions + LKB + court_fee
│   ├── draft_single_call.py             # Stage 2: draft_freetext_node (v5.0 free-text)
│   ├── evidence_anchoring.py            # Gate 1: evidence anchoring
│   ├── lkb_compliance.py               # Gate 2: LKB + superseded law check
│   ├── postprocess.py                   # Gate 3: formatting fixes
│   ├── citation_validator.py            # Gate 4: citation verification
│   ├── reviews.py                       # Stage 4: review (slim payload)
│   └── _utils.py                        # Shared helpers
├── prompts/
│   ├── intake_classify.py               # Intake+classify system/user prompts
│   ├── draft_prompt.py                  # Draft system/user prompts + exemplar loading
│   └── review.py                        # Review system/user prompts
├── states/draftGraph.py                 # DraftingState + Pydantic models
├── lkb/
│   ├── __init__.py                      # Registry, lookup, aliases, conditional resolver
│   └── civil.py                         # 24 cause types with conditional fields (v3.0)
├── exemplars/                           # Structural exemplars per cause type
├── tools/                               # Qdrant + Brave API wrappers
└── ragDomains/

app/config/settings.py                   # Feature flags + model config
app/services/llm_service.py              # Ollama Cloud client + fallback chains
```

---

## 10. Critical Rules (Non-Negotiable)

### Never Hardcode Legal Content in Python
- No `_COA_KEYWORDS`, no `must_include`, no per-scenario if/elif
- Legal substance: LLM knowledge + LKB + RAG + user request
- Python handles: validation, anchoring, citation verification, formatting

### Generate First, Validate After
- LLM drafts freely (plain text, exemplar-guided)
- 4 deterministic gates validate output
- Fix only what gates flag

### Deterministic > LLM
- Gates, LKB lookup, citation check = deterministic
- Only intake, drafting, review use LLM

### Evidence Anchoring is Mandatory
- Every factual claim -> intake/evidence
- Unsupported tokens -> `{{PLACEHOLDER}}`

### Citation Verification is Mandatory
- Every citation -> verified_provisions
- Case citations (AIR/SCC/ILR) -> ERROR unless user-provided

### Graceful Degradation, Never Block
- Missing facts -> `{{PLACEHOLDER}}`
- Enrichment fails -> `UNKNOWN` -> placeholder
- Draft fails -> retry -> fallback model chain
- Gate fails -> skip, log warning, continue
- Review fails -> deliver with gates-only quality

---

## 11. Anti-Patterns (DO NOT DO)

- Do NOT constrain LLM output format (no JSON section keys)
- Do NOT hardcode legal content in Python
- Do NOT use `os.getenv()` — use `settings.FIELD_NAME`
- Do NOT auto-fix substantive legal content — only formatting
- Do NOT allow case citations unless verified
- Do NOT dump all RAG chunks into review — use slim payload
- Do NOT add LLM calls for deterministic tasks
- Do NOT guess court fee — use verified data or placeholder
- Do NOT send full JSON dumps to review — only draft text + gate errors

---

## 12. Recent Changes (2026-03-06)

- **Review slim payload** — cut review input from ~15K to ~5K tokens by removing RAG chunks, court fee, legal research (gates already verified)
- **LKB cause-type aliases** — 16 aliases for common LLM near-misses (property_law -> recovery_of_possession, etc.)
- **LKB conditional resolver** — `resolve_entry()` flattens `_type: "conditional"` fields using keyword inference
- **Anti-hallucination in LKB brief** — instructs draft LLM to use RAG text, not training memory
- **Intake prompt updated** — added `recovery_of_possession`, `eviction` to cause_type list

---

## 13. Running Tests

```bash
# Run pipeline
agent_steer/Scripts/python.exe research/run_draft_live.py

# Unit tests
agent_steer/Scripts/python.exe -m pytest tests/drafting/ -v

# Review benchmark
agent_steer/Scripts/python.exe research/run_review_benchmark.py
```
