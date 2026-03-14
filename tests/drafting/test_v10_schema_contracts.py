from __future__ import annotations

import json
from pathlib import Path


_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "app" / "agents" / "drafting_agents" / "schemas"


def _load_schema(name: str) -> dict:
    return json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))


class TestSchemaJsonFiles:
    def test_review_findings_schema_matches_runtime_wrapper(self):
        schema = _load_schema("review_findings.schema.json")

        assert schema["required"] == ["review"]
        assert schema["properties"]["review"]["$ref"] == "#/definitions/review"

        review_props = schema["definitions"]["review"]["properties"]
        assert "unsupported_statements" in review_props
        assert "final_artifacts" in review_props

    def test_section_template_schema_covers_runtime_fields(self):
        schema = _load_schema("section_template.schema.json")
        section_props = schema["definitions"]["section"]["properties"]

        assert "condition" in section_props
        assert "examples" in section_props
        assert "Constitutional" not in schema["properties"]["law_domain"]["enum"]

    def test_filled_section_claim_types_match_claim_ledger(self):
        filled = _load_schema("filled_section.schema.json")
        ledger = _load_schema("claim_ledger.schema.json")

        filled_enum = set(filled["definitions"]["claim_entry"]["properties"]["claim_type"]["enum"])
        ledger_enum = set(ledger["items"]["properties"]["claim_type"]["enum"])

        assert filled_enum == ledger_enum


class TestSchemaContracts:
    def test_validate_template_payload_accepts_examples_and_condition(self):
        from app.agents.drafting_agents.schema_contracts import validate_template_payload

        template = {
            "template_id": "civil/test",
            "template_version": "1.1",
            "doc_type": "money_recovery_plaint",
            "law_domain": "Civil",
            "party_labels": {"primary": "Plaintiff", "opposite": "Defendant"},
            "sections": [
                {
                    "section_id": "interest",
                    "heading": "INTEREST",
                    "type": "llm_fill",
                    "instruction": "Draft the interest section.",
                    "condition": "monetary_claim",
                    "examples": {
                        "bad": "Defendant should pay interest.",
                        "good": "Award pre-suit, pendente lite, and future interest."
                    }
                }
            ],
        }

        assert validate_template_payload(template) == []

    def test_validate_template_payload_rejects_unsupported_condition(self):
        from app.agents.drafting_agents.schema_contracts import validate_template_payload

        template = {
            "template_id": "civil/test",
            "template_version": "1.1",
            "doc_type": "plaint",
            "law_domain": "Civil",
            "party_labels": {"primary": "Plaintiff", "opposite": "Defendant"},
            "sections": [
                {
                    "section_id": "interest",
                    "heading": "INTEREST",
                    "type": "llm_fill",
                    "instruction": "Draft the interest section.",
                    "condition": "unknown_condition"
                }
            ],
        }

        errors = validate_template_payload(template)
        assert any("unsupported condition" in error for error in errors)

    def test_evaluate_section_condition_supports_semantic_conditions(self):
        from app.agents.drafting_agents.schema_contracts import evaluate_section_condition

        assert evaluate_section_condition(
            "monetary_claim",
            doc_type="money_recovery_plaint",
            context={"facts": {"amounts": {"principal": 1000}}},
        )
        assert evaluate_section_condition(
            "immovable_property",
            doc_type="partition_plaint",
            context={},
        )
        assert not evaluate_section_condition(
            "immovable_property",
            doc_type="money_recovery_plaint",
            context={"facts": {"amounts": {"principal": 1000}}},
        )


class TestFallbackRoutes:
    def test_template_loader_falls_back_to_draft_freetext(self, monkeypatch):
        from app.agents.drafting_agents.nodes import template_loader as mod

        monkeypatch.setattr(mod, "_load_template", lambda _doc_type: None)
        result = mod.template_loader_node({"classify": {"doc_type": "unknown_doc"}})

        assert result.goto == "draft_freetext"

    def test_outline_validator_falls_back_to_draft_freetext(self):
        from app.agents.drafting_agents.nodes.outline_validator import outline_validator_node

        result = outline_validator_node({"template": None})
        assert result.goto == "draft_freetext"


class TestSchemaRegistry:
    def test_variant_doc_type_resolves_to_generic_plaint_schema(self):
        from app.agents.drafting_agents.schemas import get_schema

        schema = get_schema("money_recovery_plaint")
        assert schema is not None
        assert schema["code"] == "plaint"

    def test_written_statement_deadline_uses_correct_rule(self):
        from app.agents.drafting_agents.schemas import get_schema

        schema = get_schema("written_statement")
        assert schema is not None

        deadline = schema["filing_rules"]["filing_deadline"].lower()
        assert "ordinarily within 30 days" in deadline
        assert "strict outer limit of 120 days" in deadline
        assert "max 90 days" not in deadline
