# SKILL: draft-reviewer

## Purpose
Build and maintain the review node (Stage 4). Review validates draft quality and optionally applies inline fixes. Uses slim payload — only draft text + gate errors + user request.

## When to Use
- Building or modifying the review node
- Tuning the review prompt or skip conditions
- Debugging review output quality
- Changing review model assignment

## Architecture Context (v5.1 — what's running)

Review runs after 4 deterministic gates. It receives a slim payload (~3.5K tokens) and performs structured validation + optional inline fix.

```
Stage 3 gates (evidence_anchoring -> lkb_compliance -> postprocess -> citation_validator)
  -> REVIEW (slim payload: draft text + gate errors + user request)
  -> Phase 1: 7 conditional checks
  -> Phase 2: inline fix (if blocking issues found)
  -> END
```

### Skip Review
Set `DRAFTING_SKIP_REVIEW=True` in .env to bypass review entirely (for speed testing).

### Model
- **glm-5:cloud** with reasoning=ON, temperature=0.3
- ~40-70s when triggered
- Fallback: glm-4.6:cloud -> OpenAI (REVIEW_LLM_MODEL)

---

## Slim Payload (what review receives)

Review receives ONLY:
- **Draft text** (~3K tokens) — plain text extracted from `draft.draft_artifacts[0].text`
- **Gate errors summary** (~200 tokens) — compact, from `_build_gate_errors_summary()`
- **User request** (~200 tokens) — for fact fabrication check
- **doc_type + law_domain** (~10 tokens)

**Total: ~3.5K tokens** (was ~15K before pruning)

NOT sent: RAG chunks, court fee context, legal research context, cited chunk IDs.
Gates already verified all of that deterministically.

---

## Review User Prompt

```
Review the generated draft for legal correctness and filing readiness.

USER_REQUEST:
{user_request}

DOC_TYPE: {doc_type}
LAW_DOMAIN: {law_domain}

GATE ERRORS (from deterministic validation gates — already verified):
{gate_errors}

DRAFT TEXT:
{draft_text}
```

---

## Gate Errors Summary Builder

`_build_gate_errors_summary(state)` collects errors from 3 sources:
1. `evidence_anchoring_issues` — fact tracing issues
2. `postprocess_issues` — formatting + LKB compliance issues
3. `citation_issues` — provision verification issues

If no issues: returns "No gate errors — all deterministic checks passed."

---

## Review System Prompt (7 conditional checks)

The review system prompt (`prompts/review.py`) includes:
1. Factual accuracy (every claim traces to intake)
2. Legal theory validity
3. Citation correctness
4. Procedural compliance
5. Section completeness
6. Relief completeness
7. Cross-section consistency

Output: structured JSON with `review_pass`, `blocking_issues`, `non_blocking_issues`, `final_artifacts`

---

## Inline Fix (Phase 2)

When `DRAFTING_REVIEW_INLINE_FIX=True` (default), review generates a corrected `final_artifacts[]` alongside `blocking_issues[]`. This eliminates the separate pass-2 LLM call.

After inline fix, `_fix_and_or()` is applied (deterministic cleanup since LLM may reintroduce anti-patterns).

---

## Routing After Review

```python
def _route_after_review(result, review_count, state, elapsed, inline_fix_enabled):
    # Priority:
    # 1. No legal blocking issues -> END (promote pass-1)
    # 2. Legal issues + inline fix -> END (use corrected artifacts)
    # 3. Legal issues + no fix + within cycles -> draft_freetext (pass-2)
    # 4. Max cycles exceeded -> END regardless
```

- `severity="legal"` — wrong citation, missing section, wrong limitation
- `severity="formatting"` — numbering, heading style, annexure labels
- Formatting-only issues -> END (no pass-2 needed)

---

## Key Files

| File | What |
|------|------|
| `nodes/reviews.py` | Review node + routing + slim payload builder |
| `prompts/review.py` | System/user prompt (7 checks + Phase 2 suffix) |
| `states/draftGraph.py` | `ReviewNode` Pydantic model |

---

## Settings

```
DRAFTING_MAX_REVIEW_CYCLES: int = 1
DRAFTING_REVIEW_INLINE_FIX: bool = True
DRAFTING_SKIP_REVIEW: bool = False
OLLAMA_REVIEW_MODEL: str = "glm-5:cloud"
OLLAMA_REVIEW_TEMPERATURE: float = 0.3
OLLAMA_REVIEW_REASONING: bool = True
REVIEW_LLM_MODEL: Optional[str] = None  # OpenAI fallback
REVIEW_REASONING_EFFORT: Optional[str] = "medium"
```

---

## Retry Strategy (3 attempts)

1. **Attempt 1** — structured output via `with_structured_output(ReviewNode)`
2. **Attempt 2** — structured output with retry suffix prompt
3. **Attempt 3** — raw model call + `extract_json_from_text()` parsing

All 3 fail -> fallback result with `review_pass=False` + error logged, pipeline continues.

---

## Rules
- Review receives ONLY slim payload — never full RAG/court_fee/legal_research
- Max 1 review cycle (setting: `DRAFTING_MAX_REVIEW_CYCLES`)
- Inline fix preferred over pass-2 re-draft (saves 1 LLM call)
- Gate errors provided to review to avoid duplicate flagging
- Token usage logged for cost tracking

## Anti-Patterns
- Do NOT dump RAG chunks, court fee, or legal research into review prompt
- Do NOT send full JSON artifacts — extract plain text only
- Do NOT let review duplicate gate findings (gate report provided)
- Do NOT accept vague issues like "improve the facts section"
- Do NOT flag placeholder usage as an issue
- Do NOT block pipeline if review fails — deliver with gates-only quality
