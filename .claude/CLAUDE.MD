# Legal Drafting Agent — v5.1 (running) | v11.0 (target)

Version: 5.1 (active pipeline) | 11.0 (target architecture)
Runtime: Python 3.11+ | LangGraph | Qdrant | PostgreSQL 14+ | Ollama Cloud
Target: 9.5/10 | 2 LLM calls (clean draft) | Court-ready Indian legal documents

Core principle: **Decide law before drafting, enforce law after drafting.**
Architecture principle: **Better context to LLM = better draft. LKB 2-layer data + document schemas = structured prompt.**
Scaling principle: **Separate law (cause type) from structure (document type). Compose at runtime. 92 + 12 = 1,104 combinations.**

---

## 1. Design Philosophy (9 Principles)

1. **Verify, Don't Hope** — every claim traceable to source or flagged as placeholder
2. **Deterministic > LLM** — formatting, citations, compliance, court fees = deterministic. Only intake, drafting, review use LLM
3. **Decide Law Before Drafting** — applicability compiler decides legal track BEFORE LLM drafts. LLM never decides tenant vs licensee
4. **Generate First, Validate After** — LLM drafts freely, gates validate output
5. **Enforce After Drafting** — semantic gates check theory consistency, red flag violations, prayer completeness AFTER draft
6. **Minimize Cloud Dependency** — 2 LLM calls for clean drafts. Cache aggressively
7. **Graceful Degradation, Never Block** — missing facts -> `{{PLACEHOLDER}}`, enrichment fails -> `UNKNOWN`, model throttled -> fallback chain
8. **Measure Everything** — every document produces structured metrics
9. **Privacy by Default** — PII redacted before cloud calls, de-redacted after gates

When principles conflict, lower-numbered wins.

---

## 2. Target Architecture (v11.0 — Scalable Context-Driven Pipeline)

### 2.1 Core Idea

**Better context to LLM = better draft.** No complex engine needed.

The root problem: current `_build_lkb_brief_context()` dumps 13 instruction categories as flat text
at equal priority (~400 lines). LLM ignores half, hallucinates the rest.

The fix: LKB carries 2 layers of data. Document schemas define structure. Combine into ONE structured
prompt with clear hierarchy. LLM drafts the complete document. Gates validate after.

**Scaling:** Separate law (cause type) from structure (document type). Compose at runtime.
- New cause type = 1 LKB entry → works with ALL document types
- New document type = 1 schema → works with ALL 92 cause types
- 92 cause types + 12 document schemas = 1,104 combinations from 104 entries

### 2.2 LKB 2-Layer Data Model

Each LKB entry carries 2 layers:

| Layer | What It Contains | Goes To |
|-------|-----------------|---------|
| Layer 1: Legal Knowledge | `primary_acts`, `limitation`, `facts_must_cover`, `mandatory_averments`, `defensive_points`, `drafting_red_flags`, `coa_guidance`, `permitted_doctrines` | **LLM prompt** (tells LLM WHAT law to apply) |
| Layer 2: Document Components | `available_reliefs` (with `prayer_text`), `jurisdiction_basis`, `valuation_basis`, `legal_basis_text`, `suit_title_prefix` | **LLM prompt** (tells LLM WHAT structural content to use) |

Both layers go to LLM as structured context. No complex engine builders needed.

```python
# Layer 1 — Legal knowledge (LLM guidance)
"facts_must_cover": ["Date of contract", "Specific breach", "Loss quantification"],
"mandatory_averments": ["Contract existed", "Defendant breached", "Plaintiff suffered loss"],
"drafting_red_flags": ["Do NOT mix S.73/S.74", "Check arbitration clause"],

# Layer 2 — Document components (LLM uses directly)
"available_reliefs": [
    {"type": "damages", "statute": "S.73 ICA", "prayer_text": "decree for damages of Rs.{{AMOUNT}}"},
    {"type": "interest", "statute": "S.34 CPC", "prayer_text": "interest at {{RATE}}% per annum"},
    {"type": "costs", "statute": "S.35 CPC", "prayer_text": "costs of the suit"},
],
"jurisdiction_basis": "Section 20 CPC — where cause of action arose",
"valuation_basis": "Amount of damages claimed",
```

### 2.3 Document Schemas (12 schemas cover ALL civil documents)

Each schema defines section order + per-section instructions. Independent of cause type.

```python
DOCUMENT_SCHEMAS = {
    # Trial court
    "plaint":              {"sections": ["court_heading", "parties", "facts", "legal_basis", "limitation", "jurisdiction", "valuation", "schedule_of_property", "prayer", "verification", "documents_list"], ...},
    "written_statement":   {"sections": ["court_heading", "parties", "preliminary_objections", "parawise_reply", "additional_facts", "legal_grounds", "prayer", "verification"], ...},
    "rejoinder":           {"sections": ["court_heading", "parties", "reply_to_ws", "reaffirmation", "prayer", "verification"], ...},
    "counter_claim":       {"sections": ["court_heading", "parties", "facts", "legal_basis", "limitation", "valuation", "prayer", "verification"], ...},
    "interim_application": {"sections": ["court_heading", "parties", "nature", "facts", "grounds", "urgency", "prayer", "verification"], ...},

    # Post-decree
    "execution_application": {"sections": ["court_heading", "parties", "decree_details", "facts", "execution_mode", "prayer", "verification"], ...},

    # Appellate
    "appeal_memo":         {"sections": ["court_heading", "parties", "impugned_order", "brief_facts", "grounds_of_appeal", "prayer", "verification"], ...},
    "revision_petition":   {"sections": ["court_heading", "parties", "impugned_order", "brief_facts", "jurisdictional_error", "prayer", "verification"], ...},
    "review_petition":     {"sections": ["court_heading", "parties", "impugned_order", "grounds_for_review", "prayer", "verification"], ...},

    # Procedural
    "condonation_of_delay":  {"sections": ["court_heading", "parties", "delay_facts", "sufficient_cause", "prayer", "verification"], ...},
    "set_aside_ex_parte":    {"sections": ["court_heading", "parties", "facts", "sufficient_cause", "meritorious_defence", "prayer", "verification"], ...},
    "caveat":                {"sections": ["court_heading", "parties", "facts", "prayer", "verification"], ...},
}
```

Each schema also carries: `filed_by`, `annexure_prefix` (P-/D-/Annexure-), `verification_type`, `filing_rules`, `cpc_reference`.

### 2.4 Structured Prompt (Replaces Flat Dump)

The prompt builder combines LKB + schema into ONE structured prompt with clear hierarchy:

```python
def build_draft_prompt(lkb_entry, doc_schema, user_facts):
    return f"""
═══ DOCUMENT STRUCTURE (follow this section order exactly) ═══
{format_section_plan(doc_schema)}

═══ LEGAL DATA (cite ONLY from this) ═══
CAUSE: {lkb_entry['display_name']}
STATUTES: {format_acts(lkb_entry['primary_acts'])}
LIMITATION: Art {lkb_entry['limitation']['article']} — {lkb_entry['limitation']['period']}
RELIEFS TO PRAY FOR: {format_reliefs(lkb_entry['available_reliefs'])}

═══ FACTS GUIDANCE ═══
MUST COVER: {format_list(lkb_entry['facts_must_cover'])}
DO NOT: {format_list(lkb_entry['drafting_red_flags'])}

═══ CLIENT FACTS ═══
{user_facts}
"""
```

**~1,500 tokens. Clear hierarchy. 3 sections, not 13.**

vs current `_build_lkb_brief_context()`: ~3,000 tokens, 13 categories at equal priority, flat text.

### 2.5 Why This Solves Draft Quality Problems

| Problem | Root Cause | How v11.0 Fixes It |
|---------|-----------|-------------------|
| Thin facts | LLM doesn't know WHAT to plead | `facts_must_cover` in structured prompt |
| Missing sections (property schedule, doc list) | LLM decides structure itself | Schema `section_plan` enforces all sections |
| Wrong law citations | Flat dump, LLM cherry-picks | `LEGAL DATA` section with ONLY verified statutes |
| Prayer drops section numbers | `prayer_template` as prose, LLM paraphrases | `available_reliefs` with exact `prayer_text` |
| Facts-law mixing | No per-section instructions | Schema has per-section `instruction` field |
| Fabricated annexures | Hardcoded fake annexures | Schema `annexure_prefix` + evidence from intake only |
| Structure varies per draft | No explicit structure guidance | Same schema = same structure every time |

### 2.6 Scaling Math

```
Current:    92 LKB entries × 1 doc type (plaint)     = 92 combinations (12.5% coverage)
v11.0:      92 LKB entries + 12 schemas               = 1,104 combinations (~90% coverage)
With user contributions: + state/tribunal schemas     → ~100% coverage over time

To add 1 new cause type:    1 LKB entry, 0 schema changes    → works with ALL 12 doc types
To add 1 new document type: 1 schema, 0 LKB changes          → works with ALL 92 cause types
To add 1 new domain:        N LKB entries + reuse schemas     → 0 code changes
```

### 2.7 Pipeline Changes (v11.0)

```
CURRENT:
  intake_classify (cause_type) → enrichment (LKB) → draft (flat prompt) → gates

v11.0:
  intake_classify (cause_type + document_type) → enrichment (LKB + schema) → draft (structured prompt) → gates
```

- Intake LLM outputs `document_type` alongside `cause_type` (detected from user request)
- Enrichment loads LKB entry + document schema
- Prompt builder combines both into structured prompt
- LLM drafts complete document (1 call, same as today)
- Gates validate (0 LLM, same as today)

### 2.8 Document Type Coverage

```
Standard CPC (12 schemas):   ~90% of all civil documents
+ State-specific schemas:    ~95%
+ Tribunal schemas:          ~99%
+ User-contributed schemas:  ~100% over time
```

User contribution system: lawyers upload documents → system extracts schema → grows coverage.

### 2.9 Critical Requirements

1. **LKB data MUST be correct** — wrong law = wrong draft (gates catch some, not all)
2. **Document schema MUST be correct** — wrong structure = court rejection (verify against CPC)
3. **Prompt hierarchy MUST be clear** — structure > law > facts > constraints (not flat)

### 2.10 What Stays From v5.1/v9.0

- All verification gates (evidence anchoring, LKB compliance, citation validator, postprocess)
- All consistency gates (7 families, 50+ deterministic checks)
- All applicability compilers (5 families)
- All LKB entries (92 cause types — enriched with Layer 2 data)
- Pipeline structure (intake → enrich → draft → gates → review)
- 2 LLM calls (intake + draft), review optional

### 2.11 What Changes From v10.0

| v10.0 (old target) | v11.0 (new target) | Why |
|--------------------|--------------------|-----|
| 5-layer LKB model | 2-layer LKB model | Simpler, less data to maintain |
| Engine builds 70% deterministically | LLM drafts 100% from structured prompt | No complex engine builders needed |
| `section_plan` with `source: engine/llm_gap` | Document schema with section order + instructions | Schema is document-type-level, not cause-type-level |
| Engine = 400-line generic loop | Prompt builder = 100 lines | No engine at all, just better prompt |
| 5 new accuracy gates | Same 5 gates (still needed) | Gates still validate after draft |
| Plaint only | ALL 12 civil document types | Scalable to any document type |

### 2.12 Migration Path

1. **Phase 1**: Enrich LKB entries with Layer 2 (`available_reliefs` with `prayer_text`, `jurisdiction_basis`, etc.)
2. **Phase 2**: Create 3 document schemas (plaint, written_statement, interim_application)
3. **Phase 3**: Rewrite prompt builder (~100 lines replaces 400-line `_build_lkb_brief_context`)
4. **Phase 4**: Add `document_type` to intake classification
5. **Phase 5**: Add remaining 9 schemas, one at a time
6. **Phase 6**: Remove old engine.py template builders (−2400 lines)

### 2.13 Civil Plugin — Families (unchanged)

| Family | Cause Types | Resolver | Applicability | Gate | Status |
|--------|------------|----------|--------------|------|--------|
| Possession | tenant, licensee, trespasser, co_owner | Yes | Yes | Yes | **Done** |
| Injunction/Declaration | permanent, mandatory, declaration_title | Yes | Yes | Yes | **Done** |
| Contract/Commercial | breach, specific_performance, quantum_meruit | Yes | Yes | Yes | **Done** |
| Money/Debt | money_recovery_*, cheque_bounce, accounts | Yes | Yes | Yes | **Done** |
| Partition/Co-ownership | partition, easement, adverse_possession | Yes | Yes | Yes | **Done** |
| Tenancy/Rent | eviction, arrears_of_rent, mesne_profits_post_tenancy | Yes | Yes | Yes | **Done** |
| Tort/Civil Wrong | defamation, negligence, nuisance | Yes | Yes | Yes | **Done** |
| Business/Fiduciary | partnership, agency, trust | Pending | Pending | Pending | Pending |
| Succession/Estate | succession, probate, letters_admin | Pending | Pending | Pending | Pending |

### 2.14 Five New Accuracy Gates (from 44-gap analysis, still needed)

| Gate | What It Checks | Deterministic? |
|------|---------------|----------------|
| Procedural Prerequisite | S.80/S.12A/S.106/S.138 from LKB `pre_institution` | Yes |
| Date Consistency | All dates internally consistent | Yes |
| Arithmetic | Interest/damages computation correct | Yes |
| Annexure Cross-Reference | Body refs match annexure list | Yes |
| Accuracy Rules | mandatory_averments + forbidden_in_draft from LKB | Yes |

### 2.15 Universal Prompt Constraints (all drafts)

```
1. Cite ONLY from verified_provisions list
2. Do NOT include case law citations — use {{CASE_LAW_NEEDED: [topic]}}
3. Do NOT use "on or about" for dates
4. Pendente lite interest = Order XX Rule 11 CPC, NOT Section 34 CPC
5. Do NOT claim compound interest unless contract provides
6. In FACTS sections, plead ONLY factual events — no Section/Act numbers
7. Do NOT describe a licensee as "tenant"
8. Every document reference must use Annexure label
9. Verification must distinguish personal knowledge from information
10. Do NOT draft relief against non-parties
```

---

## 3. Pipeline (v5.1 — what's actually running)

```
STAGE 1: CONTEXT GATHERING (~12-15s, 1 LLM call)
  intake_classify (1 LLM) -> domain_router -> enrichment (limitation + provisions + LKB + court_fee parallel)

STAGE 2: FREE-TEXT DRAFTING (~30-50s, 1 LLM call)
  draft_freetext: LKB-guided, outputs complete court-ready document

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

### v9.0 Implementation Status

**DONE (post-draft enforcement):**
- `coa_type` default changed from `"single_event"` to `None` — fixes wrong instructions for 82/92 entries
- `_build_lkb_brief_context` updated — neutral instruction when `coa_type=None`
- `theory_anchoring` gate wired into `civil_consistency_gate_node`
- `_prayer_completeness_issues()` added — checks `required_reliefs` vs actual prayer
- Consistency gate changed from blocking to flagging (`goto="evidence_anchoring"`)
- Civil plugin registered (resolver, ambiguity gate, plan compiler, draft router, consistency gate)
- `DomainDecision` and `DraftPlanIR` models defined in states

**DONE (pre-draft enforcement — applicability compiler):**
- `_compile_applicability()` built in `civil_decision.py` — deterministic, screens Commercial Courts Act, S74/liquidated damages, mitigation_credit, arbitration
- `CivilDecision` populated with `allowed_statutes`, `forbidden_statutes`, `allowed_reliefs`, `forbidden_reliefs`, `allowed_damages`, `forbidden_damages`, `filtered_red_flags`
- `_mirror_civil_decision()` copies ALL allow/forbid fields to `decision_ir`
- `_build_lkb_brief_context()` filters through `decision_ir` — forbidden statutes excluded, forbidden damages excluded, inapplicable warning emitted
- Unsupported domains (Criminal, Family, Corporate) blocked at `domain_decision_compiler_node` → `goto=END` with blocked artifact
- LKB domain isolation enforced — `register_domain("Civil", ...)` only, no cross-domain fallback in `lookup()`
- Template failure blocks ALL families — no silent fallback to legacy freetext
- 234/234 tests passing

**DONE (applicability consumption + enforcement):**
- Plan compiler uses `decision.allowed_reliefs` / `decision.filtered_red_flags` — no longer reads raw LKB
- Prayer gate reads from `decision_ir`/`plan_ir` — no longer reads raw `lkb_brief`
- Relief vocabulary normalized — `_decree` suffix handled (both `permanent_injunction` and `permanent_injunction_decree` match)
- `plan_ir.constraints` propagates all allow/forbid fields from decision_ir
- Consistency gate blocks on hard violations (forbidden statute cited, forbidden damage as prayer) → `goto=END`
- Non-blocking issues (prayer completeness, theory anchoring) still flagged for review
- `_forbidden_content_violations()` added — checks draft text against `decision.forbidden_statutes` and `decision.forbidden_damages`
- 234/234 tests passing

**DONE (per-family consistency gates — 7 families covered):**
- `_possession_consistency_issues()` — S16 situs jurisdiction, tenant/licensee/trespasser track mixing, mesne profits, Order XX Rule 12
- `_injunction_consistency_issues()` — S38/S39 SRA footing, property situs, damages template, S34 CPC bar
- `_contract_consistency_issues()` — S73/S74 mixing, arbitration clause bar, S12A mediation, RERA forum, specific performance readiness, workman IDA exclusion, guarantee/indemnity confusion
- `_money_consistency_issues()` — S138 NI Act, Order XXXVII, excessive interest, MSMED, cheque bounce notice, accounts suit, workman exclusion
- `_partition_consistency_issues()` — Order XX Rule 18, pre/post-2005 coparcenary (Vineeta Sharma), Art 110 vs Art 65, genealogy table, share computation, S16 situs
- `_tenancy_consistency_issues()` — Rent Act protection bar, S106 TPA notice, arrears quantification, mesne profits post-tenancy
- `_tort_consistency_issues()` — 1-year limitation (Art 73/74/75), special damage for slander/public nuisance, negligence elements, MACT exclusion, consumer forum exclusion
- All wired into `civil_consistency_gate_node` — deterministic, zero LLM calls

**DONE (per-family applicability compilers — 5 families):**
- `_compile_contract()` — S14 personal service bar, S16(c) readiness, RERA forum bar, workman/IDA exclusion, guarantee vs indemnity track
- `_compile_money()` — S138 NI Act prerequisites, Order XXXVII eligibility, MSMED Council, excessive interest flag, workman exclusion
- `_compile_immovable_property()` — Vineeta Sharma coparcenary, Art 110 vs Art 65 limitation, adverse possession, S16 CPC situs
- `_compile_tenancy()` — Rent Act jurisdiction bar, S106 TPA notice, mesne profits post-tenancy, state-specific forum
- `_compile_tort()` — MACT exclusion (forbidden statute), consumer forum, Art 73/74/75 limitation, Bolam test, negligence elements, public nuisance special damage
- All dispatched from `_compile_applicability()` based on `family` parameter — 18 tests passing

**DONE (per-family templates — 7 families):**
- `_is_contract_cause()` — S73 legal basis, S10/S14/S16(c) for specific performance, rescission S27/27A, doctrine-based paragraphs
- `_is_money_cause()` — loan (S69/S73), goods (Sale of Goods Act), summary suit (Order XXXVII), quantum meruit (S70), guarantee (S126-147), indemnity (S124-125), rendition of accounts, specific movable (S7/S8 SRA)
- `_is_partition_cause()` — Partition Act + Hindu Succession Act + Order XX Rule 18, preliminary/final decree prayer, genealogy table marker, share computation marker, schedule of property
- `_is_tenancy_cause()` — S106 TPA notice, Rent Act status placeholder, notice compliance marker, eviction/arrears/mesne profits prayers
- `_is_tort_cause()` — defamation (reputation + injunction), negligence (duty of care), nuisance (abatement), malicious prosecution, conversion, fraud/misrepresentation
- All families: family-specific suit titles, jurisdiction (situs for property suits), legal basis, cause of action, valuation, interest, prayer
- 30 new template tests passing

**NOT DONE (remaining v9.0 gaps):**

1. **Non-civil domain plugins** — Criminal, Family, Corporate, IP need own LKB + plugins

---

## 4. Data Stores

### Single Source of Truth: LKB

**ALL legal data comes from the LKB. No RAG, no websearch, no external API calls during drafting.**

- **LKB v5.0** — 92 flat cause types across 16 sub-group files (`lkb/causes/`)
- **LKB v11.0 (target)** — same 92+ entries with 2 layers: Layer 1 (legal knowledge) + Layer 2 (document components with `prayer_text`, `jurisdiction_basis`, etc.)
- **Document schemas** — 12 schemas in `schemas/` directory, one per document type (plaint, written_statement, etc.)
- **Cause-type aliases** — `_CAUSE_TYPE_ALIASES` in LKB for fuzzy cause_type matching
- **Superseded acts map** — `SUPERSEDED_ACTS` in `lkb/__init__.py` for auto-replacement

### Disconnected (code preserved, not called)
- **Qdrant** — vector search, `civil` collection. Disconnected 2026-03-12. Code in `nodes/ragDomain.py`
- **Brave websearch** — court fee + legal research + procedural search. Disconnected 2026-03-12. Code in `tools/websearch.py`
- **Court fee node** — dead node, never routed to. Code in `nodes/courtFeeSearch.py`

### Why LKB-Only
- **Deterministic > LLM** — LKB is curated, verified, deterministic. No API latency, no hallucination
- **Limitation**: LKB has limitation for all 92 cause types — no need for LLM limitation selector
- **Provisions**: LKB has primary_acts + alternative_acts — verified_provisions built deterministically
- **Court fee**: LKB has court_fee_statute per cause type — placeholder if state-specific rate unknown
- **Procedural**: LKB has procedural_prerequisites — S.12A, S.80, S.106, S.138 all in data
- **Court detection**: deterministic from intake amounts + keywords
- **2 LLM calls total**: intake (1) + draft (1). Everything else is LKB data

---

## 5. Model Assignment (current)

| Node | Model | Reasoning | Temp | When |
|------|-------|-----------|------|------|
| intake_classify | qwen3.5:cloud | OFF | 0.3 | Always (1st LLM call) |
| enrichment | NONE (deterministic) | — | — | LKB lookup only, 0 LLM |
| draft | qwen3.5:cloud | ON | 0.7 | Always (2nd LLM call) |
| all gates | NONE (deterministic) | — | — | 0 LLM, pure code + LKB data |
| review | qwen3.5:cloud | ON | 0.3 | Optional (3rd LLM call, only if gates flag issues) |

### Fallback Chain
```
qwen3.5:cloud  -> glm-4.6:cloud -> OpenAI (REVIEW_LLM_MODEL)
All cloud down  -> draft skeleton with all placeholders
```

---

## 6. Verification Gates

### Current (v5.1 — 4 structural + 3 semantic gates, zero LLM)

| Gate | What it checks | Auto-fix? | Status |
|------|---------------|-----------|--------|
| Evidence Anchoring | Every fact traces to intake | Yes (tokens -> placeholder) | Done |
| LKB Compliance | Primary acts cited, superseded law auto-replace | Yes (superseded) | Done |
| Postprocess | Paragraph numbering, annexure labels, verification clause, spacing | Yes | Done |
| Citation Validator | Every citation in verified_provisions | Flag only | Done |
| **Family Consistency** | Theory mix, contradiction, COA consistency | Flag | Done (7 families) |
| **Theory Anchoring** | Every doctrine traces to LKB/provisions/user | Flag | Done |
| **Prayer Completeness** | `required_reliefs` vs actual prayer | Flag | Done |

### Target (v10.0 — add 5 accuracy gates + 2 critical fixes)

| Gate | What it checks | Auto-fix? | Status |
|------|---------------|-----------|--------|
| **Procedural Prerequisite** | S.80/S.12A/S.106/S.138 from LKB `pre_institution` | Flag (blocking) | Pending |
| **Date Consistency** | All dates internally consistent, COA < filing | Flag | Pending |
| **Arithmetic** | Interest computation = principal × rate × years | Flag | Pending |
| **Annexure Cross-Ref** | Body document refs ↔ annexure list | Flag | Pending |
| **Accuracy Rules** | `mandatory_averments` (blocking) + `forbidden_in_draft` from LKB | Block/Flag | Pending |
| **Citation Validator v2** | ALSO check draft citations AGAINST allowlist (not just allowlist in draft) | Flag | Pending |
| **Review Inline-Fix Safety** | Re-run critical gates after review inline-fix | Block | Pending |

---

## 7. LKB (2-Layer Model)

```python
from app.agents.drafting_agents.lkb import lookup
entry = lookup("Civil", "recovery_of_possession_tenant")

# Layer 1 — Legal knowledge (goes to LLM as guidance):
#   primary_acts, alternative_acts, limitation, court_rules,
#   damages_categories, permitted_doctrines, mandatory_averments,
#   facts_must_cover, defensive_points, drafting_red_flags,
#   coa_guidance, doc_type_keywords

# Layer 2 — Document components (goes to LLM as structured data):
#   available_reliefs (with prayer_text per relief)
#   jurisdiction_basis, valuation_basis, legal_basis_text
#   suit_title_prefix

# 92 cause types in 16 sub-group files (lkb/causes/)
# Intake LLM classifies into specific sub-types directly
# Intake prompt built dynamically from CAUSE_GROUPS (not hardcoded)

# coa_type default is None (not "single_event")
# When None: LLM uses display_name to determine COA characterization
# When explicit: strong instruction emitted

# Document schemas (12 entries) in schemas/ directory
# Schema defines section order + per-section instructions per document type
# Combined with LKB at runtime → structured prompt → LLM drafts
```

---

## 8. Settings Pattern

- Always use `settings.FIELD_NAME` from `from app.config import settings`
- NEVER use `os.getenv()` or `load_dotenv()`
- Import: `from app.config import logger, settings`

---

## 9. File Map (actual + v11.0 planned)

```
app/agents/drafting_agents/
├── drafting_graph.py                    # LangGraph StateGraph wiring
├── nodes/
│   ├── intake_classify.py               # Stage 1: merged intake + classify (1 LLM)
│   ├── enrichment.py                    # Stage 1: deterministic LKB enrichment (0 LLM, 0 API)
│   ├── draft_single_call.py             # Stage 2: draft_freetext_node (1 LLM)
│   ├── draft_template_fill.py           # Stage 2: template + gap_fill path (1 LLM)
│   ├── civil_decision.py               # Civil plugin: resolver + compiler (deterministic)
│   ├── domain_pipeline.py              # Domain plugin dispatcher
│   ├── evidence_anchoring.py            # Gate: evidence anchoring
│   ├── lkb_compliance.py               # Gate: LKB + superseded law check
│   ├── postprocess.py                   # Gate: formatting fixes
│   ├── citation_validator.py            # Gate: citation verification
│   ├── reviews.py                       # Stage 4: review (optional, 1 LLM)
│   ├── accuracy_gates.py               # [v11.0] 5 new accuracy gates (deterministic)
│   ├── ragDomain.py                     # DEAD CODE — Qdrant retrieval (disconnected 2026-03-12)
│   ├── courtFeeSearch.py               # DEAD CODE — court fee search (disconnected 2026-03-12)
│   └── _utils.py                        # Shared helpers
├── plugins/
│   ├── __init__.py                      # Plugin registry (get/resolve/list)
│   ├── base.py                          # DomainPlugin base class
│   └── civil.py                         # Civil plugin (wires civil_decision nodes)
├── gates/
│   └── theory_anchoring.py              # Gate: doctrine → LKB/provisions
├── prompts/
│   ├── intake_classify.py               # Dynamic cause_type list from LKB
│   ├── draft_prompt.py                  # [v11.0] Structured prompt builder (LKB + schema → prompt)
│   ├── gap_fill_prompt.py              # Gap-fill prompt (legacy, replaced by structured prompt in v11.0)
│   └── review.py                        # Review system/user prompts
├── schemas/                             # [v11.0] Document type schemas (NEW)
│   ├── __init__.py                      # DOCUMENT_SCHEMAS registry + lookup
│   ├── trial_court.py                   # plaint, written_statement, rejoinder, counter_claim
│   ├── applications.py                  # interim_application, condonation, set_aside_ex_parte, caveat
│   ├── appellate.py                     # appeal_memo, revision_petition, review_petition
│   └── execution.py                     # execution_application
├── templates/
│   └── engine.py                        # Template engine (legacy — to be removed in v11.0 Phase 6)
├── states/draftGraph.py                 # DraftingState + Pydantic models (v11.0: + document_type, document_schema)
├── lkb/                                 # SINGLE SOURCE OF TRUTH — all legal data
│   ├── __init__.py                      # Registry, lookup, aliases, superseded_acts
│   └── causes/                          # 16 sub-group files, 92 flat cause types
│       └── _helpers.py                  # _entry() schema (v11.0: Layer 1 + Layer 2)
├── tools/
│   └── websearch.py                     # DEAD CODE — Brave API (disconnected 2026-03-12)
└── docs/
    └── ARCHITECTURE_V10.md              # Architecture document (to be updated for v11.0)
```

---

## 10. Critical Rules (Non-Negotiable)

### Decide Law Before Drafting
- Applicability compiler decides legal track BEFORE LLM drafts
- LLM receives decision_ir, not raw LKB — it doesn't choose tenant vs licensee

### Generate First, Validate After
- LLM drafts freely (plain text, guided by plan_ir)
- Semantic + structural gates validate output
- Fix only what gates flag

### Deterministic > LLM
- Gates, LKB lookup, citation check, applicability = deterministic
- Only intake, drafting, review use LLM

### No Hardcoded Defaults for Legal Judgments
- `coa_type` default = `None` (not `"single_event"`)
- When field is `None`, LLM uses `display_name` as guide
- When field is explicit, strong instruction emitted

---

## 11. Anti-Patterns (DO NOT DO)

- Do NOT hardcode legal judgment defaults in `_entry()` — use `None`
- Do NOT let LLM decide legal track (tenant vs licensee) — applicability compiler decides
- Do NOT rely on red flags in prompt alone — enforce with semantic gate AFTER draft
- Do NOT constrain LLM output format (no JSON section keys)
- Do NOT use `os.getenv()` — use `settings.FIELD_NAME`
- Do NOT auto-fix substantive legal content — only formatting
- Do NOT allow case citations unless verified
- Do NOT dump all RAG chunks into review — use slim payload
- Do NOT add LLM calls for deterministic tasks
- Do NOT guess court fee — use verified data or placeholder
- Do NOT mix old/new architecture for migrated families
- Do NOT dump flat text to LLM — use structured prompt with clear hierarchy (structure > law > facts)
- Do NOT mix law data with document structure in LKB — keep Layer 1 (law) and Layer 2 (components) separate
- Do NOT hardcode document structure in engine builders — put it in document schema data
- Do NOT build per-cause-type engine builders — LLM drafts from structured prompt, not engine
- Do NOT add per-document-type hardcoded logic — document schema drives structure
- Do NOT bypass gates after review inline-fix — re-run critical gates
- Do NOT check only allowlist-in-draft for citations — ALSO check draft-against-allowlist

---

## 12. Recent Changes

### 2026-03-14 — v11.0 Architecture: Scalable Context-Driven Pipeline

- **Architecture shifted from v10.0 (engine-driven) to v11.0 (context-driven)**
- **Root cause identified**: `_build_lkb_brief_context()` dumps 13 categories as flat text → LLM ignores half
- **Solution**: LKB 2-layer model (legal data + document components) → structured prompt with hierarchy
- **Scaling solved**: Separate law (92 cause types) × structure (12 doc types) = 1,104 combinations from 104 entries
- **Document coverage expanded**: plaint-only (12.5%) → ALL civil documents (~90% day 1, ~100% with contributions)
- **12 document schemas designed**: plaint, written_statement, rejoinder, counter_claim, interim_application, execution_application, appeal_memo, revision_petition, review_petition, condonation_of_delay, set_aside_ex_parte, caveat
- **LKB Layer 2 defined**: `available_reliefs` (with `prayer_text`), `jurisdiction_basis`, `valuation_basis`
- **Prompt builder**: 100 lines replaces 400-line `_build_lkb_brief_context()`, clear 3-section hierarchy
- **No complex engine**: LLM drafts from structured prompt, not from engine-built template
- **LKB data correctness** identified as THE critical requirement — wrong data = wrong draft
- **10+ LKB corrections applied**: Art 67→64, Art 58→33, S.20A→S.41(ha), Art 55→44, proviso→Explanation
- **Review model changed**: Ollama → OpenAI (gpt-5.2) for review node

### 2026-03-13 — v10.0 Architecture (superseded by v11.0)

- **Architecture v10.0 designed** — universal data-driven pipeline, 5-layer LKB model
- **3 research passes completed**: Senior Lawyer (components), Judge (accuracy), Pipeline Debugger (44 gaps)
- **44 accuracy gaps identified** — 10 critical, 24 moderate, 10 minor
- **5 new gates designed** — procedural prerequisite, date consistency, arithmetic, annexure cross-ref, accuracy rules
- **10 universal prompt constraints defined** — prevent most common accuracy errors

### 2026-03-12 — Pipeline Optimization

- **Enrichment rewritten to pure deterministic** — 0 LLM calls, 0 API calls
- **RAG disconnected** — `_next_context_node()` always returns `"enrichment"`
- **Pipeline now: 2 LLM calls** — intake (1) + draft (1). Review optional

### 2026-03-10 — v9.0 Completion

- **Per-family applicability compilers** — 5 sub-compilers (contract, money, immovable_property, tenancy, tort)
- **Per-family consistency gates** — 7 families, 50+ deterministic checks
- **Per-family templates** — 7 families with family-specific sections
- **Applicability compiler + decision_ir** — full allow/forbid pipeline
- **1 remaining gap** — non-civil domain plugins

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
