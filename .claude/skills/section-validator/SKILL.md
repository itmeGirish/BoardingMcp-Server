# SKILL: section-validator

## Purpose
Build and maintain the 4 deterministic verification gates (Stage 3). Gates run on the full draft text with zero LLM calls. They validate, auto-fix formatting, and flag issues for review.

## When to Use
- Building or modifying any gate
- Adding new entity extraction patterns
- Debugging false positives / false negatives
- Extending verified provisions coverage

## Architecture Context (v5.1 — what's running)

4 gates run sequentially on `draft.draft_artifacts[0].text` (full document text). Total time: ~0.1s.

```
draft_freetext -> evidence_anchoring -> lkb_compliance -> postprocess -> citation_validator -> review
```

All gates are deterministic — zero LLM calls.

---

## Gate 1: Evidence Anchoring (`evidence_anchoring.py`)

For each extracted entity (date, amount, reference) in the draft:
1. Check if exists in intake facts, evidence, or user_request
2. If YES -> keep as-is
3. If NO -> replace token with `{{PLACEHOLDER}}`

### Entity Parsers
- **Date parser**: handles 15.03.2024, 15/03/2024, 15th March 2024, etc. Excludes Section/Article/Order numbers
- **Amount parser**: handles Rs. 20,00,000/-, INR 20 lakh, Rupees Twenty Lakhs. Indian comma notation. Excludes years/days/percentages
- **Reference parser**: cheque no., UTR, NEFT Ref — keyword-aware

### Output
- `evidence_anchoring_issues` — list of dicts with `type` and `description`
- Modified draft text with unsupported tokens replaced

---

## Gate 2: LKB Compliance (`lkb_compliance.py`)

Checks draft against LKB entry for the classified cause type:
1. **Primary acts cited** — are the LKB primary_acts referenced in draft?
2. **Superseded law check** — auto-replaces old acts with current (e.g., IPC -> BNS, CrPC -> BNSS)

### Auto-Fix
- Superseded law references auto-replaced (deterministic substitution)
- Missing primary acts -> flagged as issue for review

### Output
- Issues merged into `postprocess_issues`

---

## Gate 3: Postprocess (`postprocess.py`)

Deterministic formatting fixes on the draft text:
1. **Paragraph numbering** — fix sequential numbering gaps
2. **Annexure labels** — ensure Annexure A, B, C format
3. **Verification clause** — ensure Order VI Rule 15 CPC clause present
4. **Spacing** — normalize whitespace, line breaks
5. **and/or fix** — replace "and/or" with "and" (Indian legal convention)
6. **Paragraph breaks** — split run-together numbered paragraphs
7. **Annexure list** — split semicolon-separated items
8. **Prayer items** — ensure prayer sub-items on separate lines

### Output
- `postprocess_issues` — list of formatting fixes applied
- Modified draft text with all fixes applied

---

## Gate 4: Citation Validator (`citation_validator.py`)

Every statutory citation in the draft must:
1. Exist in `verified_provisions` (from enrichment) OR be a well-known procedural provision
2. Not be a fabricated case citation (AIR/SCC/ILR)

### Case Citation Patterns (flagged as ERROR)
- `(2015) 5 SCC 123`
- `AIR 2015 SC 123`
- `2015 SCC OnLine SC 123`
- `ILR 2015 KAR 123`

### Well-Known Provisions (always allowed)
- CPC: Section 26, Order VI Rule 15, Order VII Rule 1, Section 34, Section 151
- Constitution: Article 14, 19, 21, 226, 32
- Evidence Act: Section 65B

### Output
- `citation_issues` — list of dicts with `severity` and `message`
- Enabled/disabled via `DRAFTING_CITATION_VALIDATOR_ENABLED` setting

---

## Key Files

| File | What |
|------|------|
| `nodes/evidence_anchoring.py` | Gate 1: fact -> intake tracing |
| `nodes/lkb_compliance.py` | Gate 2: act citation + superseded law check |
| `nodes/postprocess.py` | Gate 3: formatting fixes |
| `nodes/citation_validator.py` | Gate 4: provision verification |
| `nodes/_utils.py` | Shared helpers (placeholder collection, encoding cleanup) |

---

## Settings

```
DRAFTING_CITATION_VALIDATOR_ENABLED: bool = True
```

---

## Rules
- NEVER modify legal substance — only replace unsupported tokens or flag claims
- NEVER remove sentences — only flag them
- Entity extraction must be deterministic (no LLM)
- Gates run on full document text (`draft.draft_artifacts[0].text`)
- False positives are better than false negatives
- All gates run regardless of individual failures (graceful degradation)
- Gate issues are summarized for review via `_build_gate_errors_summary()`

## Anti-Patterns
- Do NOT use LLM for any gate — deterministic only
- Do NOT block pipeline on gate warnings — flag and continue
- Do NOT auto-remove flagged citations — let review handle
- Do NOT flag placeholder usage as an issue
- Do NOT auto-fix substantive legal content — only formatting
