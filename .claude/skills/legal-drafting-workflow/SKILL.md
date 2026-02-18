

# 🚀 How the Workflow Runs

## 1. User Input
User provides:
- query text
- optional uploaded docs
- optional preferences

Saved as:
- `USER_INPUT.json`

## 2. Sanitization
Security normalization cleans prompt injection and unsafe characters.

Output:
- `SANITIZED_INPUT.json`

## 3. Supervisor Fact Extraction
Extracts parties, facts, issues, timeline.

Output:
- `MASTER_FACTS.json`

## 4. Fact Validation Gate
Blocks unverified facts.

Output:
- `FACT_VALIDATION_REPORT.json`

If blocked → workflow pauses and asks user.

## 5. Dual Classification
- Rule classifier (fast)
- LLM classifier (semantic)

Then route resolver decides final route.

Output:
- `WORKFLOW_ROUTE.json`

## 6. Mistake Rules Fetch
Fetches reusable objection patterns from main DB.

Output:
- `MISTAKE_CHECKLIST.json`

## 7. Template Pack Generation
Creates structure + mandatory clauses.

Output:
- `TEMPLATE_PACK.json`

## 8. Parallel Agents
Runs in parallel:
- Compliance
- Localization
- Prayer

Outputs:
- `COMPLIANCE_REPORT.json`
- `LOCAL_RULES.json`
- `PRAYER_PACK.json`

## 9. Optional Agents
Conditionally runs:
- Research agent
- Citation agent

Outputs:
- `RESEARCH_BUNDLE.json`
- `CITATION_PACK.json`

## 10. Citation Validation Gate
Drops unsafe citations.

Output:
- `CITATION_VALIDATION_REPORT.json`

## 11. Context Merge
Merges all outputs into unified draft context.

Output:
- `DRAFT_CONTEXT.json`

If hard_blocks exist → workflow pauses.

## 12. Draft Generation
Drafting agent generates Draft V1.

Output:
- `DRAFT_V1.json`

## 13. Quality Review
Final QA ensures court-grade output.

Outputs:
- `FINAL_DRAFT.json`
- `ERROR_REPORT.json`

## 14–17 Mistake DB Learning Loop
- store candidate rules in staging
- promote repeated rules
- update main DB
- log promotion decisions

## 18. Export
Final draft exported to DOCX/PDF.

Output:
- `EXPORT_OUTPUT.json`

---

# 🗄️ Database Tables (Core)

- `drafting_sessions`
- `master_facts`
- `agent_outputs`
- `validation_reports`
- `verified_citations`
- `draft_versions`
- `mistake_rules_main`
- `staging_rules`
- `promotion_logs`
- `clarification_history`

---

# 🔍 Observability + Audit Trail

This system is designed for legal audit safety.

Every workflow run stores:
- step execution times
- full intermediate outputs
- validation reports
- stop events
- clarification history
- promotion decisions

This enables replay + debugging for court liability defense.

---

# 🧪 Testing Strategy

## Required Tests
- Unit tests per agent output schema
- Unit tests for gates (validation logic)
- Integration tests for full pipeline
- Parallel execution tests (Step 8)
- Hard stop tests (Steps 3, 5, 11)
- Promotion gate tests (>=3 cases rule)
- Citation hash verification tests
- Export tests (DOCX/PDF)

---

# 📌 Success Metrics

- Hallucination Rate: **0%**
- Citation Accuracy: **100% verified**
- Compliance Pass Rate: **95%+**
- Draft Generation Time: **< 5 minutes**
- Quality Score: **90%+**
- Clarification Rate: **< 20% sessions**
- Promotion Rate: **10–15%**
- Workflow Completion Rate: **95%+**

---

# 🔑 Key Implementation Rules

## Non-Negotiable Rules
- Never draft with unverified facts
- Never generate citations
- Never write directly to main mistake DB
- Never skip hard stop conditions
- Always log validation decisions

---

# 📄 Reference Documentation

- Claude Skills Overview  
  https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

- LangGraph Workflows & Parallelization  
  https://docs.langchain.com/oss/python/langgraph/workflows-agents

- DeepAgents (Research Agent Pattern)  
  https://docs.langchain.com/oss/python/deepagents/overview

---

# 📌 License
This project is intended for internal legal automation and compliance usage.
Not legal advice. Human review recommended for sensitive filings.
