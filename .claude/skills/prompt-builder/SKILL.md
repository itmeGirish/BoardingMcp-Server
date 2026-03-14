# SKILL: prompt-builder

Use when: building, reviewing, or debugging the structured prompt that combines LKB + document schema for the draft LLM.

## What Is the Prompt Builder

The prompt builder is the core of v11.0. It replaces the 400-line `_build_lkb_brief_context()` flat dump with a ~100-line structured prompt builder that combines:

1. **Document schema** → section order + per-section instructions
2. **LKB Layer 1** → legal knowledge (statutes, limitation, facts guidance)
3. **LKB Layer 2** → document components (reliefs with prayer_text, jurisdiction)
4. **User facts** → from intake

Into ONE structured prompt with clear hierarchy (~1,500 tokens).

## The Prompt Structure

```
═══ DOCUMENT STRUCTURE (follow this section order exactly) ═══
Document type: Written Statement
Filed by: Defendant
Annexure prefix: D-

Sections (in this order):
1. COURT HEADING — Court name and place
2. PRELIMINARY OBJECTIONS — Limitation, jurisdiction, non-joinder
3. PARA-WISE REPLY — Reply to EVERY plaint paragraph: ADMITTED/DENIED/NOT ADMITTED
4. ADDITIONAL FACTS — New facts in defence
5. PRAYER — Dismiss suit with costs
6. VERIFICATION — Verification on oath

═══ LEGAL DATA (cite ONLY from this) ═══
Cause: Suit for Damages for Breach of Contract
Statutes to cite:
  - Indian Contract Act, 1872: Section 73
  - Code of Civil Procedure, 1908: Section 20
Limitation: Article 55 — Three years from date of breach
Reliefs:
  - Decree for damages of Rs.{{AMOUNT}} (S.73 ICA)
  - Interest at {{RATE}}% per annum (S.34 CPC)
  - Pendente lite and future interest (Order XX Rule 11 CPC)
  - Costs of the suit (S.35 CPC)

═══ FACTS GUIDANCE ═══
MUST COVER:
  - Date and terms of contract
  - Consideration paid/exchanged
  - Specific breach
  - Loss with quantification
  - Mitigation efforts
DO NOT:
  - Cite Section/Act numbers in FACTS section
  - Use "on or about" for dates
  - Mix S.73 and S.74 ICA

═══ CLIENT FACTS ═══
[user's actual request/facts from intake]

═══ UNIVERSAL RULES ═══
1. Cite ONLY from the statutes listed above
2. Do NOT include case law citations — use {{CASE_LAW_NEEDED: [topic]}}
3. Every document reference must use annexure label (D-1, D-2...)
4. Verification must distinguish personal knowledge from information
```

## Why This Is Better Than Current

| Current (`_build_lkb_brief_context`) | New (structured prompt) |
|--------------------------------------|------------------------|
| 400 lines, 13 categories | 100 lines, 4 sections |
| Flat text, no hierarchy | Clear hierarchy with separators |
| All instructions at equal priority | Structure > Law > Facts > Rules |
| ~3,000 tokens | ~1,500 tokens |
| Same for all document types | Adapts per document type |
| Prayer as prose instructions | Prayer as exact text with statutes |
| LLM decides structure | Schema enforces structure |

## Implementation

```python
def build_draft_prompt(lkb_entry, doc_schema, user_facts, decision_ir=None):
    """Build structured prompt from LKB + schema.

    ~100 lines. Replaces _build_lkb_brief_context() (400 lines).
    """
    parts = []

    # Section 1: Document structure (from schema)
    parts.append("═══ DOCUMENT STRUCTURE (follow this section order exactly) ═══")
    parts.append(f"Document type: {doc_schema['display_name']}")
    parts.append(f"Filed by: {doc_schema['filed_by']}")
    parts.append(f"Annexure prefix: {doc_schema['annexure_prefix']}")
    parts.append("\nSections (in this order):")
    for i, section in enumerate(doc_schema['sections'], 1):
        parts.append(f"  {i}. {section['key'].upper()} — {section['instruction']}")

    # Section 2: Legal data (from LKB Layer 1 + 2)
    parts.append("\n═══ LEGAL DATA (cite ONLY from this) ═══")
    parts.append(f"Cause: {lkb_entry['display_name']}")
    parts.append(format_acts(lkb_entry['primary_acts']))
    parts.append(format_limitation(lkb_entry['limitation']))
    parts.append(format_reliefs(lkb_entry.get('available_reliefs', [])))

    # Section 3: Facts guidance (from LKB Layer 1)
    parts.append("\n═══ FACTS GUIDANCE ═══")
    if lkb_entry.get('facts_must_cover'):
        parts.append("MUST COVER:")
        for f in lkb_entry['facts_must_cover']:
            parts.append(f"  - {f}")
    if lkb_entry.get('drafting_red_flags'):
        parts.append("DO NOT:")
        for r in lkb_entry['drafting_red_flags']:
            parts.append(f"  - {r}")

    # Section 4: Client facts
    parts.append(f"\n═══ CLIENT FACTS ═══\n{user_facts}")

    return "\n".join(parts)
```

## Key File
- Current: `app/agents/drafting_agents/nodes/draft_single_call.py` → `_build_lkb_brief_context()` (lines 176-400)
- Target: `app/agents/drafting_agents/prompts/draft_prompt.py` → `build_draft_prompt()` (~100 lines)

## Rules
- Prompt hierarchy: STRUCTURE > LAW > FACTS > RULES (never flat)
- Keep total prompt under ~2,000 tokens
- Use visual separators (═══) between sections
- Schema drives section order — prompt just formats it
- LKB drives legal content — prompt just formats it
- Universal rules appended at end (lowest priority)
- Do NOT dump raw LKB dict — format each field clearly
- Do NOT include fields the LLM doesn't need (complexity_weight, registry_kind, etc.)
