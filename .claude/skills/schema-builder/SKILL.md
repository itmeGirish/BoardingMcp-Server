# SKILL: schema-builder

Use when: creating, reviewing, or modifying document schemas for the v11.0 pipeline. Covers all 12 civil document types.

## What Are Document Schemas

Document schemas define the STRUCTURE of a legal document — section order, per-section instructions, filing rules. They are INDEPENDENT of cause type.

Same schema works for ALL 92 cause types. One schema per document type.

## The 12 Civil Document Schemas

| # | Document Type | CPC Reference | Filed By | Annexure Prefix |
|---|--------------|---------------|----------|-----------------|
| 1 | plaint | Order VII | plaintiff | P- |
| 2 | written_statement | Order VIII | defendant | D- |
| 3 | rejoinder | Order VIII Rule 2 | plaintiff | P- |
| 4 | counter_claim | Order VIII Rule 6A-6G | defendant | D- |
| 5 | interim_application | Order XXXIX / XXXVIII / XL | either | Annexure- |
| 6 | execution_application | Order XXI | decree_holder | Annexure- |
| 7 | appeal_memo | Order XLI Rule 1 | appellant | Annexure- |
| 8 | revision_petition | S.115 CPC | aggrieved_party | Annexure- |
| 9 | review_petition | Order XLVII, S.114 CPC | aggrieved_party | Annexure- |
| 10 | condonation_of_delay | S.5 Limitation Act | applicant | Annexure- |
| 11 | set_aside_ex_parte | Order IX Rule 13 | defendant | Annexure- |
| 12 | caveat | S.148A CPC | caveator | Annexure- |

## Schema Structure

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
        {"key": "court_heading",          "instruction": "Court name and place"},
        {"key": "preliminary_objections", "instruction": "Limitation, jurisdiction, non-joinder"},
        {"key": "parawise_reply",         "instruction": "Reply to EVERY plaint paragraph"},
        {"key": "additional_facts",       "instruction": "New facts in defence"},
        {"key": "prayer",                 "instruction": "Dismiss suit with costs"},
        {"key": "verification",           "instruction": "Verification on oath"},
    ],

    "filing_rules": {
        "court_fee": False,
        "filing_deadline": "30 days (max 120 days — Order VIII Rule 1)",
    },
}
```

## Creating a New Schema

1. Read the CPC/statute reference for that document type
2. List ALL required sections in court-standard order
3. Write per-section `instruction` — what that section must contain
4. Set metadata: `filed_by`, `annexure_prefix`, `verification_type`
5. Add `filing_rules` (deadline, court fee, certified copy needed)
6. Verify against actual court documents / CPC text
7. Add to appropriate file in `schemas/` directory
8. Test with pipeline

## Files

```
app/agents/drafting_agents/schemas/
├── __init__.py      # DOCUMENT_SCHEMAS registry + lookup
├── trial_court.py   # plaint, written_statement, rejoinder, counter_claim
├── applications.py  # interim_application, condonation, set_aside, caveat
├── appellate.py     # appeal_memo, revision_petition, review_petition
└── execution.py     # execution_application
```

## Rules
- ONE schema per document type (not per cause type)
- Schema defines STRUCTURE only — not legal substance
- Verify section order against CPC text
- Wrong schema structure = court rejects document
- Schema is independent of cause type — same for all 92 causes
- Keep `instruction` field concise — tells LLM what goes in that section
