"""v9.0 Anti-Fabrication Tests — prompt changes, review check, LKB fallback.

Tests the architectural changes that prevent fact fabrication:
  1. Draft prompt: Q1-Q10 removed, anti-fabrication rule present
  2. Freetext prompt: 14 rules → 5 rules, anti-fabrication rule present
  3. Review prompt: Q1-Q10 removed, fact fabrication check (check 7) added
  4. LKB fallback: honest "unknown" instead of empty string
  5. build_draft_system_prompt no longer uses Q-rule helpers

Run:  pytest tests/drafting/test_v9_antifab.py -v
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, ".")


# ===========================================================================
# A) Draft Prompt — Anti-Fabrication Rule
# ===========================================================================

class TestDraftPromptAntiFabrication:
    """Verify v4.0 system prompt has anti-fabrication rule and no Q-rules."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.prompts.draft_prompt import (
            _SYSTEM_TEMPLATE,
            build_draft_system_prompt,
        )
        self._template = _SYSTEM_TEMPLATE
        self._build = build_draft_system_prompt

    def test_anti_fabrication_rule_present(self):
        """Anti-fabrication rule must be in the system template."""
        assert "ANTI-FABRICATION" in self._template

    def test_anti_fabrication_highest_priority(self):
        """Anti-fabrication must be Rule 1 (highest priority)."""
        assert "1. ANTI-FABRICATION (HIGHEST PRIORITY)" in self._template

    def test_no_minimum_paragraph_count(self):
        """No '8-10' or 'at least 8' paragraph minimums."""
        assert "8-10" not in self._template
        assert "at least 8" not in self._template
        assert "at least 5 Annexures" not in self._template

    def test_no_q_rules(self):
        """Q1-Q10 section quality requirements must be removed."""
        for q in ["Q1.", "Q2.", "Q3.", "Q4.", "Q5.", "Q6.", "Q7.", "Q8.", "Q9.", "Q10."]:
            assert q not in self._template, f"Found {q} in system template — should be removed"

    def test_no_section_quality_requirements_header(self):
        """SECTION QUALITY REQUIREMENTS header must be removed."""
        assert "SECTION QUALITY REQUIREMENTS" not in self._template

    def test_placeholder_instruction_present(self):
        """Must instruct to use PLACEHOLDER for missing details."""
        assert "PLACEHOLDER" in self._template

    def test_shorter_accurate_instruction(self):
        """Must say shorter accurate > longer fabricated."""
        assert "shorter accurate" in self._template.lower()

    def test_only_five_rules(self):
        """Template should have exactly 5 rules (numbered 1-5)."""
        assert "1. ANTI-FABRICATION" in self._template
        assert "2. Do NOT fabricate" in self._template
        assert "3. Number paragraphs" in self._template
        assert "4. NEVER cite repealed" in self._template
        assert "5. If PROCEDURAL" in self._template
        # No rule 6
        assert "\n6." not in self._template

    def test_do_not_invent_annexures(self):
        """Must instruct not to invent Annexures."""
        assert "Do NOT invent Annexures" in self._template

    def test_court_fee_placeholder(self):
        """Must instruct to use placeholder for unverified court fee."""
        assert "COURT_FEE_AMOUNT" in self._template

    def test_build_function_no_q_rule_args(self):
        """build_draft_system_prompt should not reference Q-rule variables."""
        import inspect
        src = inspect.getsource(self._build)
        assert "relief_quality_rules" not in src
        assert "coa_quality_rules" not in src
        assert "_MONETARY_RELIEF_RULES" not in src
        assert "_NON_MONETARY_RELIEF_RULES" not in src
        assert "_CONTINUING_COA_RULES" not in src
        assert "_SINGLE_EVENT_COA_RULES" not in src

    def test_build_returns_string(self):
        """build_draft_system_prompt returns a non-empty string."""
        result = self._build("civil_suit", "money_recovery")
        assert isinstance(result, str)
        assert len(result) > 100

    def test_build_contains_anti_fabrication(self):
        """Built prompt contains anti-fabrication rule."""
        result = self._build("civil_suit")
        assert "ANTI-FABRICATION" in result


# ===========================================================================
# B) Freetext Prompt — Anti-Fabrication Rule
# ===========================================================================

class TestFreetextPromptAntiFabrication:
    """Verify v5.0 freetext prompt has anti-fabrication rule and max 5 rules."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.prompts.draft_prompt import (
            _FREETEXT_SYSTEM_TEMPLATE,
            build_draft_freetext_system_prompt,
        )
        self._template = _FREETEXT_SYSTEM_TEMPLATE
        self._build = build_draft_freetext_system_prompt

    def test_anti_fabrication_rule_present(self):
        """Anti-fabrication rule must be in the freetext template."""
        assert "ANTI-FABRICATION" in self._template

    def test_anti_fabrication_highest_priority(self):
        """Anti-fabrication must be Rule 1."""
        assert "1. ANTI-FABRICATION (HIGHEST PRIORITY)" in self._template

    def test_no_minimum_paragraph_count(self):
        """No paragraph minimums in freetext template."""
        assert "at least 8" not in self._template
        assert "8-10" not in self._template

    def test_no_old_rules_11_through_14(self):
        """Old rules 11-14 must be removed."""
        assert "\n11." not in self._template
        assert "\n12." not in self._template
        assert "\n13." not in self._template
        assert "\n14." not in self._template

    def test_only_five_rules(self):
        """Freetext template should have exactly 5 rules."""
        assert "1. ANTI-FABRICATION" in self._template
        assert "2. Do NOT fabricate" in self._template
        assert "3. Number paragraphs" in self._template
        assert "4. NEVER cite repealed" in self._template
        assert "5. If PROCEDURAL" in self._template
        # Rule 6 must NOT exist
        lines = self._template.split("\n")
        rule_6_lines = [l for l in lines if l.strip().startswith("6.")]
        assert len(rule_6_lines) == 0, f"Found rule 6: {rule_6_lines}"

    def test_do_not_invent_documents(self):
        """Must instruct not to invent documents."""
        assert "do NOT invent" in self._template

    def test_shorter_accurate_instruction(self):
        """Must say shorter accurate > longer fabricated."""
        assert "shorter accurate" in self._template.lower()

    def test_facts_law_separation_present(self):
        """Facts vs law separation instruction still present."""
        assert "legal analysis belongs in LEGAL BASIS" in self._template

    def test_build_returns_string(self):
        """build_draft_freetext_system_prompt returns a non-empty string."""
        result = self._build("civil_suit")
        assert isinstance(result, str)
        assert len(result) > 100
        assert "ANTI-FABRICATION" in result


# ===========================================================================
# C) Review Prompt — Fact Fabrication Check
# ===========================================================================

class TestReviewPromptFactCheck:
    """Verify review prompt has fact fabrication check and Q-rules removed."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.prompts.review import (
            REVIEW_SYSTEM_PROMPT,
            build_review_system_prompt,
            _PHASE2_SUFFIX,
        )
        self._prompt = REVIEW_SYSTEM_PROMPT
        self._build = build_review_system_prompt
        self._phase2 = _PHASE2_SUFFIX

    def test_no_q_rules(self):
        """Q1-Q10 quality checks must be removed from review prompt."""
        for label in [
            "Q1. NARRATIVE FACTS CHECK",
            "Q2. FACTS vs LAW SEPARATION",
            "Q3. DRAFTING-NOTES LANGUAGE",
            "Q4. CAUSE OF ACTION STRENGTH",
            "Q5. JURISDICTION SPECIFICITY",
            "Q6. INTEREST JUSTIFICATION",
            "Q7. PRAYER SPECIFICITY",
            "Q8. LEGAL TRIGGER EXPLANATION",
            "Q9. DEFENSIVE PLEADING",
            "Q10. AND/OR USAGE",
        ]:
            assert label not in self._prompt, f"Found {label} — should be removed"

    def test_fact_fabrication_check_present(self):
        """Check 7 (FACT FABRICATION CHECK) must be present."""
        assert "7. FACT FABRICATION CHECK" in self._prompt

    def test_fact_fabrication_is_critical(self):
        """Fact fabrication check must be marked CRITICAL."""
        assert "CRITICAL" in self._prompt.split("7. FACT FABRICATION CHECK")[1][:50]

    def test_fabrication_check_has_examples(self):
        """Must include examples of fabrication."""
        assert "Plaintiff accompanied Defendant" in self._prompt
        assert "thumb impression" in self._prompt

    def test_fabrication_threshold(self):
        """3+ fabricated facts should trigger blocking issue."""
        assert "3+ fabricated facts" in self._prompt

    def test_fabrication_severity_legal(self):
        """Fabrication blocking issue must be severity=legal."""
        section = self._prompt.split("7. FACT FABRICATION CHECK")[1]
        assert 'severity="legal"' in section

    def test_unsupported_statements_for_fabricated(self):
        """Each fabricated fact should go into unsupported_statements[]."""
        section = self._prompt.split("7. FACT FABRICATION CHECK")[1]
        assert "unsupported_statements" in section

    def test_annexure_fabrication_check(self):
        """Must check Annexures against USER_REQUEST too."""
        section = self._prompt.split("7. FACT FABRICATION CHECK")[1]
        assert "Annexure" in section

    def test_existing_checks_preserved(self):
        """Checks 1-6 must still be present."""
        assert "1. STATUTORY REFERENCE SOURCING" in self._prompt
        assert "2. CAUSE OF ACTION ACCRUAL DATE" in self._prompt
        assert "3. COURT FEE COMPUTATION" in self._prompt
        assert "4. EVIDENCE PROVISION ACCURACY" in self._prompt
        assert "5. DOCUMENT REFERENCE CONSISTENCY" in self._prompt
        assert "6. PROCEDURAL ACT COMPLIANCE" in self._prompt

    def test_phase2_references_check_7(self):
        """Phase 2 suffix must reference checks 1-7."""
        assert "checks 1–7" in self._phase2 or "checks 1-7" in self._phase2

    def test_build_returns_string_with_check_7(self):
        """Built review prompt includes fact fabrication check."""
        result = self._build(retry=False, inline_fix=True)
        assert "FACT FABRICATION CHECK" in result

    def test_fabricated_facts_in_severity_definition(self):
        """Severity definition must include 'fabricated facts' as example."""
        # The severity="legal" definition lists examples — fabricated facts should be among them
        assert "fabricated facts" in self._prompt


# ===========================================================================
# D) LKB Fallback — Honest Unknown
# ===========================================================================

class TestLKBFallback:
    """Verify LKB fallback returns honest 'unknown' instead of empty."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.draft_single_call import (
            _build_lkb_brief_context,
        )
        self._build = _build_lkb_brief_context

    def test_none_returns_honest_unknown(self):
        """None lkb_brief returns honest fallback, not empty string."""
        result = self._build(None)
        assert result != ""
        assert "No specific Legal Knowledge Base entry" in result

    def test_empty_dict_returns_honest_unknown(self):
        """Empty dict lkb_brief returns honest fallback."""
        result = self._build({})
        assert "No specific Legal Knowledge Base entry" in result

    def test_fallback_mentions_placeholder(self):
        """Fallback must tell LLM to use PLACEHOLDER."""
        result = self._build(None)
        assert "PLACEHOLDER" in result

    def test_fallback_mentions_accuracy(self):
        """Fallback must emphasize accuracy > completeness."""
        result = self._build(None)
        assert "accuracy" in result.lower()

    def test_valid_entry_returns_brief(self):
        """Valid lkb_brief should return structured brief, not fallback."""
        entry = {
            "display_name": "Money Recovery",
            "primary_acts": [{"act": "Indian Contract Act, 1872", "sections": ["Section 73"]}],
        }
        result = self._build(entry)
        assert "LEGAL BRIEF" in result
        assert "Money Recovery" in result
        assert "Indian Contract Act" in result

    def test_fallback_does_not_contain_wrong_acts(self):
        """Fallback must NOT suggest any specific acts."""
        result = self._build(None)
        assert "Indian Contract Act" not in result
        assert "Article" not in result


# ===========================================================================
# E) Q-Rule Helper Variables Removed
# ===========================================================================

class TestQRuleVariablesRemoved:
    """Verify Q-rule helper variables no longer exist in draft_prompt module."""

    def test_monetary_relief_rules_removed(self):
        """_MONETARY_RELIEF_RULES should not exist."""
        from app.agents.drafting_agents.prompts import draft_prompt
        assert not hasattr(draft_prompt, "_MONETARY_RELIEF_RULES")

    def test_non_monetary_relief_rules_removed(self):
        """_NON_MONETARY_RELIEF_RULES should not exist."""
        from app.agents.drafting_agents.prompts import draft_prompt
        assert not hasattr(draft_prompt, "_NON_MONETARY_RELIEF_RULES")

    def test_continuing_coa_rules_removed(self):
        """_CONTINUING_COA_RULES should not exist."""
        from app.agents.drafting_agents.prompts import draft_prompt
        assert not hasattr(draft_prompt, "_CONTINUING_COA_RULES")

    def test_single_event_coa_rules_removed(self):
        """_SINGLE_EVENT_COA_RULES should not exist."""
        from app.agents.drafting_agents.prompts import draft_prompt
        assert not hasattr(draft_prompt, "_SINGLE_EVENT_COA_RULES")


# ===========================================================================
# F) Integration — Prompt Character Count Reduction
# ===========================================================================

class TestPromptSizeReduction:
    """Verify prompts are significantly shorter after Q-rule removal."""

    def test_v4_system_prompt_shorter_than_old(self):
        """v4.0 system template should be under 2500 chars (was ~4000+ with Q-rules)."""
        from app.agents.drafting_agents.prompts.draft_prompt import _SYSTEM_TEMPLATE
        assert len(_SYSTEM_TEMPLATE) < 2500, (
            f"System template is {len(_SYSTEM_TEMPLATE)} chars — should be under 2500"
        )

    def test_freetext_system_prompt_shorter_than_old(self):
        """v5.0 freetext template should be under 2500 chars (was ~3000+ with 14 rules)."""
        from app.agents.drafting_agents.prompts.draft_prompt import _FREETEXT_SYSTEM_TEMPLATE
        assert len(_FREETEXT_SYSTEM_TEMPLATE) < 2500, (
            f"Freetext template is {len(_FREETEXT_SYSTEM_TEMPLATE)} chars — should be under 2500"
        )

    def test_review_prompt_shorter_than_old(self):
        """Review prompt should be under 10000 chars (was ~12000+ with Q1-Q10)."""
        from app.agents.drafting_agents.prompts.review import REVIEW_SYSTEM_PROMPT
        assert len(REVIEW_SYSTEM_PROMPT) < 10000, (
            f"Review prompt is {len(REVIEW_SYSTEM_PROMPT)} chars — should be under 10000"
        )


# ===========================================================================
# G) Existing Functionality Preserved
# ===========================================================================

class TestExistingFunctionalityPreserved:
    """Verify existing helper functions still work correctly."""

    def test_load_exemplar_works(self):
        """load_exemplar should still return content for civil_suit."""
        from app.agents.drafting_agents.prompts.draft_prompt import load_exemplar
        result = load_exemplar("civil_suit")
        assert isinstance(result, str)
        # May be empty if exemplar file doesn't exist, but shouldn't crash

    def test_get_section_keys_civil(self):
        """get_section_keys returns correct keys for civil suits."""
        from app.agents.drafting_agents.prompts.draft_prompt import (
            get_section_keys, CIVIL_PLAINT_SECTIONS,
        )
        result = get_section_keys("civil_suit", "money_recovery")
        assert result == CIVIL_PLAINT_SECTIONS

    def test_get_section_keys_partition(self):
        """get_section_keys returns non-monetary keys for partition."""
        from app.agents.drafting_agents.prompts.draft_prompt import (
            get_section_keys, CIVIL_NON_MONETARY_SECTIONS,
        )
        result = get_section_keys("civil_suit", "partition")
        assert result == CIVIL_NON_MONETARY_SECTIONS

    def test_get_section_keys_criminal(self):
        """get_section_keys returns criminal sections."""
        from app.agents.drafting_agents.prompts.draft_prompt import (
            get_section_keys, CRIMINAL_SECTIONS,
        )
        result = get_section_keys("bail_application")
        assert result == CRIMINAL_SECTIONS

    def test_build_draft_user_prompt_works(self):
        """build_draft_user_prompt should still work."""
        from app.agents.drafting_agents.prompts.draft_prompt import build_draft_user_prompt
        result = build_draft_user_prompt(
            user_request="test",
            doc_type="civil_suit",
            law_domain="Civil",
            jurisdiction="{}",
            parties="{}",
            facts="{}",
            evidence="[]",
            verified_provisions="none",
            limitation="UNKNOWN",
            court_fee_context="none",
            rag_context="none",
        )
        assert "test" in result
        assert "civil_suit" in result

    def test_build_draft_freetext_user_prompt_works(self):
        """build_draft_freetext_user_prompt should still work."""
        from app.agents.drafting_agents.prompts.draft_prompt import build_draft_freetext_user_prompt
        result = build_draft_freetext_user_prompt(
            user_request="test",
            doc_type="civil_suit",
            law_domain="Civil",
            jurisdiction="{}",
            parties="{}",
            facts="{}",
            evidence="[]",
            verified_provisions="none",
            limitation="UNKNOWN",
            court_fee_context="none",
            rag_context="none",
        )
        assert "test" in result

    def test_build_review_system_prompt_works(self):
        """build_review_system_prompt should still work."""
        from app.agents.drafting_agents.prompts.review import build_review_system_prompt
        result = build_review_system_prompt(retry=False, inline_fix=True)
        assert isinstance(result, str)
        assert "FACT FABRICATION CHECK" in result
        assert "Schema" in result

    def test_build_review_system_prompt_retry(self):
        """build_review_system_prompt with retry should include retry suffix."""
        from app.agents.drafting_agents.prompts.review import build_review_system_prompt
        result = build_review_system_prompt(retry=True, inline_fix=True)
        assert "PREVIOUS ATTEMPT FAILED" in result

    def test_build_review_system_prompt_no_inline_fix(self):
        """build_review_system_prompt without inline_fix should skip Phase 2."""
        from app.agents.drafting_agents.prompts.review import build_review_system_prompt
        result = build_review_system_prompt(retry=False, inline_fix=False)
        assert "PHASE 2" not in result

    def test_limitation_context_builder(self):
        """_build_limitation_context should still work."""
        from app.agents.drafting_agents.nodes.draft_single_call import _build_limitation_context
        result = _build_limitation_context({"limitation": {"article": "58", "period": "3 years"}})
        assert "Article 58" in result

    def test_limitation_context_none(self):
        """_build_limitation_context with NONE article."""
        from app.agents.drafting_agents.nodes.draft_single_call import _build_limitation_context
        result = _build_limitation_context({"limitation": {"article": "NONE", "description": "No limitation"}})
        assert "NO LIMITATION" in result

    def test_limitation_context_unknown(self):
        """_build_limitation_context with UNKNOWN article."""
        from app.agents.drafting_agents.nodes.draft_single_call import _build_limitation_context
        result = _build_limitation_context({"limitation": {"article": "UNKNOWN"}})
        assert "LIMITATION_ARTICLE" in result or "placeholder" in result.lower()


# ===========================================================================
# H) LKB Lookup Still Works
# ===========================================================================

class TestLKBLookupPreserved:
    """Verify LKB lookup behavior is unchanged."""

    def test_known_cause_type_returns_entry(self):
        """Known cause type should return an entry."""
        from app.agents.drafting_agents.lkb import lookup
        entry = lookup("Civil", "money_recovery_loan")
        assert entry is not None
        assert "primary_acts" in entry

    def test_unknown_cause_type_returns_none(self):
        """Unknown cause type should return None."""
        from app.agents.drafting_agents.lkb import lookup
        entry = lookup("Civil", "cancellation_of_instrument")
        assert entry is None

    def test_cancellation_sale_deed_not_in_lkb(self):
        """cancellation_sale_deed should not be in LKB (known gap)."""
        from app.agents.drafting_agents.lkb import lookup
        entry = lookup("Civil", "cancellation_sale_deed")
        assert entry is None

    def test_lkb_brief_for_unknown_gives_honest_fallback(self):
        """When LKB returns None, brief context should give honest fallback."""
        from app.agents.drafting_agents.lkb import lookup
        from app.agents.drafting_agents.nodes.draft_single_call import _build_lkb_brief_context

        entry = lookup("Civil", "cancellation_of_instrument")
        result = _build_lkb_brief_context(entry)
        assert "No specific Legal Knowledge Base entry" in result
        assert "PLACEHOLDER" in result
