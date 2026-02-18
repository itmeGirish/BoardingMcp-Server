# Legal Drafting Agent — Hardened Multi-Agent System (LangGraph)

Version: 2.0  
Runtime: Python + LangGraph  
Database: PostgreSQL 14+  (Running in docker)
Output: Court-ready Draft text

# reffernce 
Use app\agents\whatsp_agents broadcasting agent for building Multi agent

already agent is built check where they reach correct requirements

use ollama model:
reffernce app\services\llm_service.py 


Go for legal drafting workflow
before starting .claude\skills\legal-drafting-workflow\SKILL.md

check where the requirements in workflow is full filled or not,if not there plan to implement
---


## 1. Purpose

Build a court-grade legal drafting system that generates structured legal drafts with:

- zero hallucination tolerance
- verified citations only (RAG/DB-backed)
- mistake-rule learning with anti-pollution staging + promotion
- full workflow audit trail and replay support

---

## 2. Global Hard Rules (Non-Negotiable)

### 2.1 Zero Hallucination Policy
Agents must not invent facts. Every factual claim must be:
- extracted from uploaded documents, OR
- user-provided, OR
- validated with confidence ≥ 0.75

If required facts are missing → workflow must pause for clarification.

### 2.2 Citation Policy
Citations must only come from verified sources stored in database/RAG.

Any citation without:
- verified=true
- valid verification_hash  
must be discarded.

### 2.3 Mistake Rule Anti-Pollution Policy
Rules must never be written directly into `mistake_rules_main`.

All extracted candidate rules must go into `staging_rules`.

Promotion requires:
- severity medium/high
- appears in ≥ 3 distinct cases
- not case-specific
- not contradictory

### 2.4 Hard Stop Conditions
Workflow must stop and request clarification if:
- jurisdiction (state/city) missing
- classifier conflict unresolved
- unverified facts remain
- limitation date required but missing
- hard_blocks exist in merged context

---

## 3. Workflow Pipeline (18 Steps)

Step 0  → Raw Input Collection  
Step 1  → Security + Normalization (NO LLM)  
Step 2  → Supervisor Intake / Fact Extraction (LLM)  
Step 3  → Fact Validation Gate (NO LLM)  
Step 4A → Rule Classifier (NO LLM)  
Step 4B → LLM Classifier (LLM)  
Step 4C → Route Resolver (NO LLM)  
Step 5  → Clarification Handler (STOP IF REQUIRED)  
Step 6  → Mistake Rules Fetch (Main DB)  
Step 7  → Template Pack Agent (LLM)  
Step 8  → Parallel Agents: Compliance + Localization + Prayer  
Step 9  → Optional Agents: Research + Citation  
Step 10 → Citation Validation Gate (NO LLM)  
Step 11 → Context Merge + Conflict Resolver (NO LLM)  
Step 12 → Drafting Agent (LLM)  
Step 13 → Quality Agent (LLM)  
Step 14 → Store Candidate Rules (Staging DB)  
Step 15 → Promotion Gate (NO LLM)  
Step 16 → Update Main Mistake DB (NO LLM)  
Step 17 → Promotion Logging (NO LLM)  
Step 18 → Export Engine (NO LLM)

---

## 4. Skills (Claude Skill Format)

All agents are defined as Skills with:
- clear input/output JSON contracts
- restrictions
- failure conditions

---

# SKILL: supervisor_intake
---
name: supervisor_intake
description: Extract structured case facts from user input and uploaded documents.
model: kimi-k2.5
output_schema: schemas/MASTER_FACTS.schema.json
---

## Responsibilities
- extract parties and roles
- extract timeline events
- extract legal issues
- detect missing mandatory fields (jurisdiction, limitation date, court type)
- assign confidence score per extracted fact
- attach source_doc_id for every extracted fact

## Constraints
- must not invent facts
- if a fact has no source_doc_id → confidence must be < 0.75
- if jurisdiction missing → mark hard_block=true

## Output
Writes `MASTER_FACTS.json`

---

# SKILL: classifier_agent
---
name: classifier_agent
description: Classify case type and draft routing metadata.
model: glm-4.7
output_schema: schemas/LLM_CLASSIFY_OUTPUT.schema.json
---

## Responsibilities
- classify legal_domain
- classify court_type
- classify proceeding_type
- detect draft language + style

## Constraints
- must return confidence per classification label
- must not override rule_classifier output directly

## Output
Writes `LLM_CLASSIFY_OUTPUT.json`

---

# SKILL: compliance_agent
---
name: compliance_agent
description: Validate limitation, annexures, affidavit requirements, and statutory compliance.
model: glm-4.7
output_schema: schemas/COMPLIANCE_REPORT.schema.json
---

## Responsibilities
- limitation check
- mandatory annexure list
- affidavit requirements
- missing mandatory sections

## Constraints
- must not assume limitation dates
- if limitation unknown → mark needs_clarification=true

## Output
Writes `COMPLIANCE_REPORT.json`

---

# SKILL: localization_agent
---
name: localization_agent
description: Apply court and state-specific formatting conventions.
model: glm-4.7
output_schema: schemas/LOCAL_RULES.schema.json
---

## Responsibilities
- heading and court format rules
- verification clause formatting
- annexure style conventions
- date formatting rules

## Constraints
- must require state/city in input context
- if state missing → mark hard_block=true

## Output
Writes `LOCAL_RULES.json`

---

# SKILL: prayer_agent
---
name: prayer_agent
description: Generate prayer/relief pack based on extracted facts and proceeding type.
model: glm-4.7
output_schema: schemas/PRAYER_PACK.schema.json
---

## Responsibilities
- primary relief
- alternative relief
- interim relief
- costs clause

## Constraints
- must align with proceeding_type
- must not include relief not supported by facts

## Output
Writes `PRAYER_PACK.json`

---

# SKILL: research_agent
---
name: research_agent
description: Generate legal principles and argument framework (no fabricated citations).
model: kimi-k2.5
output_schema: schemas/RESEARCH_BUNDLE.schema.json
---

## Trigger
Run only if proceeding_type in:
- writ petition
- quash
- bail
- appeal
- revision

## Responsibilities
- statute framework
- legal principles summary
- argument structure
- possible grounds

## Constraints
- must not output fake citations
- must not output case numbers unless provided by verified DB

## Output
Writes `RESEARCH_BUNDLE.json`

---

# SKILL: citation_agent
---
name: citation_agent
description: Retrieve verified citations from database/RAG only.
model: kimi-k2.5
output_schema: schemas/CITATION_PACK.schema.json
---

## Trigger
Run only if:
- verified_citations DB exists
- research_agent executed
- workflow_route.agents_required includes citation_agent

## Responsibilities
- retrieve citations relevant to research bundle
- return only verified citations with verification_hash

## Constraints
- must not fabricate citations
- must return empty list if none found

## Output
Writes `CITATION_PACK.json`

---

# SKILL: drafting_agent
---
name: drafting_agent
description: Draft full legal document using merged verified context.
model: kimi-k2.5
output_schema: schemas/DRAFT_V1.schema.json
---

## Responsibilities
- follow template pack strictly
- insert prayers
- apply localization formatting
- insert compliance annexure list
- preserve placeholders for missing required data

## Constraints
- must not invent facts
- missing data must remain as placeholders like: {{MISSING_FIELD}}

## Output
Writes `DRAFT_V1.json`

---

# SKILL: quality_agent
---
name: quality_agent
description: Final QA check and generate error report + candidate mistake rules.
model: use kimi k2.5
output_schema: schemas/FINAL_DRAFT.schema.json
---

## Responsibilities
- remove inconsistencies
- verify prayers match relief structure
- verify annexure references
- generate error report
- compute quality_score (0-100)
- propose candidate mistake rules (staging only)

## Constraints
- must not invent facts or citations
- must flag all unverifiable claims
- candidate rules must be generic, not case-specific

## Outputs
Writes:
- `FINAL_DRAFT.json`
- `ERROR_REPORT.json`

---

## 5. LangGraph Execution Rules

### 5.1 Parallel Execution (Mandatory Fan-Out)
These must run in parallel:
- compliance_agent
- localization_agent
- prayer_agent

### 5.2 Conditional Execution
Run only if required by route:
- research_agent
- citation_agent

### 5.3 Stop/Resume
If clarification required:
- persist workflow_state to DB
- set drafting_sessions.status = paused
- resume only after user response

---

## 6. Mandatory Non-LLM Gates

These must be deterministic and non-LLM:

- Security Normalization Gate
- Fact Validation Gate
- Route Resolver
- Citation Validation Gate
- Context Merge + Conflict Resolver
- Promotion Gate

---

## 11. Forbidden Behavior

The system must never:
- invent facts
- invent citations
- bypass validation gates
- write directly to mistake_rules_main
- skip clarification pause
- create file paths outside the allowed map

## Remember follow the steps after builing agents

# SKILL: code Reviewer
 review code and fixes it 

skills path:
.claude\skills\code_reviewer\SKILL.md

 
# SKILL: code tester

tester is NOT an implementation agent.
tester is only responsible for testing all cases using pytest.
- .claude/skills/tester

# SKILL: lawyer_validator
as senior lawyer validates differnce use case
and suggest imporing drafting

- .claude/skills/lawyer_validator

# CRITICAL DRAFTING RULES (MANDATORY)

1. Never hardcode legal drafting content in Python:
   - Do NOT write fixed paragraphs, prayer clauses, or legal arguments directly in code.
   - Python should only handle workflow, validation gates, routing, formatting, and schema enforcement.

2. If drafting accuracy is low, improve the prompt first:
   - Prefer refining system prompts, role prompts, and drafting instructions.
   - Prefer better context extraction (facts, jurisdiction, court type) instead of adding hardcoded text.

3. Do not overload prompts with irrelevant context:
   - Avoid injecting full case history or unrelated documents into the drafting prompt.
   - Only include the minimum required facts, citations, and legal issues needed for that document type.

4. Prompt context must be structured and clean:
   - Provide facts as JSON blocks or bullet points.
   - Provide citations separately.
   - Provide missing fields explicitly.

5. Draft output must remain dynamic:
   - Draft structure must change depending on court, state, case type, and legal section.
   - Never force one fixed template for all drafts.
