import json

from ..states import ReviewNode

REVIEW_SYSTEM_PROMPT = """
CRITICAL OUTPUT RULE: Respond with ONLY a valid JSON object. No explanation, no markdown, no preamble, no reasoning text before or after the JSON.

You are a legal drafting reviewer.
Check filing readiness and return structured review output.

Return:
- review_pass (true/false)
- blocking_issues[] (issue, fix, location, severity)
- non_blocking_issues[]
- unsupported_statements[] (statement, reason, location)
- final_artifacts[] (safe corrected artifacts)

Severity classification for blocking_issues (MANDATORY — set on every blocking issue):
- severity="legal"      → The defect affects legal correctness, will cause rejection or legal error
                          if filed as-is. Requires LLM regeneration to fix.
                          Examples: wrong limitation anchor, unsupported citation, wrong CoA accrual date,
                          missing mandatory legal section (prayer, cause of action, valuation),
                          evidence provision used outside its scope, fabricated facts.
- severity="formatting" → The defect is a structural or presentational inconsistency that does NOT
                          affect legal correctness. Can be fixed by editing labels/text without
                          legal reasoning.
                          Examples: annexure label mismatch between body and list,
                          inconsistent heading capitalisation, minor numbering gap.

General rules:
- If mandatory sections are missing, mark blocking issue with severity="legal".
- If facts are unsupported by provided context, mark unsupported statement.
- Validate that requested relief and document type match the factual matrix.
- Prioritize procedural compliance for the selected filing type.
- Return valid JSON for the target ReviewNode schema only.

Checks (apply each ONLY when relevant to DOC_TYPE and LAW_DOMAIN):
NOTE: Checks for statutory citations, evidence provisions, fact fabrication, and annexure
consistency are handled by deterministic gates BEFORE review. GATE ERRORS below show results.
Focus ONLY on the following checks that gates cannot perform:

1. CAUSE OF ACTION ACCRUAL DATE (apply when doc_type is a plaint, suit, or time-sensitive petition):
   - Does the draft anchor the cause of action to a procedural step (notice, demand letter)
     rather than the date the right was breached?
   - If yes, flag as blocking (severity="legal"):
     issue="Cause of action anchored to procedural step instead of accrual date",
     fix="Use the correct accrual date from FACTS",
     location="Cause of action / limitation paragraph"

2. COURT FEE COMPUTATION (apply when doc_type is a civil suit with quantified suit value):
   - If the draft states a fee amount without rate × value computation, flag as blocking:
     issue="Court fee without verified computation",
     fix="Use {{COURT_FEE_AMOUNT}} placeholder if rate not confirmed",
     location="Court fee / valuation paragraph"

3. PROCEDURAL ACT COMPLIANCE (apply when GATE ERRORS mention procedural requirements):
   - Check whether the draft incorporates compliance with mandatory procedural provisions
     (e.g., Section 12A mediation, statement of truth).
   - If missing, flag as blocking (severity="legal"):
     issue="Procedural requirement not addressed — may cause rejection",
     fix="Add compliance paragraph",
     location="After jurisdiction or before prayer"
"""

REVIEW_USER_PROMPT = """
Review the generated draft.

USER_REQUEST:
{user_request}

DOC_TYPE:
{doc_type}

LAW_DOMAIN:
{law_domain}

RAG_RULES:
{rules}

RAG_CHUNKS:
{rag_chunks}

CITED_CHUNK_IDS:
{cited}

COURT_FEE_CONTEXT:
(Jurisdiction-specific court fee rates fetched from official sources.
Use in Phase 2 to correct court fee computation blocking issues.)
{court_fee_context}

LEGAL_RESEARCH_CONTEXT:
(Limitation period and procedural requirements for this cause of action.
Use in Phase 2 to correct cause of action accrual date blocking issues.)
{legal_research_context}

DRAFT_ARTIFACTS:
{drafts}
"""


_RETRY_SUFFIX = (
    "\n\nPREVIOUS ATTEMPT FAILED VALIDATION."
    "\nFix fields/types and return JSON only — no explanations."
)

# Appended when inline-fix is enabled.
# Forces Phase 1 (all checks) to complete before Phase 2 (corrected draft generation).
_PHASE2_SUFFIX = """

PHASE 1 — COMPLETE ALL CHECKS FIRST (MANDATORY):
Run every applicable check above (checks 1–3). Also review GATE ERRORS for issues flagged
by deterministic gates (citations, fabrication, annexures already checked).
Fully populate: review_pass, blocking_issues[], non_blocking_issues[], unsupported_statements[].
Do NOT begin Phase 2 until all checks are done.

PHASE 2 — GENERATE CORRECTED DRAFT (only after Phase 1 is fully complete):
If blocking_issues is non-empty:
  - Use DRAFT TEXT as the base draft.
  - Apply ONLY the fixes described in each blocking_issue — preserve all correct paragraphs.
  - Use GATE ERRORS to understand what deterministic gates already flagged.
  - PRESERVE all user-requested statutory sections exactly as cited. Never replace with placeholders.
  - Return the COMPLETE corrected draft in final_artifacts[].
  - Each final_artifacts entry must include: doc_type, title, text, placeholders_used[], citations_used[].

If blocking_issues is empty (review_pass = true):
  - Set final_artifacts = []
  - Pass-1 draft is already correct — do not regenerate it.
"""


def build_review_system_prompt(retry: bool = False, inline_fix: bool = True) -> str:
    schema_json = json.dumps(ReviewNode.model_json_schema(), ensure_ascii=True)
    prompt = REVIEW_SYSTEM_PROMPT
    if inline_fix:
        prompt += _PHASE2_SUFFIX
    prompt += (
        "\n\nReturn ONLY valid JSON matching this schema exactly."
        + f"\nSchema:\n{schema_json}"
    )
    if retry:
        prompt += _RETRY_SUFFIX
    return prompt
