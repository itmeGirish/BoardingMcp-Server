# SKILL: lkb-enrichment

Use when: adding Layer 2 data to LKB entries, verifying LKB accuracy, or fixing wrong legal data.

## What Is LKB Enrichment

LKB entries currently have Layer 1 (legal knowledge). v11.0 needs Layer 2 (document components) added to each entry. This skill guides enrichment.

## LKB 2-Layer Model

| Layer | Fields | Purpose |
|-------|--------|---------|
| Layer 1: Legal Knowledge | `primary_acts`, `limitation`, `facts_must_cover`, `mandatory_averments`, `defensive_points`, `drafting_red_flags`, `coa_guidance` | Tells LLM WHAT law to apply |
| Layer 2: Document Components | `available_reliefs` (with `prayer_text`), `jurisdiction_basis`, `valuation_basis`, `legal_basis_text` | Tells LLM WHAT structural content to use |

Both layers go to LLM as structured context in the prompt.

## Layer 2 Fields to Add

### `available_reliefs` (most important)

List of reliefs with exact prayer text. LLM uses `prayer_text` verbatim in prayer section.

```python
"available_reliefs": [
    {
        "type": "damages",           # relief category
        "subtype": "compensatory",   # specific kind
        "statute": "S.73 ICA",       # statutory basis
        "prayer_text": "decree for damages in the sum of Rs.{{AMOUNT}} on account of breach of contract",
        "condition": None,           # when to include (None = always)
    },
    {
        "type": "interest",
        "subtype": "pre_suit",
        "statute": "S.34 CPC",
        "prayer_text": "interest at the rate of {{RATE}}% per annum from {{DATE}} till date of filing",
    },
    {
        "type": "interest",
        "subtype": "pendente_lite",
        "statute": "Order XX Rule 11 CPC",
        "prayer_text": "pendente lite and future interest at such rate as this Hon'ble Court deems fit",
    },
    {
        "type": "costs",
        "statute": "S.35 CPC",
        "prayer_text": "costs of the suit",
    },
    {
        "type": "general",
        "prayer_text": "such other and further relief(s) as this Hon'ble Court may deem fit and proper",
    },
],
```

### `jurisdiction_basis`

```python
"jurisdiction_basis": "Section 20 CPC — where cause of action arose wholly or in part",
# or: "Section 16 CPC — where immovable property is situated (situs jurisdiction)"
# or: "Section 17 CPC — property in multiple jurisdictions"
```

### `valuation_basis`

```python
"valuation_basis": "Amount of damages claimed (for court fee and pecuniary jurisdiction)",
# or: "Market value of suit property"
# or: "Amount of rent arrears claimed"
```

## Enrichment Process

1. Read existing LKB entry in `lkb/causes/{file}.py`
2. Check what Layer 2 fields already exist (some entries may have partial data)
3. Add `available_reliefs` — list ALL reliefs applicable for that cause type
4. Add `jurisdiction_basis` — which CPC section determines jurisdiction
5. Add `valuation_basis` — what determines suit valuation
6. Verify `prayer_text` matches actual court prayer wording
7. Run tests to ensure no regression

## LKB Accuracy Verification

When enriching, also verify existing Layer 1 data:

- **Limitation article** — check against Limitation Act schedule
- **Primary acts** — check section numbers exist in actual act
- **Superseded acts** — check for repealed laws (Evidence Act 1872 → BSA 2023)
- **Red flags** — check legal accuracy of warnings

### Known Corrections (2026-03-14)
- Art 67 → Art 64 (recovery_of_possession_tenant)
- Art 58 → Art 33 (easement)
- S.20A → S.41(ha) SRA (specific_performance)
- Art 55 → Art 44 (guarantee_recovery)
- Art 55 → UNKNOWN (indemnity_recovery)
- "S.73 proviso" → "Explanation to S.73 ICA"

## Files

```
app/agents/drafting_agents/lkb/
├── __init__.py           # Registry, lookup, aliases
└── causes/
    ├── _helpers.py        # _entry() schema — add Layer 2 fields here
    ├── contract_commercial.py
    ├── money_and_debt.py
    ├── immovable_property.py
    ├── injunction_declaratory.py
    ├── partition_coownership.py
    ├── tenancy_rent.py
    ├── tort_civil_wrong.py
    └── ... (16 sub-group files, 92 entries)
```

## Rules
- `prayer_text` must match actual court prayer wording — not generic
- Layer 2 fields are document-AGNOSTIC — same reliefs for plaint and counter-claim
- Do NOT put document-specific structure in LKB — that's the schema's job
- Verify against bare act text, not memory
- When unsure about limitation article, use "UNKNOWN" with description
- `available_reliefs` must cover ALL reliefs for that cause type (including costs + general)
