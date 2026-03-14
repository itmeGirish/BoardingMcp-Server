# Legal Drafting Architecture v10.0 — Universal Data-Driven Pipeline

**Status:** FINAL ARCHITECTURE (approved for implementation)
**Date:** 2026-03-13
**Based on:** 3 research passes (Senior Lawyer Components, Judge Accuracy, Pipeline Gap Analysis)

---

## 1. Core Principle

**ONE architecture, ALL domains, ZERO hardcoding per cause type.**

Every decision the template engine currently makes via Python `if/elif` or `frozenset`
moves to DATA in the LKB entry. Adding a new cause type, new domain, or new document
type requires ONLY data — zero Python changes.

---

## 2. The 5-Layer Data Model

Each LKB entry carries 5 layers of data. Together they replace ALL hardcoded logic.

### Layer 1: Section Plan (replaces 9 frozensets + 117 if/elif branches)

```python
"section_plan": [
    {"key": "court_heading",    "source": "engine",  "builder": "court_heading"},
    {"key": "parties",          "source": "engine",  "builder": "parties"},
    {"key": "title",            "source": "engine",  "builder": "suit_title"},
    {"key": "jurisdiction",     "source": "engine",  "builder": "jurisdiction"},
    {"key": "facts",            "source": "llm_gap", "gap_id": "FACTS"},
    {"key": "cloud_on_title",   "source": "llm_gap", "gap_id": "HOSTILE_CLAIM"},
    {"key": "legal_basis",      "source": "engine",  "builder": "legal_basis"},
    {"key": "cause_of_action",  "source": "engine",  "builder": "cause_of_action"},
    {"key": "limitation",       "source": "engine",  "builder": "limitation"},
    {"key": "valuation",        "source": "engine",  "builder": "valuation"},
    {"key": "schedule_of_property", "source": "engine", "builder": "schedule_of_property"},
    {"key": "prayer",           "source": "engine",  "builder": "prayer"},
    {"key": "documents_list",   "source": "engine",  "builder": "documents_list"},
    {"key": "verification",     "source": "engine",  "builder": "verification"},
]
```

**Rules:**
- `source: "engine"` = deterministic section built by a named builder function
- `source: "llm_gap"` = LLM fills this section during gap-fill call
- Order in the list = order in the document
- Sections with `"condition"` key only appear when condition is true
- Each cause type defines its OWN section plan (inherits family defaults)

**What this replaces:**
- `_PARTITION_CAUSE_TYPES`, `_POSSESSION_CAUSE_TYPES`, etc. (9 frozensets) — DELETED
- `_is_partition_cause()`, `_is_possession_cause()`, etc. (9 methods) — DELETED
- 117 if/elif branches in `assemble()`, `_prayer()`, `_legal_basis()`, etc. — DELETED
- Hardcoded 3-gap structure (FACTS/BREACH/DAMAGES) — replaced by variable gaps

### Layer 2: Gap Definitions (replaces hardcoded 3-gap system)

```python
"gap_definitions": [
    {
        "gap_id": "FACTS",
        "heading": "FACTS ESTABLISHING TITLE",
        "constraints": [
            "Trace chain of title from original grant to plaintiff",
            "State mode of acquisition (sale deed / gift / inheritance)",
            "Identify registration details of each conveyance"
        ],
        "anti_constraints": [
            "Do NOT cite Section/Order/Act numbers — legal basis is a separate section",
            "Do NOT plead breach or damages — those belong in later sections"
        ],
        "max_paragraphs": 10
    },
    {
        "gap_id": "HOSTILE_CLAIM",
        "heading": "CLOUD ON TITLE AND DEFENDANT'S HOSTILE ACTS",
        "constraints": [
            "Describe defendant's specific hostile act (encroachment / denial / competing claim)",
            "State when plaintiff became aware of the cloud on title",
            "State how the cloud affects plaintiff's enjoyment of property"
        ],
        "anti_constraints": [
            "Do NOT argue law — state facts only"
        ],
        "max_paragraphs": 6
    }
]
```

**Rules:**
- Gap count is VARIABLE per cause type (3 to 6 gaps)
- Each gap has heading + constraints + anti_constraints
- Gap IDs become markers: `{{GENERATE:FACTS}}`, `{{GENERATE:HOSTILE_CLAIM}}`
- gap_fill_prompt.py reads these from LKB — no hardcoded heading overrides
- Parser extracts N gaps dynamically from LLM response

**What this replaces:**
- Hardcoded heading overrides in `merge_template_with_gaps()` for 3 families
- Hardcoded constraint blocks in `build_gap_fill_user_prompt()` for 3 families
- Fixed 3-gap parse logic in `parse_gap_fill_response()`
- Generic "BREACH PARTICULARS" heading applied to declaration/injunction suits

**Gap count by family (civil):**

| Family | # Gaps | Gap IDs |
|--------|--------|---------|
| Contract | 3 | FACTS, BREACH_PARTICULARS, DAMAGES |
| Money/Debt | 3 | TRANSACTION, DEFAULT, QUANTIFICATION |
| Possession | 3 | FACTS_OF_POSSESSION, DISPOSSESSION, LOSS_AND_DAMAGE |
| Injunction/Declaration | 3 | FACTS, THREATENED_INJURY, BALANCE_OF_CONVENIENCE |
| Partition | 4 | FACTS, GENEALOGY_AND_SHARES, DEFENDANT_CONDUCT, NECESSITY |
| Tenancy | 4 | FACTS, NOTICE_COMPLIANCE, GROUNDS, ARREARS_OR_MESNE |
| Tort | 3 | FACTS_OF_WRONG, CAUSATION, DAMAGES |

**Gap count by domain (future):**

| Domain | Document Type | # Gaps | Gap IDs |
|--------|--------------|--------|---------|
| Criminal | S.138 complaint | 4 | TRANSACTION, CHEQUE_DETAILS, NOTICE, NON_PAYMENT |
| Criminal | Bail application | 3 | CUSTODIAL_STATUS, MERITS, NO_FLIGHT_RISK |
| Family | Divorce petition | 4 | MARRIAGE, MISCONDUCT, BREAKDOWN, CHILDREN |
| Writ | Art.226 petition | 3 | FACTS, RIGHTS_VIOLATED, ALTERNATIVE_REMEDY |
| Consumer | Builder delay | 4 | TRANSACTION, DEFICIENCY, LOSS, COMPENSATION |
| Civil | Written statement | 4 | PRELIM_OBJECTIONS, PARAWISE_REPLY, ADDITIONAL_FACTS, LEGAL_GROUNDS |

### Layer 3: Accuracy Rules (replaces scattered gate logic)

```python
"accuracy_rules": {
    # Mandatory averments — gate BLOCKS if missing
    "mandatory_averments": [
        {
            "id": "readiness_willingness",
            "text_pattern": "ready and willing",
            "provision": "Section 16(c), Specific Relief Act, 1963",
            "blocking": True,
            "message": "S.16(c) SRA requires express averment of readiness and willingness"
        }
    ],

    # Forbidden content — gate BLOCKS if present
    "forbidden_in_draft": [
        {
            "pattern": "Section 34.*pendente",
            "message": "Pendente lite interest is under Order XX Rule 11 CPC, NOT Section 34 CPC",
            "blocking": True
        }
    ],

    # Required in prayer — gate flags if absent
    "prayer_must_include": ["costs", "omnibus_relief", "pendente_lite_interest"],

    # Required in facts — gate flags if absent
    "facts_must_mention": ["cause_of_action_date", "jurisdiction_basis"],

    # Cross-cutting rules activated by this cause type
    "activate_rules": [
        "situs_jurisdiction",        # S.16 CPC — property must be in court's territory
        "schedule_of_property",      # Property description required
        "commercial_court_screen",   # Check commercial threshold
    ]
}
```

**Cross-cutting rules (defined once, activated per cause type):**

| Rule ID | What It Checks | Deterministic? |
|---------|---------------|----------------|
| `situs_jurisdiction` | Property suit → court in property's district | Yes |
| `commercial_court_screen` | Amount > threshold → address S.12A mediation | Yes |
| `s80_notice` | Government defendant → S.80 CPC notice required | Yes |
| `arbitration_disclosure` | Contract with arb clause → plead why civil court | Yes |
| `date_consistency` | All dates internally consistent | Yes |
| `amount_consistency` | Prayer amount = facts amount | Yes |
| `annexure_crossref` | Body refs ↔ annexure list match | Yes |
| `party_in_prayer` | Every prayer party in parties block | Yes |
| `limitation_computation` | COA date + period vs filing date | Yes |
| `interest_computation` | principal × rate × years ≈ claimed interest | Yes |
| `no_case_citations` | No AI-generated case law | Yes |
| `no_compound_interest` | No compound interest without contract basis | Yes |
| `verification_split` | Personal knowledge vs information paragraphs | Yes |
| `s141_averment` | NI Act company → director averment required | Yes |

### Layer 4: Pre-Institution Requirements

```python
"pre_institution": [
    {
        "step": "section_12a_mediation",
        "act": "Commercial Courts Act, 2015, Section 12A",
        "condition": "is_commercial AND amount >= 300000",
        "mandatory": True,
        "waiver": "Urgent interim relief sought",
        "draft_must_contain": "pre-institution mediation certificate",
        "message": "S.12A pre-institution mediation mandatory for commercial suits"
    },
    {
        "step": "section_80_notice",
        "act": "CPC, Section 80",
        "condition": "government_defendant",
        "mandatory": True,
        "waiver": "Urgent interim relief with court permission",
        "notice_period_days": 60,
        "draft_must_contain": "notice under Section 80"
    }
]
```

**Pre-institution steps by cause type:**

| Cause Type | Required Steps |
|-----------|---------------|
| All commercial suits | S.12A mediation |
| Suits vs government | S.80 CPC notice (60 days) |
| Eviction (tenancy) | S.106 TPA notice (15/30 days) |
| Cheque bounce | S.138 demand notice (30+15 days) |
| Specific performance | Tender of performance |
| RERA disputes | RERA complaint (optional but advised) |

### Layer 5: Quality Anchors (what separates 6.8 from 9.5)

```python
"quality_anchors": {
    # What facts the LLM must plead (completeness)
    "facts_must_cover": [
        "Chain of title from original grant",
        "Mode of acquisition (sale/gift/inheritance)",
        "Registration details of each conveyance",
        "Defendant's specific hostile act with date"
    ],

    # Pre-empt opponent's likely defences (strategic)
    "defensive_points": [
        "Address limitation proactively — state exact accrual date",
        "Pre-empt adverse possession defence if applicable",
        "Address laches/delay if filing after extended period"
    ],

    # Evidence that must be referenced (anchoring)
    "evidence_checklist": [
        "Title deed / sale deed",
        "Revenue records / 7/12 extract",
        "Property tax receipts showing possession",
        "Legal notice to defendant"
    ],

    # Cause of action template (precision)
    "coa_trigger": "the Defendant denied/disputed the Plaintiff's title to the suit property",
    "coa_continuing": "The cause of action continues to subsist so long as the cloud on the Plaintiff's title remains"
}
```

---

## 3. How the Engine Changes

### Current Engine (2400 lines, 117 branches)

```
assemble() →
    if _is_partition_cause(): add schedule_of_property
    elif _is_possession_cause(): add schedule_of_property
    elif _is_tenancy_cause(): add schedule_of_property
    ...117 more branches...

    insert 3 fixed gaps: {{GENERATE:FACTS}}, {{GENERATE:BREACH}}, {{GENERATE:DAMAGES}}
```

### New Engine (~400 lines, ZERO branches)

```python
def assemble(self, lkb, intake, decision_ir, ...):
    """Generic loop — reads section_plan from LKB."""

    section_plan = lkb.get("section_plan")
    if not section_plan:
        return self._assemble_legacy(lkb, intake, ...)  # Backward compat during migration

    parts = []
    for section in section_plan:
        # Check condition (if any)
        if "condition" in section:
            if not self._evaluate_condition(section["condition"], lkb, intake, decision_ir):
                continue

        if section["source"] == "engine":
            # Deterministic section — call named builder
            builder = self._get_builder(section["builder"])
            text = builder(lkb=lkb, intake=intake, decision_ir=decision_ir)
            parts.append(text)

        elif section["source"] == "llm_gap":
            # LLM gap — insert marker
            parts.append(f"{{{{GENERATE:{section['gap_id']}}}}}")

    return "\n\n".join(parts)
```

**Builder registry (replaces 10 hardcoded section methods):**

```python
BUILDERS = {
    # Universal builders (ALL documents, ALL domains)
    "court_heading":        self._court_heading,
    "parties":              self._parties_block,
    "suit_title":           self._suit_title,
    "limitation":           self._limitation_section,
    "prayer":               self._prayer,
    "documents_list":       self._documents_list,
    "verification":         self._verification,

    # Civil domain builders
    "jurisdiction":         self._jurisdiction_section,
    "legal_basis":          self._legal_basis,
    "cause_of_action":      self._cause_of_action,
    "valuation":            self._valuation_court_fee,
    "interest":             self._interest_section,
    "schedule_of_property": self._schedule_of_property,
    "damages_schedule":     self._damages_schedule,
    "commercial_maintainability": self._commercial_maintainability,
    "genealogy_table":      self._genealogy_table,

    # Future domain builders (Criminal, Family, Writ, etc.)
    # Added here when domain plugins are built — engine code unchanged
}
```

**Each builder becomes DATA-DRIVEN internally:**

```python
def _prayer(self, *, lkb, intake, decision_ir, **kw):
    """Build prayer from LKB prayer_template — no if/elif per cause type."""
    prayer_items = lkb.get("prayer_template") or []
    if not prayer_items:
        return self._prayer_generic(lkb, intake)  # Fallback for entries without template

    lines = ["PRAYER", "", "In the premises aforesaid, ..."]
    for i, item in enumerate(prayer_items):
        letter = chr(ord('a') + i)
        lines.append(f"    ({letter}) {item};")

    # Auto-append mandatory closing reliefs
    if not any("costs" in p.lower() for p in prayer_items):
        lines.append(f"    ({chr(ord('a') + len(prayer_items))}) Award costs of this suit;")
    if not any("further relief" in p.lower() for p in prayer_items):
        lines.append(f"    ({chr(ord('a') + len(prayer_items) + 1)}) Pass such other and further relief...")

    return "\n".join(lines)
```

```python
def _suit_title(self, *, lkb, intake, **kw):
    """Build suit title from LKB display_name — no if/elif per cause type."""
    display = lkb.get("display_name", "")
    return f"SUIT FOR {display.upper()}"
```

```python
def _legal_basis(self, *, lkb, intake, decision_ir, **kw):
    """Build legal basis from LKB data — no hardcoded doctrine blocks."""
    # 1. Section overrides from LKB (cause-type-specific paragraphs)
    overrides = lkb.get("section_overrides", {}).get("legal_basis", {})
    if overrides.get("paragraphs"):
        lines = ["LEGAL BASIS"]
        for para in overrides["paragraphs"]:
            lines.append(f"\n{self._next_para()}. {para}")
        return "\n".join(lines)

    # 2. Build from permitted_doctrines + primary_acts (generic)
    lines = ["LEGAL BASIS"]
    for doctrine in (lkb.get("permitted_doctrines") or []):
        template = _DOCTRINE_TEMPLATES.get(doctrine)
        if template:
            lines.append(f"\n{self._next_para()}. {template}")
    return "\n".join(lines)
```

### Migration Strategy

| Phase | What | Risk | Test |
|-------|------|------|------|
| Phase 1 | Add `section_plan` + `gap_definitions` to `_entry()` with `None` defaults | Zero — no behavior change | All existing tests pass |
| Phase 2 | Add `_assemble_from_plan()` in engine — if `section_plan` exists, use it; else legacy | Zero — legacy path unchanged | All existing tests pass |
| Phase 3 | Add `section_plan` to ONE family (contract, 7 cause types) | Low — one family only | Contract tests pass + benchmark |
| Phase 4 | Migrate remaining 6 families one by one | Low — each family isolated | Per-family tests |
| Phase 5 | Delete legacy path (frozensets, `_is_X_cause()`, if/elif) | Medium — irreversible | Full test suite |
| Phase 6 | Add gap_fill_prompt changes (read gap_definitions) | Low — only affects template path | Gap-fill tests |
| Phase 7 | Add accuracy rules + new gates | Low — additive | Gate tests |

---

## 4. Gap-Fill Prompt Changes

### Current (hardcoded 3 families)

```python
def build_gap_fill_user_prompt(...):
    # Hardcoded heading overrides for 3 families
    if cause_type in _INJUNCTION_CAUSE_TYPES:
        heading_1 = "FACTS REQUIRING PROTECTION"
    elif cause_type in _CONTRACT_CAUSE_TYPES:
        heading_1 = "FACTS OF THE CASE"
    else:
        heading_1 = "FACTS OF THE CASE"  # Generic

    # Hardcoded constraints for 3 families
    if cause_type in _CONTRACT_CAUSE_TYPES:
        constraints = "Do NOT plead S.74 unless..."
    ...
```

### New (reads from LKB)

```python
def build_gap_fill_user_prompt(*, gap_definitions, facts_must_cover=None, ...):
    """Build gap-fill prompt from LKB gap_definitions — zero hardcoding."""

    parts = []

    # Per-gap instructions from LKB
    for gap_def in gap_definitions:
        parts.append(f"\n--- {{{{GENERATE:{gap_def['gap_id']}}}}} ---")
        parts.append(f"Section heading: {gap_def['heading']}")

        if gap_def.get("constraints"):
            parts.append("In this section, you MUST cover:")
            for c in gap_def["constraints"]:
                parts.append(f"  - {c}")

        if gap_def.get("anti_constraints"):
            parts.append("In this section, you must NOT:")
            for ac in gap_def["anti_constraints"]:
                parts.append(f"  - {ac}")

    # Facts guidance from LKB
    if facts_must_cover:
        parts.append("\nFACTS MUST COVER:")
        for f in facts_must_cover:
            parts.append(f"  - {f}")

    return "\n".join(parts)
```

### Parser Changes

```python
def parse_gap_fill_response(response: str, gap_definitions: list) -> dict:
    """Parse N gaps from LLM response — not fixed at 3."""
    gap_ids = [g["gap_id"] for g in gap_definitions]
    result = {}

    # Split on {{GENERATE:GAP_ID}} markers
    pattern = '|'.join(re.escape(gid) for gid in gap_ids)
    parts = re.split(rf'\{{{{GENERATE:({pattern})(?:\|[^}}]*)?\}}}}', response)

    for i, part in enumerate(parts):
        if part in gap_ids and i + 1 < len(parts):
            result[part] = parts[i + 1].strip()

    return result
```

---

## 5. New Gates (from Accuracy Research)

### 5 New Deterministic Gates

```
Pipeline with new gates:

intake_classify → domain_router → enrichment
    → [NEW] procedural_prerequisite_gate    ← checks S.80/S.12A/S.106/S.138 steps
    → civil_decision → template + gap_fill → draft
    → [NEW] date_consistency_gate           ← all dates internally consistent
    → [NEW] arithmetic_gate                 ← interest computation verification
    → evidence_anchoring
    → [NEW] annexure_crossref_gate          ← body refs ↔ annexure list
    → lkb_compliance
    → consistency_gate (existing)
    → [NEW] accuracy_rules_gate             ← mandatory_averments, forbidden_in_draft
    → citation_validator
    → postprocess
    → review (if issues)
    → END
```

**Gate 1: Procedural Prerequisite Gate**
```python
def procedural_prerequisite_gate(state):
    """Check pre-institution requirements from LKB."""
    lkb = state["lkb_brief"]
    pre_steps = lkb.get("pre_institution", [])
    issues = []
    for step in pre_steps:
        if _condition_met(step["condition"], state):
            if step["draft_must_contain"] not in state["draft_text"].lower():
                issues.append({
                    "issue": f"Missing {step['step']}",
                    "provision": step["act"],
                    "message": step["message"],
                    "blocking": step["mandatory"]
                })
    return issues
```

**Gate 2: Date Consistency Gate**
```python
def date_consistency_gate(draft_text, intake):
    """Extract all (date, event) pairs. Flag same-event conflicts."""
    date_events = _extract_date_event_pairs(draft_text)  # regex
    issues = []
    # Check: COA date < filing date
    # Check: contract date < breach date
    # Check: notice date < filing date
    # Check: S.138 cheque return + 30 days >= notice date
    return issues
```

**Gate 3: Arithmetic Gate**
```python
def arithmetic_gate(draft_text, intake_amounts, lkb):
    """Verify interest/damages computation."""
    principal = intake_amounts.get("principal", 0)
    rate = intake_amounts.get("interest_rate", 0)
    coa_date = intake_amounts.get("cause_of_action_date")
    # Compute expected interest
    # Compare against claimed interest in prayer (regex extract)
    # Flag if discrepancy > 5%
    return issues
```

**Gate 4: Annexure Cross-Reference Gate**
```python
def annexure_crossref_gate(draft_text):
    """Check body document references match annexure list."""
    body_refs = _extract_annexure_refs_from_body(draft_text)    # regex: "Annexure P-1"
    list_refs = _extract_annexure_refs_from_list(draft_text)    # regex from documents section
    orphan_annexures = list_refs - body_refs   # In list but not in body
    missing_annexures = body_refs - list_refs  # In body but not in list
    return issues
```

**Gate 5: Accuracy Rules Gate**
```python
def accuracy_rules_gate(draft_text, lkb):
    """Check mandatory_averments and forbidden_in_draft from LKB."""
    rules = lkb.get("accuracy_rules", {})
    issues = []

    # Mandatory averments
    for av in rules.get("mandatory_averments", []):
        if av["text_pattern"].lower() not in draft_text.lower():
            issues.append({
                "issue": f"Missing mandatory averment: {av['id']}",
                "provision": av["provision"],
                "blocking": av["blocking"]
            })

    # Forbidden content
    for fc in rules.get("forbidden_in_draft", []):
        if re.search(fc["pattern"], draft_text, re.IGNORECASE):
            issues.append({
                "issue": f"Forbidden content found: {fc['message']}",
                "blocking": fc["blocking"]
            })

    return issues
```

---

## 6. Updated `_entry()` Schema

```python
def _entry(
    *,
    # ── Identity (existing) ──
    registry_kind,
    code,
    display_name,
    document_type="plaint",

    # ── Substantive Law (existing) ──
    primary_acts=None,
    alternative_acts=None,
    limitation=None,
    permitted_doctrines=None,
    excluded_doctrines=None,

    # ── NEW: Section Plan ── (Layer 1)
    section_plan=None,          # List[Dict] — ordered sections

    # ── NEW: Gap Definitions ── (Layer 2)
    gap_definitions=None,       # List[Dict] — variable-count LLM gaps

    # ── NEW: Accuracy Rules ── (Layer 3)
    accuracy_rules=None,        # Dict — mandatory_averments, forbidden_in_draft, etc.

    # ── NEW: Pre-Institution ── (Layer 4)
    pre_institution=None,       # List[Dict] — procedural prerequisites with conditions

    # ── Quality Anchors (existing + enhanced) ── (Layer 5)
    facts_must_cover=None,
    defensive_points=None,
    evidence_checklist=None,
    mandatory_averments=None,   # Kept for backward compat; accuracy_rules.mandatory_averments preferred
    coa_type=None,
    coa_guidance="",

    # ── Section Overrides ── (for deterministic sections)
    section_overrides=None,     # Dict[str, Dict] — per-section data overrides

    # ── Existing fields (unchanged) ──
    stage=None,
    court_rules=None,
    required_sections=None,
    required_reliefs=None,
    required_averments=None,
    optional_reliefs=None,
    procedural_prerequisites=None,
    doc_type_keywords=None,
    classification_hints=None,
    defensive_points_legacy=None,
    terminology=None,
    damages_categories=None,
    interest_basis="not_applicable",
    interest_guidance="",
    mandatory_inline_sections=None,
    drafting_red_flags=None,
    prayer_template=None,
    court_fee_statute=None,
    detected_court=None,
    complexity_weight=2,
    notes=None,
    draft_config=None,
):
```

**New fields default to `None` — engine falls back to legacy path when `None`.**

---

## 7. Family Defaults + Cause-Type Overrides

To avoid repeating the same section_plan for every cause type in a family,
define FAMILY DEFAULTS that cause types inherit:

```python
# In _helpers.py or a new family_defaults.py

CONTRACT_FAMILY_DEFAULTS = {
    "section_plan": [
        {"key": "court_heading",    "source": "engine",  "builder": "court_heading"},
        {"key": "parties",          "source": "engine",  "builder": "parties"},
        {"key": "title",            "source": "engine",  "builder": "suit_title"},
        {"key": "jurisdiction",     "source": "engine",  "builder": "jurisdiction"},
        {"key": "commercial",       "source": "engine",  "builder": "commercial_maintainability",
         "condition": "is_commercial"},
        {"key": "facts",            "source": "llm_gap", "gap_id": "FACTS"},
        {"key": "breach",           "source": "llm_gap", "gap_id": "BREACH_PARTICULARS"},
        {"key": "damages",          "source": "llm_gap", "gap_id": "DAMAGES"},
        {"key": "legal_basis",      "source": "engine",  "builder": "legal_basis"},
        {"key": "cause_of_action",  "source": "engine",  "builder": "cause_of_action"},
        {"key": "limitation",       "source": "engine",  "builder": "limitation"},
        {"key": "valuation",        "source": "engine",  "builder": "valuation"},
        {"key": "interest",         "source": "engine",  "builder": "interest"},
        {"key": "prayer",           "source": "engine",  "builder": "prayer"},
        {"key": "damages_schedule", "source": "engine",  "builder": "damages_schedule",
         "condition": "has_damages_categories"},
        {"key": "documents_list",   "source": "engine",  "builder": "documents_list"},
        {"key": "verification",     "source": "engine",  "builder": "verification"},
    ],
    "gap_definitions": [
        {
            "gap_id": "FACTS",
            "heading": "FACTS OF THE CASE",
            "constraints": [
                "Date, parties, and essential terms of the contract",
                "Plaintiff's performance or readiness to perform",
                "Reference to supporting documents as Annexures"
            ],
            "anti_constraints": [
                "Do NOT cite Section/Order/Act numbers",
                "Do NOT plead breach or damages — those belong in later sections"
            ]
        },
        {
            "gap_id": "BREACH_PARTICULARS",
            "heading": "BREACH OF CONTRACT AND PARTICULARS",
            "constraints": [
                "Specific act or omission constituting breach",
                "Date of breach",
                "Demand made and response (or silence)"
            ],
            "anti_constraints": [
                "Do NOT repeat facts already stated",
                "Do NOT compute damages — that belongs in DAMAGES section"
            ]
        },
        {
            "gap_id": "DAMAGES",
            "heading": "LOSS AND DAMAGE",
            "constraints": [
                "Itemized heads of damage with amounts",
                "Causal link between breach and each head of damage",
                "Mitigation efforts by plaintiff"
            ],
            "anti_constraints": [
                "Do NOT claim compound interest unless contract expressly provides",
                "Do NOT claim punitive damages (not recognized in Indian contract law)"
            ]
        }
    ]
}

# Cause-type entry INHERITS family defaults + overrides specific fields:
"specific_performance": _entry(
    ...,
    section_plan=None,       # None = inherit CONTRACT_FAMILY_DEFAULTS.section_plan
    gap_definitions=[        # Override: different constraints for specific_performance
        {
            "gap_id": "FACTS",
            "heading": "FACTS OF THE CONTRACT AND READINESS",
            "constraints": [
                "Date and terms of agreement to sell / contract",
                "Plaintiff's readiness and willingness to perform (S.16(c) SRA — MANDATORY)",
                "Tender of performance and defendant's refusal"
            ],
            ...
        },
        ...
    ]
)
```

**Resolution logic:**
```python
def resolve_section_plan(lkb_entry, family_defaults):
    """Cause-type plan overrides family default; None = inherit."""
    return lkb_entry.get("section_plan") or family_defaults.get("section_plan")

def resolve_gap_definitions(lkb_entry, family_defaults):
    return lkb_entry.get("gap_definitions") or family_defaults.get("gap_definitions")
```

---

## 8. Prompt Constraints (from Accuracy Research)

These 10 constraints are injected into EVERY draft prompt, regardless of cause type:

```python
UNIVERSAL_PROMPT_CONSTRAINTS = [
    "1. Cite ONLY statutes from the VERIFIED PROVISIONS list. Do NOT add any statutory section not in that list.",
    "2. Do NOT include any case law citations. Write {{CASE_LAW_NEEDED: [topic]}} if case law support is needed.",
    "3. Do NOT use 'on or about' for any date. Use specific dates or {{DATE_PLACEHOLDER}}.",
    "4. Pendente lite interest is under Order XX Rule 11 CPC, NOT Section 34 CPC.",
    "5. Do NOT claim compound interest unless the contract expressly provides for it.",
    "6. In FACTS sections, plead ONLY factual events. Do NOT cite Section/Order/Act numbers.",
    "7. Do NOT describe a licensee as a 'tenant' or use 'tenancy' for a licence arrangement.",
    "8. Every document referenced must use its Annexure label (Annexure P-1, P-2, etc.).",
    "9. The verification clause must distinguish personal knowledge from information and belief.",
    "10. Do NOT draft relief against any person not named in the parties block.",
]
```

---

## 9. Citation Validator Fix (Critical Gap #32)

Current validator checks: "is each ALLOWLIST provision present in draft?"
Should ALSO check: "is each DRAFT citation present in ALLOWLIST?"

```python
def _check_draft_citations_against_allowlist(draft_text, verified_provisions):
    """NEW: Extract citations FROM draft and verify against allowlist."""
    draft_citations = _extract_all_section_citations(draft_text)  # regex
    allowed_set = {p["section"] for p in verified_provisions} | _ALWAYS_ALLOWED

    issues = []
    for citation in draft_citations:
        if citation not in allowed_set:
            issues.append({
                "issue": f"Unverified citation: {citation}",
                "severity": "WARN",
                "message": f"'{citation}' not in verified provisions. May be hallucinated."
            })
    return issues
```

---

## 10. Review Inline-Fix Safety (Critical Gap #40)

Current: Review inline-fix goes directly to final_draft, bypassing ALL gates.
Fix: Re-run critical gates after inline fix.

```python
def review_node(state):
    ...
    if review.inline_fix:
        fixed_text = review.inline_fix
        # RE-RUN critical gates on fixed text
        fixed_text = _fix_superseded_acts(fixed_text, lkb)
        evidence_issues = evidence_anchoring(fixed_text, intake)
        citation_issues = _check_draft_citations_against_allowlist(fixed_text, verified)
        accuracy_issues = accuracy_rules_gate(fixed_text, lkb)
        # Only promote if no new blocking issues
        ...
```

---

## 11. File Changes Summary

| File | Change | Lines | Phase |
|------|--------|-------|-------|
| `lkb/causes/_helpers.py` | Add 5 new fields to `_entry()` | +30 | 1 |
| `lkb/causes/_helpers.py` | Add family defaults (7 families) | +350 | 1 |
| `templates/engine.py` | Add `_assemble_from_plan()` generic loop | +80 | 2 |
| `templates/engine.py` | Make builders accept `lkb` kwarg | +50 | 2 |
| `prompts/gap_fill_prompt.py` | Read `gap_definitions` from LKB | +40, -60 | 3 |
| `nodes/draft_template_fill.py` | Pass `gap_definitions`, parse N gaps | +30, -20 | 3 |
| `nodes/accuracy_gates.py` | NEW: 5 new deterministic gates | +200 | 4 |
| `nodes/citation_validator.py` | Add draft-against-allowlist check | +30 | 4 |
| `nodes/reviews.py` | Re-run gates after inline fix | +20 | 4 |
| `drafting_graph.py` | Wire new gates into graph | +15 | 4 |
| `lkb/causes/*.py` (16 files) | Add section_plan + gap_definitions per cause type | +30/file | 5 |

**Total: ~900 new lines, ~80 deleted lines. Engine.py drops from 2400 to ~600 after Phase 5.**

---

## 12. What Does NOT Change

- `drafting_graph.py` structure (intake → enrichment → draft → gates → review)
- `civil_decision.py` (applicability compiler stays)
- `plugins/` (plugin architecture stays)
- `states/draftGraph.py` (state models stay)
- `nodes/enrichment.py` (deterministic enrichment stays)
- `nodes/evidence_anchoring.py` (evidence anchoring stays, gets enhanced)
- `nodes/postprocess.py` (postprocess stays)
- LLM call count (still 2 calls: intake + draft; review optional)
- All existing tests (legacy path preserved during migration)

---

## 13. Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Pipeline avg score | 9.0/10 | 9.5/10 |
| Pipeline wins vs ChatGPT | 3/10 | 7/10 |
| Lines in engine.py | 2400 | 600 |
| Python changes per new cause type | 50-100 lines | 0 |
| Python changes per new domain | 2000+ lines | 200 lines (domain builders only) |
| Accuracy gaps (critical) | 10 | 0 |
| Deterministic accuracy rules | 0 | 50+ |
| LLM calls for clean draft | 2 | 2 (unchanged) |

---

## 14. Implementation Order

```
Phase 1: Data Model         (1 day)  — _entry() fields + family defaults
Phase 2: Engine Generic Loop (1 day)  — _assemble_from_plan() + builder registry
Phase 3: Gap-Fill Prompt     (0.5 day) — read gap_definitions, parse N gaps
Phase 4: Accuracy Gates      (1 day)  — 5 new gates + citation fix + review fix
Phase 5: Migrate Families    (3 days) — 7 families × section_plan + gap_definitions
Phase 6: Delete Legacy       (0.5 day) — remove frozensets, _is_X_cause(), if/elif
Phase 7: Benchmark           (0.5 day) — run 10-scenario comparison
```
