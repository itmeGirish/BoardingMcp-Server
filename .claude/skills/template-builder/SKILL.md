# SKILL: exemplar-builder

## Purpose
Create, validate, and maintain structural exemplars that guide draft LLM output quality. v5.1 uses exemplar-guided free-text drafting — exemplars show document structure, section order, and Indian legal conventions. The LLM uses the exemplar as a structural reference while drafting the complete document.

## When to Use
- Creating a new exemplar for a cause type
- Reviewing exemplar quality
- Adding a new document category
- Debugging why draft structure is wrong for a specific cause type

## Architecture Context (v5.1 — what's running)

Exemplars are loaded into the draft system prompt via `load_exemplar(doc_type)`. The LLM sees the exemplar as a structural guide and produces a complete court-ready document in a single call.

```
exemplar (system prompt) + LKB brief + RAG + user facts -> draft_freetext_node -> complete document
```

No Template Engine, no Section Registry, no gap-fill markers. Exemplars guide STRUCTURE and TONE.

---

## Exemplar Directory

```
app/agents/drafting_agents/exemplars/
├── breach_dealership_franchise.txt
├── money_recovery_loan.txt
├── partition.txt
├── recovery_of_possession.txt
├── permanent_injunction.txt
├── defamation.txt
├── _default.txt                    # Fallback for unknown cause types
└── ... (per cause type)
```

---

## Exemplar Format (~1,500 tokens)

Each exemplar is a structural template showing:
1. Court heading format
2. Parties block format
3. Section ordering (FACTS, BREACH, DAMAGES, CAUSE OF ACTION, JURISDICTION, etc.)
4. Heading style (ALL CAPS)
5. Paragraph numbering convention
6. Prayer section format
7. Verification clause
8. Advocate block

### Example Structure
```
IN THE COURT OF {{COURT_NAME}}
AT {{PLACE}}

CIVIL SUIT NO. _____ OF 20____

{{PLAINTIFF_NAME}}                               ... PLAINTIFF
VERSUS
{{DEFENDANT_NAME}}                               ... DEFENDANT

PLAINT UNDER {{SECTIONS}}

MOST RESPECTFULLY SHOWETH:

FACTS OF THE CASE

1. That the Plaintiff is {{description}}...
2. That the Defendant is {{description}}...

[... structural sections with generic placeholders ...]

PRAYER

In the premises aforesaid, the Plaintiff most respectfully prays:
(a) That this Hon'ble Court be pleased to pass a decree...

VERIFICATION
I, {{NAME}}, the Plaintiff above-named, do hereby verify...

DEPONENT

Place: {{PLACE}}
Date: {{DATE}}

Through:
{{ADVOCATE_NAME}}
Advocate for the Plaintiff
```

---

## Creating a New Exemplar

1. Name file to match LKB cause_type key (e.g., `specific_performance.txt`)
2. Use ~1,500 tokens (shorter is fine, never exceed ~2,000)
3. Use `{{PLACEHOLDER}}` for all specific facts/names/amounts
4. Show ALL expected sections for that cause type in correct order
5. Show correct heading style (ALL CAPS for section headers)
6. Include verification clause and advocate block
7. Test by running pipeline with the new cause type

### Cause-Type Specific Sections

Different cause types need different sections:
- **Partition**: genealogy table, share entitlement, schedule of property
- **Dealership/franchise**: investment details, territory, termination breach
- **Recovery of possession**: property description, occupancy basis, trespass/encroachment
- **Defamation**: publication details, defamatory statements, reputation damage
- **Money recovery**: loan details, repayment schedule, demand notice

---

## LKB Integration

Exemplars work alongside LKB entries. The LKB provides:
- Primary acts and sections to cite
- Limitation article
- Damages categories to cover
- Permitted doctrines
- Terminology mapping

The exemplar shows HOW to structure the document; LKB tells WHAT legal substance to include.

---

## Key Files

| File | What |
|------|------|
| `exemplars/` | All structural exemplars |
| `prompts/draft_prompt.py` | `load_exemplar()` function |
| `lkb/civil.py` | LKB entries per cause type |
| `lkb/__init__.py` | Cause-type aliases for fuzzy matching |

---

## Rules
- Exemplars guide STRUCTURE and TONE — not legal substance
- Keep to ~1,500 tokens (Few-Shot > Exhaustive Rules)
- Use generic `{{PLACEHOLDER}}` for all specifics — never real data
- One exemplar per cause type (naming convention: `{cause_type}.txt`)
- `_default.txt` is the fallback for unknown cause types
- Exemplar section order should match Indian court conventions for that document type

## Anti-Patterns
- Do NOT include specific amounts, dates, or names — use placeholders
- Do NOT include must_include checklists in exemplars
- Do NOT include legal arguments or doctrines — LKB handles that
- Do NOT make exemplars too long (>2,000 tokens) — diminishing returns
- Do NOT include scenario-specific instructions — exemplar is generic
- Do NOT use JSON or structured format — exemplar is plain text, exactly as filed
