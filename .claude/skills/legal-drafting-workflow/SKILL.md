# SKILL: legal-drafting-workflow

## Purpose
Execution guide for the drafting pipeline. v5.1 is running. v11.0 is target.

## Architecture Reference
- CLAUDE.md: `.claude/CLAUDE.md` (v11.0 target architecture)
- Skills: `/v9-architecture`, `/schema-builder`, `/lkb-enrichment`, `/prompt-builder`

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

### Benchmark (10 scenarios)
```bash
agent_steer/Scripts/python.exe research/run_draft_benchmark.py --draft
agent_steer/Scripts/python.exe research/run_draft_benchmark.py --compare
```

---

## Pipeline Flow (v5.1 — what's running)

```
STAGE 1: CONTEXT GATHERING (~12-15s, 1 LLM call)
  intake_classify (qwen3.5:cloud)
    -> domain_router -> enrichment (LKB lookup, 0 LLM, 0 API)

STAGE 2: FREE-TEXT DRAFTING (~30-50s, 1 LLM call)
  draft_freetext (qwen3.5:cloud, reasoning=True)
    LKB-guided, outputs complete court-ready document

STAGE 3: DETERMINISTIC VALIDATION (~0.1s, zero LLM)
  evidence_anchoring -> lkb_compliance -> postprocess -> citation_validator

STAGE 4: REVIEW (~40-70s, 1 LLM call — slim payload, optional)
  review (OpenAI gpt-5.2)
    Slim context: draft text + gate errors + user request (~7K tokens)
```

## Pipeline Flow (v11.0 — target)

```
STAGE 1: CONTEXT GATHERING (~12-15s, 1 LLM call)
  intake_classify (cause_type + document_type)
    -> domain_router -> enrichment (LKB + document schema)

STAGE 2: DRAFTING (~30-50s, 1 LLM call)
  draft (structured prompt: schema + LKB Layer 1 + Layer 2 + facts)
    LLM drafts complete document from structured context

STAGE 3: DETERMINISTIC VALIDATION (~0.1s, zero LLM)
  evidence_anchoring -> lkb_compliance -> postprocess -> citation_validator

STAGE 4: REVIEW (optional)
  review (OpenAI gpt-5.2)
```

---

## Key Files

### To change draft quality (v11.0 approach)
1. `lkb/causes/*.py` — LKB entries Layer 1 + Layer 2 (legal data + document components)
2. `schemas/*.py` — document schemas (section order + instructions)
3. `prompts/draft_prompt.py` — structured prompt builder
4. `nodes/draft_single_call.py` — `_build_lkb_brief_context()` (to be replaced by prompt builder)

### To add a new cause type
1. `lkb/causes/{file}.py` — add entry with Layer 1 + Layer 2 fields
2. `lkb/__init__.py` — add aliases if needed
3. Done. Works with ALL 12 document types automatically.

### To add a new document type
1. `schemas/{file}.py` — add schema with section order + instructions
2. Done. Works with ALL 92 cause types automatically.

### To change models
1. `app/config/settings.py` — `OLLAMA_DRAFT_MODEL`, `OLLAMA_REVIEW_MODEL`
2. Review: now OpenAI gpt-5.2 (changed 2026-03-14)

### To change validation gates
1. `nodes/evidence_anchoring.py` — fact → intake tracing
2. `nodes/lkb_compliance.py` — act citation + superseded law
3. `nodes/postprocess.py` — formatting
4. `nodes/citation_validator.py` — provision verification
5. `nodes/civil_decision.py` — family consistency gates (7 families)

---

## Debug Checklist

When a draft scores below target:

1. **Check intake** — did it classify cause_type correctly? Check `[INTAKE+CLASSIFY]` log
2. **Check LKB** — did lookup succeed? Watch for `[LKB] miss`. Check aliases
3. **Check enrichment** — did limitation resolve? Check `[ENRICHMENT]` log
4. **Check prompt** — is LKB data reaching draft LLM? Check `_build_lkb_brief_context` output
5. **Check gates** — false positives? Check gate logs
6. **Check review** — did review fix or break? Check `[REVIEW]` blocking_issues

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Thin facts | Missing `facts_must_cover` in LKB | Add to LKB entry |
| Missing sections | LLM decides structure | Add document schema (v11.0) |
| Wrong limitation | Wrong article in LKB | Fix LKB entry, verify against Limitation Act |
| Wrong prayer | Missing `available_reliefs` | Add Layer 2 data to LKB |
| Fabricated citations | LLM hallucinated | Check `verified_provisions` in enrichment |
| Facts cite statutes | No anti-constraint | Add "Do NOT cite sections in FACTS" to red_flags |

---

## v11.0 Migration Status

| Phase | What | Status |
|-------|------|--------|
| 1 | Enrich LKB with Layer 2 | Pending |
| 2 | Create 3 schemas (plaint, WS, interim app) | Pending |
| 3 | Rewrite prompt builder | Pending |
| 4 | Add document_type to intake | Pending |
| 5 | Add remaining 9 schemas | Pending |
| 6 | Remove engine.py | Pending |
