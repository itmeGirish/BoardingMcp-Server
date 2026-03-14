# SKILL: v9-architecture

Use when: planning, building, or reviewing v11.0 architecture components (LKB 2-layer model, document schemas, structured prompt builder, gates, family migrations).

## v11.0 Architecture — Scalable Context-Driven Pipeline

### Core Principles
1. **Better context to LLM = better draft** — no complex engine needed
2. **Separate law from structure** — cause type (92) × document type (12) = 1,104 combinations
3. **Decide law before drafting, enforce law after drafting**

### The Root Problem
`_build_lkb_brief_context()` dumps 13 instruction categories as flat text at equal priority (~400 lines).
LLM ignores half, hallucinates the rest. This is why drafts have thin facts, missing sections, wrong citations.

### The Solution: LKB 2-Layer + Document Schemas → Structured Prompt

```
LKB Layer 1 (legal knowledge)  +  LKB Layer 2 (document components)  +  Document Schema
            ↓                              ↓                                    ↓
         COMBINE into ONE structured prompt with clear hierarchy
            ↓
         LLM drafts complete document (1 call)
            ↓
         Gates validate (0 LLM)
```

### LKB 2-Layer Model

| Layer | Fields | Goes To |
|-------|--------|---------|
| Layer 1: Legal Knowledge | `primary_acts`, `limitation`, `facts_must_cover`, `mandatory_averments`, `defensive_points`, `drafting_red_flags`, `coa_guidance` | LLM prompt (guidance) |
| Layer 2: Document Components | `available_reliefs` (with `prayer_text`), `jurisdiction_basis`, `valuation_basis`, `legal_basis_text` | LLM prompt (structured data) |

### Document Schemas (12 schemas)

```
Trial court:  plaint, written_statement, rejoinder, counter_claim
Applications: interim_application, condonation_of_delay, set_aside_ex_parte, caveat
Appellate:    appeal_memo, revision_petition, review_petition
Post-decree:  execution_application
```

Each schema defines: section order, per-section instructions, filed_by, annexure_prefix, verification_type, filing_rules.

### Structured Prompt (replaces flat dump)

```
═══ DOCUMENT STRUCTURE (follow this section order exactly) ═══
[from document schema]

═══ LEGAL DATA (cite ONLY from this) ═══
[from LKB Layer 1 + Layer 2]

═══ FACTS GUIDANCE ═══
[from LKB facts_must_cover + red_flags]

═══ CLIENT FACTS ═══
[from user intake]
```

~1,500 tokens. Clear hierarchy. 3 sections, not 13.

### Pipeline (v11.0)

```
intake_classify (cause_type + document_type)
  → enrichment (LKB + document schema)
  → draft (structured prompt → LLM → complete document)
  → gates (evidence_anchoring, lkb_compliance, postprocess, citation_validator)
  → review (optional)
  → END
```

### Scaling

```
New cause type:     1 LKB entry → works with ALL 12 doc types
New document type:  1 schema → works with ALL 92 cause types
New domain:         N LKB entries + reuse schemas → 0 code changes
```

### What Stays From v5.1/v9.0
- All verification gates (7 structural + semantic, zero LLM)
- All applicability compilers (5 families)
- All consistency gates (7 families, 50+ checks)
- Pipeline structure (intake → enrich → draft → gates → review)
- 2 LLM calls (intake + draft), review optional

### Migration Path
1. Enrich LKB with Layer 2 (`available_reliefs` with `prayer_text`, `jurisdiction_basis`)
2. Create 3 schemas (plaint, written_statement, interim_application)
3. Rewrite prompt builder (~100 lines replaces 400-line `_build_lkb_brief_context`)
4. Add `document_type` to intake classification
5. Add remaining 9 schemas
6. Remove old engine.py (-2400 lines)

### Civil Plugin — Families (unchanged)

| Family | Status |
|--------|--------|
| Possession | **Done** (resolver, compiler, gate) |
| Injunction/Declaration | **Done** |
| Contract/Commercial | **Done** |
| Money/Debt | **Done** |
| Partition/Co-ownership | **Done** |
| Tenancy/Rent | **Done** |
| Tort/Civil Wrong | **Done** |
| Business/Fiduciary | Pending |
| Succession/Estate | Pending |

### Key Files
- Draft prompt (to rewrite): `nodes/draft_single_call.py` (`_build_lkb_brief_context`)
- Template engine (to remove): `templates/engine.py`
- LKB: `lkb/causes/` (16 sub-group files, 92 entries)
- LKB helpers: `lkb/causes/_helpers.py` (`_entry()` schema)
- Schemas (NEW): `schemas/` directory
- Civil decision: `nodes/civil_decision.py`
- States: `states/draftGraph.py`

### Rules
- Do NOT dump flat text to LLM — use structured prompt with hierarchy
- Do NOT mix law data with document structure — Layer 1 and Layer 2 are separate concerns
- Do NOT build per-cause-type engine builders — LLM drafts from structured prompt
- Do NOT add per-document-type hardcoded logic — schema drives structure
- Do NOT let LLM decide legal track — applicability compiler decides
- Do NOT add LLM calls for deterministic tasks
- LKB data correctness is THE critical requirement — wrong data = wrong draft
- Document schema correctness is critical — wrong structure = court rejects
