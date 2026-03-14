# SKILL: exemplar-builder

## Purpose
Create, validate, and maintain document schemas and LKB Layer 2 data for the v11.0 scalable drafting pipeline.

**v11.0 approach:** No exemplar documents in prompts. Instead: LKB 2-layer data + document schema → structured prompt → LLM drafts.

## When to Use
- Creating a new document schema (e.g., written_statement, appeal_memo)
- Enriching LKB entries with Layer 2 data (available_reliefs, jurisdiction_basis)
- Reviewing schema quality against CPC rules
- Adding a new document type to the pipeline
- Debugging why draft structure is wrong

## Architecture Context (v11.0)

```
LKB Layer 1 (legal knowledge) + LKB Layer 2 (document components) + Document Schema
  → Structured prompt (3 sections, ~1,500 tokens)
  → LLM drafts complete document (1 call)
  → Gates validate (0 LLM)
```

No template engine. No exemplar files. Just better context to the same LLM.

---

## Document Schema Directory (v11.0)

```
app/agents/drafting_agents/schemas/
├── __init__.py          # DOCUMENT_SCHEMAS registry + lookup
├── trial_court.py       # plaint, written_statement, rejoinder, counter_claim
├── applications.py      # interim_application, condonation, set_aside_ex_parte, caveat
├── appellate.py          # appeal_memo, revision_petition, review_petition
└── execution.py          # execution_application
```

---

## Document Schema Format

Each schema defines structure for ONE document type, independent of cause type:

```python
{
    "code": "written_statement",
    "display_name": "Written Statement",
    "filed_by": "defendant",
    "cpc_reference": "Order VIII",
    "annexure_prefix": "D-",
    "verification_type": "defendant",
    "signing_format": "Defendant through Advocate",

    "sections": [
        {"key": "court_heading",          "instruction": "Court name, place, suit number"},
        {"key": "parties",                "instruction": "Defendant and Plaintiff details"},
        {"key": "preliminary_objections", "instruction": "Limitation, jurisdiction, non-joinder objections"},
        {"key": "parawise_reply",         "instruction": "Reply to EVERY plaint paragraph: ADMITTED/DENIED/NOT ADMITTED"},
        {"key": "additional_facts",       "instruction": "New facts supporting defence, not in plaint"},
        {"key": "legal_grounds",          "instruction": "Statutory and legal basis for defence"},
        {"key": "prayer",                 "instruction": "Dismiss suit with costs"},
        {"key": "verification",           "instruction": "Verification on oath"},
    ],

    "filing_rules": {
        "court_fee": False,
        "filing_deadline": "30 days from service (max 120 days — Order VIII Rule 1)",
        "vakalatnama": True,
    },
}
```

---

## LKB Layer 2 Data Format

Each LKB entry gets document component fields alongside existing legal knowledge:

```python
"breach_of_contract": {
    # Layer 1 — Legal knowledge (already exists)
    "primary_acts": [...],
    "limitation": {...},
    "facts_must_cover": [...],

    # Layer 2 — Document components (NEW)
    "available_reliefs": [
        {"type": "damages", "statute": "S.73 ICA", "prayer_text": "decree for damages of Rs.{{AMOUNT}}"},
        {"type": "interest_pre_suit", "statute": "S.34 CPC", "prayer_text": "interest at {{RATE}}% per annum from {{BREACH_DATE}}"},
        {"type": "interest_pendente_lite", "statute": "Order XX Rule 11 CPC", "prayer_text": "pendente lite and future interest"},
        {"type": "costs", "statute": "S.35 CPC", "prayer_text": "costs of the suit"},
    ],
    "jurisdiction_basis": "Section 20 CPC — where cause of action arose",
    "valuation_basis": "Amount of damages claimed",
}
```

---

## Creating a New Document Schema

1. Identify CPC/statute reference for the document type
2. List all required sections in court-standard order
3. Add per-section instruction (what goes in that section)
4. Set `filed_by`, `annexure_prefix`, `verification_type`
5. Add `filing_rules` (deadline, court fee, etc.)
6. Verify section order against actual court practice
7. Test by running pipeline with the new document type

---

## Enriching LKB with Layer 2

1. For each LKB entry, add `available_reliefs` with `prayer_text`
2. Add `jurisdiction_basis` (which CPC section determines jurisdiction)
3. Add `valuation_basis` (what determines suit valuation/court fee)
4. Verify prayer_text matches actual court prayer format
5. Test by running pipeline — check if prayer output uses exact prayer_text

---

## Key Files

| File | What |
|------|------|
| `schemas/` | Document type schemas (NEW) |
| `lkb/causes/` | LKB entries (enrich with Layer 2) |
| `lkb/causes/_helpers.py` | `_entry()` schema definition |
| `prompts/draft_prompt.py` | Structured prompt builder |
| `nodes/draft_single_call.py` | `_build_lkb_brief_context()` (to be replaced) |

---

## Rules
- Schema defines STRUCTURE — not legal substance (LKB does that)
- One schema per document type (not per cause type)
- Schema is independent of cause type — same schema works for ALL 92 causes
- `available_reliefs.prayer_text` must match actual court prayer wording
- Verify schemas against CPC/statute text — wrong structure = court rejects
- Keep sections in court-standard order for that document type

## Anti-Patterns
- Do NOT create per-cause-type schemas — schema is per document type only
- Do NOT put legal knowledge in schemas — LKB handles that
- Do NOT use exemplar files in prompts — structured data replaces exemplars
- Do NOT hardcode section order in engine.py — schema drives order
- Do NOT mix Layer 1 and Layer 2 fields — keep them conceptually separate
