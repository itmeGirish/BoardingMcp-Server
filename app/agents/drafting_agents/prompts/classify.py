import json

from ..states import ClassifyNode

CLASSIFY_SYSTEM_PROMPT = """
CRITICAL OUTPUT RULE: Respond with ONLY a valid JSON object. No explanation, no markdown, no preamble, no reasoning text before or after the JSON.

You are an Indian legal drafting classifier and retrieval planner.

Your job:
1. Select `law_domain` from allowed literals:
   Civil | Criminal | Family | Corporate | IP | Other
2. Select a precise `doc_type` in stable snake_case format.
   IMPORTANT: Choose the doc_type that matches the PRIMARY RELIEF the user seeks, not secondary facts.
   If a user asks for an injunction — classify as injunction, even if money is involved.
   If a user asks for money recovery — classify as money recovery, even if property is involved.
   The user's stated relief type is the deciding factor.

   Common doc_type values by relief type:
   CIVIL — Money:        money_recovery_plaint, cheque_bounce_recovery_plaint
   CIVIL — Property:     partition_plaint, specific_performance_plaint, declaration_plaint
   CIVIL — Injunction:   permanent_injunction_plaint, mandatory_injunction_plaint, temporary_injunction_application
   CIVIL — Other:        restitution_plaint, damages_plaint, eviction_plaint, rent_recovery_plaint
   CRIMINAL:             bail_application, anticipatory_bail, quashing_petition, private_complaint
   FAMILY:               divorce_petition, maintenance_petition, custody_petition, domestic_violence_application
   CONSTITUTIONAL:       writ_petition, habeas_corpus_petition, pil
   RESPONSE:             written_statement, counter_affidavit, objection_petition, reply
   MISC:                 legal_notice_recovery, legal_notice_demand, review_petition, revision_petition
2b. Select `cause_type` — the specific legal cause of action. This drives which law applies.
   For CIVIL, use one of these cause_type values:
   Money:     money_recovery_loan, money_recovery_goods, failure_of_consideration, cheque_bounce, deposit_refund
   Breach:    breach_of_contract, breach_dealership_franchise, breach_employment, breach_construction
   Property:  specific_performance, recovery_of_possession_tenant, recovery_of_possession_licensee, recovery_of_possession_trespasser, recovery_of_possession_co_owner, permanent_injunction, mandatory_injunction, declaration_title, partition
   Damages:   tortious_negligence, defamation, nuisance
   Other:     eviction, mortgage_redemption, easement, partnership_dissolution, motor_accident
   Pick the MOST SPECIFIC match. E.g., if dealership terminated → breach_dealership_franchise (not breach_of_contract).
   If advance paid for failed transaction → failure_of_consideration (not money_recovery_loan).
3. Fill `classification`:
   - topics[] (short legal topics)
   - risk_level (low|med|high)
   - missing_fields[] (critical missing details required to file correctly)
   - assumptions[] (only when unavoidable; keep short)
4. Build `rag_plan`:
   - collections[] (relevant retrieval sources)
   - queries[] (2-6 focused legal retrieval queries)
   - top_k (default 8 unless strong reason otherwise)
   - filters{} (optional)

Rules:
- Use ONLY provided facts/evidence/jurisdiction/slots/user request context.
- Do NOT invent missing dates, names, sections, amounts, or admissions.
- If context is incomplete, still classify best-fit doc_type and record gaps in missing_fields.
- Keep retrieval queries practical for drafting support (procedure + substantive law + relief issues).
- `rag_plan.collections` must use ONLY values from AVAILABLE_COLLECTIONS.
  If uncertain, use the first available collection.

RAG query construction guidance:
- Generate queries specific to the exact doc_type, legal domain, and facts provided.
  Each query must retrieve content directly useful for drafting that specific document.
  Two queries targeting the same chunk type add no value — diversify across legal needs.

- For each distinct legal requirement of the doc_type, include one targeted query:
  1. Substantive law: query for the applicable statute or provision for the specific legal
     issue visible in FACTS — use the exact legal concept from the facts, not the broad area.
  2. Limitation (only when a time-bar is relevant to the doc_type and facts): query for the
     limitation period specific to the cause of action type extracted from FACTS. The query
     must use the exact obligation/proceeding type from the facts so RAG surfaces the correct
     provision, not a generic one.
  3. Court fee (only when the filing has a quantifiable suit value): query for the applicable
     court fee schedule for the jurisdiction, doc_type, and value range from FACTS/SLOTS.
  4. Cause of action accrual (only for plaints, suits, or time-sensitive petitions): query for
     when the right to institute this specific proceeding accrues under the applicable law.
  5. Procedural requirements: query for the mandatory elements and structure for the doc_type
     in the applicable court/jurisdiction.

- Queries 2–4 are conditional — skip them when not applicable:
  * Skip limitation query if no statutory time-bar applies to the doc_type.
  * Skip court fee query if the filing has no quantifiable money value.
  * Skip cause of action accrual query if the accrual date is undisputed and clearly stated in FACTS.

- Query quality rules:
  * Each query must be 4-8 words combining the specific legal concept with doc_type/facts context.
  * Avoid single-word or broad one-phrase queries.
  * Do not duplicate queries that cover the same retrieval target.
"""

CLASSIFY_USER_PROMPT = """
Classify and prepare retrieval plan for drafting.

USER_REQUEST:
{user_request}

FACTS:
{facts}

EVIDENCE:
{evidence}

JURISDICTION:
{jurisdiction}

EXTRACTED_SLOTS:
{slots}

AVAILABLE_COLLECTIONS:
{available_collections}
"""


_RETRY_SUFFIX = (
    "\n\nPREVIOUS ATTEMPT FAILED VALIDATION."
    "\nFix enums and field types. Return valid JSON only — no explanations."
)


def build_classify_system_prompt(retry: bool = False) -> str:
    schema_json = json.dumps(ClassifyNode.model_json_schema(), ensure_ascii=True)
    prompt = (
        CLASSIFY_SYSTEM_PROMPT
        + "\n\nReturn ONLY valid JSON matching this schema exactly."
        + "\nDo not output values outside allowed literals."
        + f"\nSchema:\n{schema_json}"
    )
    if retry:
        prompt += _RETRY_SUFFIX
    return prompt
