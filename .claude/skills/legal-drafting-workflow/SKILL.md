# SKILL: legal-drafting-workflow

## Purpose
Execution guide for the v5.1 drafting pipeline. Use this when running, testing, debugging, or extending the pipeline.

## Architecture Reference
- CLAUDE.md: `.claude/CLAUDE.md` (concise reference — reflects what's running)
- Target architecture: `docs/architecture_drafting_agent_v8.4.md` (future)

---

## How to Run

### Run single draft
```bash
agent_steer/Scripts/python.exe research/run_draft_live.py
```

### Unit tests
```bash
agent_steer/Scripts/python.exe -m pytest tests/drafting/ -v
```

### Review model benchmark
```bash
agent_steer/Scripts/python.exe research/run_review_benchmark.py
```

---

## Pipeline Flow (v5.1 — what's running)

```
STAGE 1: CONTEXT GATHERING (~12-15s, 1 LLM call)
  intake_classify (qwen3.5:cloud)
    -> rag (4 Qdrant queries, top-8 per query, dedup to ~30)
    -> enrichment (limitation + provisions + LKB lookup + court_fee parallel)

STAGE 2: FREE-TEXT DRAFTING (~30-50s, 1 LLM call)
  draft_freetext (glm-5:cloud, reasoning=True)
    Exemplar-guided, LKB-informed, outputs complete court-ready document

STAGE 3: DETERMINISTIC VALIDATION (~0.1s, zero LLM)
  evidence_anchoring -> lkb_compliance -> postprocess -> citation_validator

STAGE 4: REVIEW (~40-70s, 1 LLM call — slim payload)
  review (glm-5:cloud, reasoning=True)
    Slim context: draft text + gate errors + user request (~5K tokens total)
    Phase 1: all checks | Phase 2: inline fix -> END
```

---

## Key Files to Edit

### To change draft quality
1. `prompts/draft_prompt.py` — system/user prompt + exemplar loading
2. `exemplars/` — structural exemplars per cause type
3. `nodes/draft_single_call.py` — `draft_freetext_node` + context builders
4. `lkb/civil.py` — LKB entries (acts, limitation, doctrines, terminology)

### To change review behavior
1. `prompts/review.py` — review system prompt (7 conditional checks)
2. `nodes/reviews.py` — slim payload builder + routing logic
3. Settings: `DRAFTING_REVIEW_INLINE_FIX`, `DRAFTING_MAX_REVIEW_CYCLES`

### To add a new cause type
1. `lkb/civil.py` — add entry with primary_acts, limitation, permitted_doctrines, doc_type_keywords
2. `lkb/__init__.py` — add aliases in `_CAUSE_TYPE_ALIASES` if needed
3. `prompts/intake_classify.py` — add to common cause_type values list
4. Optionally add exemplar in `exemplars/`

### To change models
1. `app/config/settings.py` — `OLLAMA_DRAFT_MODEL`, `OLLAMA_REVIEW_MODEL`, etc.
2. Or override in `.env` file

### To change validation gates
1. `nodes/evidence_anchoring.py` — fact -> intake tracing
2. `nodes/lkb_compliance.py` — act citation + superseded law check
3. `nodes/postprocess.py` — formatting fixes
4. `nodes/citation_validator.py` — provision verification

---

## LKB v3.0 Features

### Cause-type aliases (new)
LKB now resolves near-miss cause types via `_CAUSE_TYPE_ALIASES`:
- `property_law` -> `recovery_of_possession`
- `money_recovery` -> `money_recovery_loan`
- `breach_contract` -> `breach_of_contract`
- `eviction_plaint` -> `recovery_of_possession`

### Conditional fields (new)
LKB entries can have `_type: "conditional"` fields that resolve at runtime:
```python
"limitation": {
    "_type": "conditional",
    "_resolve_by": "occupancy_type",
    "_rules": [
        {"when": "tenant_determined", "then": {"article": "67", ...}},
        {"when": "trespasser", "then": {"article": "65", ...}},
    ],
    "_default": {"article": "67", ...}
}
```
Resolved by `resolve_entry(entry, user_request_text)` using keyword inference.

---

## Debug Checklist

When a draft scores below target:

1. **Check intake** — did it classify cause_type correctly? Check `[INTAKE+CLASSIFY]` log
2. **Check LKB** — did lookup succeed? Watch for `[LKB] miss` in logs. Check aliases
3. **Check enrichment** — did limitation resolve? Check `[ENRICHMENT]` log for article selected
4. **Check conditional resolution** — did `resolve_entry` flatten conditionals? Check `[LKB] conditional` logs
5. **Check draft prompt** — is LKB brief reaching the draft? Check `_build_lkb_brief_context`
6. **Check RAG** — are relevant chunks being retrieved? Check `[RAG]` query terms
7. **Check gates** — are there false positives? Check `[EVIDENCE_ANCHORING]`, `[LKB_COMPLIANCE]`, `[CITATION_VALIDATOR]`
8. **Check review** — did review fix or break things? Check `[REVIEW]` blocking_issues

### Common issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| 35 placeholders | LKB miss -> no acts/limitation fed to draft | Add alias or fix cause_type in intake prompt |
| Wrong limitation article | Conditional field not resolved | Check `resolve_entry` + `_INFERENCE_MAP` keywords |
| Hallucinated section content | LLM uses training memory not RAG | Check anti-hallucination instruction in LKB brief builder |
| Review too slow | Too many tokens sent | Already fixed — slim payload (~5K tokens) |
| Citation flagged incorrectly | Provision not in verified_provisions | Check enrichment RAG scan + user_cited_provisions |
| Wrong model used | Settings override in .env | Check `OLLAMA_DRAFT_MODEL` / `OLLAMA_REVIEW_MODEL` |

---

## Review Slim Payload

Review receives ONLY:
- Draft text (plain text, ~3K tokens)
- Gate errors summary (compact, ~200 tokens)
- User request (~200 tokens)
- doc_type + law_domain (~10 tokens)

NOT sent: RAG chunks, court fee context, legal research context, cited IDs.
Gates already verified all of that deterministically.
