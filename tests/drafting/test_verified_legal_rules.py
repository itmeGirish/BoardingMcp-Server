from __future__ import annotations

from pathlib import Path

from app.agents.drafting_agents.lkb.causes.contract_commercial import CAUSES as CONTRACT_CAUSES
from app.agents.drafting_agents.lkb.causes.money_and_debt import CAUSES as MONEY_CAUSES
from app.agents.drafting_agents.prompts.draft_prompt import (
    build_draft_freetext_system_prompt,
    build_structured_draft_prompt,
)
from app.agents.drafting_agents.schemas.trial_court import SCHEMAS as TRIAL_SCHEMAS


_ROOT = Path(__file__).resolve().parents[2]


def _reliefs_by_subtype(entry: dict) -> dict[str, dict]:
    reliefs = {}
    for item in entry.get("available_reliefs", []):
        subtype = item.get("subtype") or item.get("type")
        reliefs[subtype] = item
    return reliefs


class TestVerifiedInterestRules:
    def test_money_recovery_reliefs_use_section_34_only_for_suit_to_decree_and_future(self):
        entry = MONEY_CAUSES["money_recovery_loan"]
        reliefs = _reliefs_by_subtype(entry)

        assert reliefs["pre_suit"]["statute"] == "Contract / usage / substantive law"
        assert reliefs["pendente_lite"]["statute"] == "S.34 CPC"
        assert reliefs["future"]["statute"] == "S.34 CPC"

    def test_contract_reliefs_split_pendente_lite_and_future_interest(self):
        entry = CONTRACT_CAUSES["breach_of_contract"]
        reliefs = _reliefs_by_subtype(entry)

        assert reliefs["pre_suit"]["statute"] == "Contract / usage / substantive law"
        assert reliefs["pendente_lite"]["statute"] == "S.34 CPC"
        assert reliefs["future"]["statute"] == "S.34 CPC"
        assert "future interest" in reliefs["future"]["prayer_text"].lower()

    def test_deposit_refund_guidance_no_longer_routes_pendente_lite_interest_to_order_20_rule_11(self):
        entry = MONEY_CAUSES["deposit_refund"]
        guidance = entry["interest_guidance"]
        prayers = " ".join(entry["prayer_template"])

        assert "Order XX Rule 11 CPC" not in guidance
        assert "Section 34 CPC governs pendente lite interest" in guidance
        assert "under Section 34 CPC" in prayers

    def test_interest_guidance_does_not_present_fixed_rate_as_statutory_default(self):
        loan_guidance = MONEY_CAUSES["money_recovery_loan"]["interest_guidance"]
        contract_guidance = CONTRACT_CAUSES["breach_of_contract"]["interest_guidance"]

        assert "12% p.a." not in loan_guidance
        assert "12-18% p.a." not in contract_guidance
        assert "legally sustainable basis" in loan_guidance
        assert "legally sustainable basis" in contract_guidance


class TestVerifiedProceduralRules:
    def test_written_statement_deadline_uses_current_non_commercial_and_commercial_position(self):
        deadline = TRIAL_SCHEMAS["written_statement"]["filing_rules"]["filing_deadline"].lower()

        assert "ordinarily within 30 days" in deadline
        assert "strict outer limit of 120 days" in deadline
        assert "max 90 days" not in deadline


class TestPromptAndTemplateFallbacks:
    def test_freetext_prompt_uses_section_34_for_pendente_lite_interest(self):
        prompt = build_draft_freetext_system_prompt("plaint")

        assert "pendente lite under Section 34 CPC" in prompt
        assert "Order XX Rule 11 CPC" not in prompt

    def test_structured_prompt_universal_rule_uses_section_34(self):
        prompt = build_structured_draft_prompt(
            lkb_entry={},
            doc_schema={
                "display_name": "Plaint",
                "filed_by": "plaintiff",
                "annexure_prefix": "P-",
                "cpc_reference": "Order VII CPC",
                "sections": [],
            },
            user_facts="Sample facts",
        )

        assert "Section 34 CPC" in prompt
        assert "Order XX Rule 11 CPC" not in prompt

    def test_template_engine_contains_no_hardcoded_order_20_rule_11_interest_rule(self):
        engine_text = (
            _ROOT
            / "app"
            / "agents"
            / "drafting_agents"
            / "templates"
            / "engine.py"
        ).read_text(encoding="utf-8")

        assert "Order XX Rule 11 CPC" not in engine_text
