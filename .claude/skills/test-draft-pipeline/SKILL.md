# SKILL: test-draft-pipeline

## Purpose
Run the drafting pipeline, evaluate output quality, and verify all 4 gates + review work correctly.

## When to Use
- After modifying any pipeline node, gate, or prompt
- After creating or updating an exemplar or LKB entry
- For regression testing across multiple scenarios
- For debugging pipeline failures

## Test Runners

### Quick Test (single scenario)
```bash
agent_steer/Scripts/python.exe research/run_draft_live.py
```

### Unit Tests
```bash
agent_steer/Scripts/python.exe -m pytest tests/drafting/ -v
```

### Review Benchmark
```bash
agent_steer/Scripts/python.exe research/run_review_benchmark.py
```

### Multi-Scenario Compare
```bash
agent_steer/Scripts/python.exe research/run_v5_compare.py
```

---

## What to Check in Logs

```
[INTAKE+CLASSIFY] -> doc_type, law_domain, cause_type, facts extracted, parties
[RAG]             -> query terms, chunks retrieved, dedup count
[ENRICHMENT]      -> limitation article, verified_provisions count, LKB hit/miss
[LKB]             -> hit/miss/alias resolution, conditional field resolution
[DRAFT]           -> model used, prompt size, output chars, placeholders found
[EVIDENCE_ANCHORING] -> entities found, anchored, replaced with placeholder
[LKB_COMPLIANCE]     -> primary acts check, superseded law replacements
[POSTPROCESS]        -> formatting fixes applied
[CITATION_VALIDATOR] -> provisions verified, flagged, case citations found
[REVIEW]           -> skipped? cycle count, blocking_issues, inline fix, token usage
```

---

## Scoring Framework

### Universal Checks (ALL doc_types)

| # | Check | What to verify |
|---|---|---|
| 1 | Court heading present | Court name + place |
| 2 | Title present | Document type stated |
| 3 | Parties section | Primary + opposite party |
| 4 | Jurisdiction section | Territorial + pecuniary + subject matter |
| 5 | Facts section | Numbered paragraphs, chronological |
| 6 | Legal basis section | At least one statutory provision |
| 7 | Prayer section | Specific relief(s) requested |
| 8 | Verification clause | Order VI Rule 15 for CPC |
| 9 | Continuous numbering | Paragraphs numbered sequentially |
| 10 | No fabricated citations | Zero AIR/SCC/ILR unless user-provided |
| 11 | Proper placeholders | `{{NAME}}` format for unknowns |
| 12 | Evidence referenced | Annexure labels used |
| 13 | Formal language | Court-ready register |

### Pipeline-Specific Checks

| # | Check | What to verify |
|---|---|---|
| 14 | LKB resolved | cause_type matched (direct or via alias) |
| 15 | Primary acts cited | LKB primary_acts appear in draft |
| 16 | Limitation correct | Matches LKB (or NONE when appropriate) |
| 17 | No superseded acts | IPC/CrPC/Evidence Act replaced with BNS/BNSS/BSA |
| 18 | Citation validator clean | No unverified provisions flagged |
| 19 | Evidence anchoring clean | No unsupported tokens remain |
| 20 | Review routing correct | Legal vs formatting severity handled properly |

---

## Debug Checklist

When a draft scores below target:

1. **Check intake** — did it classify cause_type correctly? Check `[INTAKE+CLASSIFY]` log
2. **Check LKB** — did lookup succeed? Watch for `[LKB] miss` in logs. Check aliases
3. **Check enrichment** — did limitation resolve? Check `[ENRICHMENT]` log
4. **Check conditional resolution** — did `resolve_entry` flatten conditionals? Check `[LKB] conditional`
5. **Check draft prompt** — is LKB brief reaching the draft? Check `_build_lkb_brief_context`
6. **Check RAG** — are relevant chunks retrieved? Check `[RAG]` query terms
7. **Check gates** — are there false positives? Check each gate's log output
8. **Check review** — did review fix or break things? Check `[REVIEW]` blocking_issues

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| 35 placeholders | LKB miss -> no acts/limitation fed to draft | Add alias in `lkb/__init__.py` or fix cause_type in intake prompt |
| Wrong limitation article | Conditional field not resolved | Check `resolve_entry` + `_INFERENCE_MAP` keywords |
| Hallucinated section content | LLM uses training memory not RAG | Check anti-hallucination instruction in LKB brief builder |
| Review too slow | Too many tokens sent | Already fixed — slim payload (~3.5K tokens) |
| Citation flagged incorrectly | Provision not in verified_provisions | Check enrichment RAG scan + user_cited_provisions |
| Wrong model used | Settings override in .env | Check `OLLAMA_DRAFT_MODEL` / `OLLAMA_REVIEW_MODEL` |
| Superseded act in draft | LKB compliance gate missed | Check superseded law patterns in `lkb_compliance.py` |

---

## Hallucination Tests

| Test | Input | Verify | Fail if |
|------|-------|--------|---------|
| Date hallucination | No dates provided | All dates `{{PLACEHOLDER}}` | Concrete date fabricated |
| Amount hallucination | Only principal amount | Principal matches exactly | Unrelated amount in draft |
| Citation hallucination | No case law request | Zero AIR/SCC/ILR | Case citation in draft |
| Name hallucination | No specific names | All names `{{PLACEHOLDER}}` | Invented name in draft |
| Statute hallucination | Check cited provisions | In verified_provisions | Unverified citation not flagged |

---

## Regression Testing

After ANY change, run scenarios covering:
1. **Money recovery** — formulaic, should score high
2. **Breach of contract** — standard complexity
3. **Dealership damages** — complex, multiple damage heads
4. **Partition** — complex, genealogy + property schedule
5. **Recovery of possession** — tests LKB alias resolution
6. **Defamation** — tests cause-type matching

Check:
- No quality regression (gate issues count, placeholder count)
- No timing regression (within expected bounds)
- No new false positives in gates
- LKB resolution succeeds for all cause types

---

## Telemetry to Log
- Total pipeline duration + per-stage breakdown
- Model used + estimated tokens (input/output)
- LKB hit/miss/alias
- Gate results (per gate: pass/fail/fixes)
- Review: skipped/triggered, blocking issues, inline fix applied
- Placeholder count in final output
- Draft text length (chars)
