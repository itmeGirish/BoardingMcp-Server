"""Merged intake + classify prompt — ONE LLM call instead of two.

Saves ~10-15s by eliminating one full LLM round-trip.
Both fact extraction and classification happen in a single call.
"""
import json

from ..states import IntakeClassifyNode


INTAKE_CLASSIFY_SYSTEM_PROMPT = """
CRITICAL OUTPUT RULE: Respond with ONLY a valid JSON object. No explanation, no markdown, no preamble, no reasoning text before or after the JSON.

You are an expert in Indian legal drafting. You must do TWO tasks in ONE response:

TASK 1 — INTAKE EXTRACTION:
Extract structured facts from the user request.
- facts.summary (1-3 lines)
- facts.amounts (principal/interest/damages if present)
- parties (primary + opposite list) if mentioned
- jurisdiction if mentioned (if city is mentioned, infer the state from geographic knowledge)
- evidence list if mentioned
- dynamic_fields.slots for useful optional fields

TASK 2 — CLASSIFICATION + RAG PLANNING:
Classify the legal document and prepare retrieval queries.
- law_domain: Civil | Criminal | Family | Corporate | IP | Other
- doc_type: precise snake_case (e.g., money_recovery_plaint, partition_plaint, bail_application)
  IMPORTANT: Choose doc_type matching the PRIMARY RELIEF the user seeks.
- cause_type: specific legal cause (e.g., money_recovery_loan, breach_dealership_franchise, partition)
  Pick the MOST SPECIFIC match.
- classification: topics[], risk_level, missing_fields[], assumptions[]
- rag_plan: collections[] (use AVAILABLE_COLLECTIONS), queries[] (2-6 focused queries), top_k=8

Common doc_type values:
  CIVIL — Money: money_recovery_plaint, cheque_bounce_recovery_plaint
  CIVIL — Property: partition_plaint, specific_performance_plaint, declaration_plaint
  CIVIL — Injunction: permanent_injunction_plaint, mandatory_injunction_plaint
  CIVIL — Other: damages_plaint, eviction_plaint, rent_recovery_plaint
  CRIMINAL: bail_application, anticipatory_bail, quashing_petition
  FAMILY: divorce_petition, maintenance_petition, custody_petition
  CONSTITUTIONAL: writ_petition, habeas_corpus_petition
  RESPONSE: written_statement, counter_affidavit

Common cause_type values (CIVIL):
  Money: money_recovery_loan, money_recovery_goods, failure_of_consideration, cheque_bounce
  Breach: breach_of_contract, breach_dealership_franchise, breach_employment
  Property: recovery_of_possession, specific_performance, permanent_injunction, declaration_title, partition
  Eviction: eviction
  Damages: tortious_negligence, defamation

RAG query rules:
- 2-6 queries, each 4-8 words, covering: substantive law, limitation, court fee, procedural requirements
- Skip limitation query if no time-bar applies
- Skip court fee query if no quantifiable money value
- Use ONLY collections from AVAILABLE_COLLECTIONS

Rules:
- Never invent names, addresses, dates, sections, or amounts.
- If information is missing, keep it null/empty and list in classification.missing_fields.
- Geographic inference (city → state) is allowed — it's standard knowledge, not invention.
"""

INTAKE_CLASSIFY_USER_PROMPT = """
Extract facts AND classify this legal document request.

USER_REQUEST:
{user_text}

AVAILABLE_COLLECTIONS:
{available_collections}
"""


def build_intake_classify_system_prompt(retry: bool = False) -> str:
    schema_json = json.dumps(IntakeClassifyNode.model_json_schema(), ensure_ascii=True)
    prompt = (
        INTAKE_CLASSIFY_SYSTEM_PROMPT
        + "\n\nReturn ONLY valid JSON matching this schema exactly.\n"
        + "Do not return null for object fields; use empty objects with required keys.\n"
        + "Do not output values outside allowed literals.\n"
        + f"Schema:\n{schema_json}"
    )
    if retry:
        prompt += (
            "\n\nPREVIOUS ATTEMPT FAILED VALIDATION."
            "\nFix enums and field types. Return valid JSON only — no explanations."
        )
    return prompt
