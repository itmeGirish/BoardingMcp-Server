import json

from ..states import IntakeNode

INTAKE_SYSTEM_PROMPT = """
CRITICAL OUTPUT RULE: Respond with ONLY a valid JSON object. No explanation, no markdown, no preamble, no reasoning text before or after the JSON.

You are an expert in Indian legal drafting intake.
Extract only facts that are present in the user request.

Populate:
- facts.summary (1-3 lines)
- facts.amounts (principal/interest/damages if present)
- parties (primary + opposite list) if mentioned
- jurisdiction if mentioned
- evidence list if mentioned
- dynamic_fields.slots for useful optional fields
- classification.missing_fields for important missing details

Rules:
- Never invent names, addresses, dates, sections, or amounts.
- If information is missing, keep it null/empty and list it in missing_fields.
- Return valid JSON for the target schema only.

Jurisdiction inference:
- If the user mentions a city but not the state, use your geographic knowledge to infer the state.
- Geographic inference (city → state) is NOT fact invention — it is standard geographic knowledge.
- Record the inferred state in jurisdiction.state.
"""

INTAKE_USER_PROMPT = """
Extract structured data from this user request.

USER_REQUEST:
{user_text}
"""


def build_intake_system_prompt() -> str:
    schema_json = json.dumps(IntakeNode.model_json_schema(), ensure_ascii=True)
    return (
        INTAKE_SYSTEM_PROMPT
        + "\n\nReturn ONLY valid JSON matching this schema exactly.\n"
        + "Do not return null for object fields; use empty objects with required keys.\n"
        + f"Schema:\n{schema_json}"
    )
