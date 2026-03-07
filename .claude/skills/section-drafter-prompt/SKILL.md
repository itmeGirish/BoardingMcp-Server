# SKILL: draft-prompt

## Purpose
Build and refine the draft prompt that produces a complete court-ready legal document in a single LLM call. v5.1 uses free-text drafting — the LLM outputs the entire document (not section-keyed JSON, not gap-fill). Exemplar-guided, LKB-informed.

## When to Use
- Building or modifying `prompts/draft_prompt.py`
- Debugging why draft quality is low
- Tuning exemplars or context injection
- Adapting prompt for a new cause type
- Optimizing prompt token count

## Architecture Context (v5.1 — what's running)

Single LLM call produces the complete document. No templates, no section keys, no gap-fill markers.

```
intake_classify -> rag -> enrichment -> draft_freetext_node -> 4 gates -> review
```

Model: **glm-5:cloud** with reasoning=ON, temperature=0.7, ~30-50s

---

## System Prompt Structure

`build_draft_freetext_system_prompt(doc_type, cause_type)` builds:

1. **Role** — "senior Indian litigation lawyer, 25 years practice"
2. **Exemplar** — loaded via `load_exemplar(doc_type)` (~1,500 tokens)
3. **LKB quality rules** — Q1-Q10, COA rules, relief rules (from LKB entry)
4. **Substantive rules** — R1-R16 (anti-hallucination, citation, formatting)
5. **Output instruction** — "Write the COMPLETE document as it would appear when filed in court"

Key instruction: plain text output, not JSON, not markdown code blocks.

---

## User Prompt Structure

`build_draft_freetext_user_prompt(...)` includes (in order):

1. **User request** (facts FIRST — lost-in-middle principle)
2. **Extracted facts summary** from intake
3. **Parties context**
4. **Evidence context**
5. **Limitation context** — from `_build_limitation_context()`
6. **Verified provisions** — from `_build_verified_provisions_context()`
7. **LKB brief** — from `_build_lkb_brief_context()` (acts, limitation, terminology)
8. **RAG context** — from `_build_rag_context()` (top chunks, deduped)

---

## Context Builders (in draft_single_call.py)

| Builder | What it provides |
|---------|-----------------|
| `_build_limitation_context()` | Limitation article, period, description. Handles `article == "NONE"` |
| `_build_verified_provisions_context()` | List of verified statutory provisions from enrichment |
| `_build_rag_context()` | Top RAG chunks from Qdrant, deduped, scored |
| `_build_lkb_brief_context()` | Primary acts, limitation summary, terminology, anti-hallucination instruction |
| `_build_procedural_requirements_context()` | Court rules, procedural requirements from LKB |

---

## LKB Brief Builder

`_build_lkb_brief_context()` feeds verified legal knowledge to the draft LLM:
- Primary acts with sections
- Alternative acts
- Limitation article + period (or "NO LIMITATION APPLIES" when article=NONE)
- Terminology mapping (conditional, resolved at runtime)
- Anti-hallucination instruction: "Use RAG text, not training memory"

---

## Exemplars

Structural exemplars per cause type in `exemplars/` directory (~1,500 tokens each):
- Show document structure, section order, heading style
- Use generic placeholders, not specific facts
- Guide LLM on Indian legal drafting conventions

To add a new exemplar:
1. Create file in `exemplars/` matching cause type name
2. `load_exemplar(doc_type)` auto-discovers by naming convention
3. Exemplar included in system prompt

---

## Draft Node Flow (draft_single_call.py)

`draft_freetext_node(state)`:
1. Build system prompt (exemplar + LKB + rules)
2. Build user prompt (facts + context)
3. Single LLM call -> raw text output
4. Strip markdown fences if present (defensive)
5. Clean encoding artifacts
6. Append advocate block if absent
7. Collect placeholders
8. Wrap in `DraftArtifact` -> `draft.draft_artifacts[0]`
9. Route to `evidence_anchoring` gate

---

## Key Files

| File | What |
|------|------|
| `prompts/draft_prompt.py` | System/user prompt builders + exemplar loading |
| `nodes/draft_single_call.py` | `draft_freetext_node` + all context builders |
| `exemplars/` | Structural exemplars per cause type |
| `lkb/civil.py` | LKB entries feeding the brief |

---

## Rules
- User facts go FIRST in user prompt (lost-in-middle: LLMs attend best to start/end)
- Only cite VERIFIED PROVISIONS — enrichment provides the list
- Exemplar guides structure, LKB guides substance
- Plain text output — no JSON, no markdown code blocks
- Max 5 system instruction rules (Few-Shot > Exhaustive Rules)
- Strip markdown fences defensively (LLM sometimes wraps)
- Handle `limitation.article == "NONE"` explicitly

## Anti-Patterns
- Do NOT use JSON section-key output format
- Do NOT add must_include checklists in prompt
- Do NOT add per-scenario instructions (if partition do X, if money do Y)
- Do NOT dump all RAG chunks raw — use context builders to filter/score
- Do NOT constrain legal reasoning ("must cite Section 65")
- Do NOT hardcode legal content in Python — LKB + RAG + exemplar handles it
- Do NOT exceed prompt budget unnecessarily — compression matters for speed
