"""v4.0 Unit Tests — deterministic nodes, prompts, graph compilation.

Tests ALL v4.0 pipeline components that don't require LLM calls:
  - structural_gate: section presence checking
  - citation_validator: citation regex + enrichment verification
  - evidence_anchoring: entity extraction + token replacement
  - assembler: dict → formatted text rendering
  - draft_prompt: exemplar loading, section keys, prompt building
  - graph: compilation, node count, routing chain

Run:  pytest tests/drafting/test_v4_unit.py -v
"""
from __future__ import annotations

import re
import sys
import time

import pytest

# ---------------------------------------------------------------------------
# 0) Ensure project root is on sys.path
# ---------------------------------------------------------------------------
sys.path.insert(0, ".")


# ===========================================================================
# A) Structural Gate Tests
# ===========================================================================

class TestStructuralGate:
    """Test structural_gate_node: checks required sections are present."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.structural_gate import (
            structural_gate_node,
            _detect_category,
            _REQUIRED_SECTIONS,
        )
        self.node = structural_gate_node
        self.detect = _detect_category
        self.required = _REQUIRED_SECTIONS

    def test_detect_category_civil(self):
        assert self.detect("money_recovery_plaint") == "civil"
        assert self.detect("specific_performance_plaint") == "civil"
        assert self.detect("plaint_for_damages") == "civil"

    def test_detect_category_criminal(self):
        assert self.detect("bail_application") == "criminal"
        assert self.detect("criminal_complaint") == "criminal"

    def test_detect_category_constitutional(self):
        assert self.detect("writ_petition") == "constitutional"
        assert self.detect("constitutional_challenge") == "constitutional"

    def test_detect_category_family(self):
        assert self.detect("divorce_petition") == "family"
        assert self.detect("family_maintenance") == "family"

    def test_detect_category_default(self):
        assert self.detect("some_unknown_type") == "civil"

    def test_required_sections_exist_for_civil(self):
        assert "facts" in self.required["civil"]
        assert "prayer" in self.required["civil"]

    def test_full_sections_pass(self):
        """All required civil sections present → no ERROR issues."""
        state = {
            "filled_sections": {
                "court_heading": "IN THE COURT...",
                "title": "PLAINT",
                "parties": "Plaintiff vs Defendant",
                "jurisdiction": "This court has jurisdiction",
                "facts": "The plaintiff advanced Rs.15,00,000...",
                "legal_basis": "Section 65 of the Indian Contract Act",
                "cause_of_action": "The cause of action arose on...",
                "limitation": "Article 55 of the Limitation Act",
                "valuation_court_fee": "The suit is valued at...",
                "interest": "Interest at 12% per annum",
                "prayer": "The plaintiff prays for...",
                "verification": "Verified at...",
            },
            "classify": {"doc_type": "money_recovery_plaint"},
        }
        result = self.node(state)
        issues = result.update.get("structural_issues", [])
        errors = [i for i in issues if i["severity"] == "ERROR"]
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_missing_required_section_gives_error(self):
        """Missing 'facts' section → ERROR."""
        state = {
            "filled_sections": {
                "prayer": "The plaintiff prays...",
                # facts missing!
            },
            "classify": {"doc_type": "money_recovery_plaint"},
        }
        result = self.node(state)
        gate = result.update.get("structural_gate", {})
        errors = gate.get("errors", [])
        assert len(errors) > 0
        missing_secs = [e["section"] for e in errors]
        assert "facts" in missing_secs

    def test_missing_warn_section_gives_warn(self):
        """Missing 'limitation' section → WARN, not ERROR."""
        state = {
            "filled_sections": {
                "facts": "The plaintiff...",
                "prayer": "Prays for...",
                "parties": "Ram vs Suresh",
                "jurisdiction": "Court has jurisdiction",
                "legal_basis": "Section 65",
                "cause_of_action": "Arose on...",
                "verification": "Verified at Bengaluru",
                # limitation missing
            },
            "classify": {"doc_type": "money_recovery_plaint"},
        }
        result = self.node(state)
        gate = result.update.get("structural_gate", {})
        warns = gate.get("warnings", [])
        warn_secs = [w["section"] for w in warns]
        assert "limitation" in warn_secs

    def test_always_routes_to_assembler(self):
        """Structural gate should always route to assembler (even with errors)."""
        state = {
            "filled_sections": {},
            "classify": {"doc_type": "money_recovery_plaint"},
        }
        result = self.node(state)
        assert result.goto == "assembler"


# ===========================================================================
# B) Citation Validator Tests
# ===========================================================================

class TestCitationValidator:
    """Test citation_validator_node: string containment approach (v5.1)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.citation_validator import (
            citation_validator_node,
            _RE_CASE_CITATION,
            _ALWAYS_ALLOWED,
        )
        self.node = citation_validator_node
        self.re_case = _RE_CASE_CITATION
        self.allowed = _ALWAYS_ALLOWED

    def test_always_allowed_contains_common_cpc(self):
        assert "Section 26" in self.allowed
        assert "Order VII Rule 1" in self.allowed
        assert "Section 151" in self.allowed
        assert "Article 226" in self.allowed
        assert "Section 65B" in self.allowed
        # v5.1: common substantive sections also allowed
        assert "Section 73" in self.allowed
        assert "Section 10" in self.allowed

    def test_case_citation_regex_detects_air(self):
        text = "as held in AIR 2015 SC 123"
        matches = list(self.re_case.finditer(text))
        assert len(matches) >= 1

    def test_case_citation_regex_detects_scc(self):
        text = "see SCC 2020 Delhi 456"
        matches = list(self.re_case.finditer(text))
        assert len(matches) >= 1

    def test_no_false_positive_on_currency_amounts(self):
        """v5.1: Rs. 15,00,000 must NOT produce 'Section 15' warnings."""
        state = {
            "draft": {
                "draft_artifacts": [{
                    "text": (
                        "The plaintiff claims Rs. 15,00,000/- (Rupees Fifteen Lakhs). "
                        "The suit is valued at Rs. 20,00,000/-. "
                        "Section 73 of the Indian Contract Act applies."
                    ),
                }],
            },
            "mandatory_provisions": {
                "verified_provisions": [
                    {"section": "Section 73", "act": "Indian Contract Act"},
                ],
            },
        }
        result = self.node(state)
        issues = result.update.get("citation_issues", [])
        # No "Section 15" or "Section 20" warnings from currency amounts
        section_warns = [i for i in issues if "Section 15" in str(i) or "Section 20" in str(i)]
        assert len(section_warns) == 0

    def test_verified_provision_in_draft_no_issues(self):
        """v5.1: verified provision found in draft text → no issues."""
        state = {
            "draft": {
                "draft_artifacts": [{
                    "text": (
                        "This suit is filed under Section 26 of the Code of Civil Procedure. "
                        "The plaintiff relies on Section 65 of the Indian Contract Act. "
                        "The suit is within limitation under Article 55 of the Limitation Act."
                    ),
                }],
            },
            "mandatory_provisions": {
                "verified_provisions": [
                    {"section": "Section 65", "act": "Indian Contract Act"},
                ],
                "limitation": {"article": "55"},
            },
        }
        result = self.node(state)
        issues = result.update.get("citation_issues", [])
        errors = [i for i in issues if i["severity"] == "ERROR"]
        assert len(errors) == 0

    def test_fabricated_case_citation_flagged(self):
        """AIR/SCC case citations are always flagged as ERROR."""
        state = {
            "draft": {
                "draft_artifacts": [{
                    "text": "As held in AIR 2019 SC 1234, the defendant is liable.",
                }],
            },
            "mandatory_provisions": {"verified_provisions": []},
        }
        result = self.node(state)
        issues = result.update.get("citation_issues", [])
        errors = [i for i in issues if i["severity"] == "ERROR"]
        assert len(errors) >= 1
        assert errors[0]["type"] == "fabricated_case_citation"

    def test_verified_provision_missing_from_draft(self):
        """v5.1: verified provision NOT in draft → INFO (not WARN)."""
        state = {
            "draft": {
                "draft_artifacts": [{
                    "text": "The plaintiff seeks relief under general principles.",
                }],
            },
            "mandatory_provisions": {
                "verified_provisions": [
                    {"section": "Section 92", "act": "Code of Civil Procedure"},
                ],
            },
        }
        result = self.node(state)
        issues = result.update.get("citation_issues", [])
        info_issues = [i for i in issues if i["severity"] == "INFO"]
        assert len(info_issues) >= 1
        assert info_issues[0]["type"] == "verified_provision_not_cited"

    def test_limitation_article_missing_from_draft(self):
        """v5.1: limitation article not cited in draft → WARN."""
        state = {
            "draft": {
                "draft_artifacts": [{
                    "text": "The suit is filed within time.",
                }],
            },
            "mandatory_provisions": {
                "verified_provisions": [],
                "limitation": {"article": "55"},
            },
        }
        result = self.node(state)
        issues = result.update.get("citation_issues", [])
        warns = [i for i in issues if i["severity"] == "WARN"]
        assert len(warns) >= 1
        assert warns[0]["type"] == "limitation_reference_missing"

    def test_special_limitation_reference_missing_from_draft(self):
        """Special-statute limitation reference not cited in draft → WARN."""
        state = {
            "draft": {
                "draft_artifacts": [{
                    "text": "The complaint is within limitation.",
                }],
            },
            "mandatory_provisions": {
                "verified_provisions": [],
                "limitation": {
                    "article": "N/A",
                    "reference": "Section 69 of the Consumer Protection Act, 2019",
                    "act": "Consumer Protection Act, 2019",
                },
            },
        }
        result = self.node(state)
        issues = result.update.get("citation_issues", [])
        warns = [i for i in issues if i["severity"] == "WARN"]
        assert len(warns) >= 1
        assert warns[0]["type"] == "limitation_reference_missing"
        assert "Section 69" in warns[0]["citation"]

    def test_disabled_setting_skips(self):
        """When DRAFTING_CITATION_VALIDATOR_ENABLED=False, skip with empty issues."""
        from app.config import settings
        original = settings.DRAFTING_CITATION_VALIDATOR_ENABLED
        try:
            settings.DRAFTING_CITATION_VALIDATOR_ENABLED = False
            state = {
                "draft": {"draft_artifacts": [{"text": "AIR 2020 SC 999"}]},
                "mandatory_provisions": {"verified_provisions": []},
            }
            result = self.node(state)
            assert result.update.get("citation_issues") == []
            assert result.goto in ("review", "__end__")
        finally:
            settings.DRAFTING_CITATION_VALIDATOR_ENABLED = original

    def test_routes_after_validation(self):
        """After validation, routes to review or END depending on skip setting."""
        state = {
            "draft": {"draft_artifacts": [{"text": "Some clean draft"}]},
            "mandatory_provisions": {"verified_provisions": []},
        }
        result = self.node(state)
        assert result.goto in ("review", "__end__")


# ===========================================================================
# C) Evidence Anchoring Tests
# ===========================================================================

class TestEvidenceAnchoring:
    """Test evidence_anchoring_node: entity extraction + Tier A replacement."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.evidence_anchoring import (
            evidence_anchoring_node,
        )
        self.node = evidence_anchoring_node

    def test_no_draft_skips(self):
        state = {"draft": None, "intake": None}
        result = self.node(state)
        assert result.goto == "lkb_compliance"
        assert result.update.get("evidence_anchoring_issues") == []

    def test_supported_dates_not_replaced(self):
        """Dates matching intake should NOT be replaced with placeholder."""
        state = {
            "draft": {
                "draft_artifacts": [{
                    "text": "The loan was given on 15.03.2024 and default occurred on 20.06.2024.",
                }],
            },
            "intake": {
                "facts": {
                    "chronology": [
                        {"date": "15.03.2024", "event": "Loan given"},
                        {"date": "20.06.2024", "event": "Default"},
                    ],
                },
            },
        }
        result = self.node(state)
        text = result.update["draft"]["draft_artifacts"][0]["text"]
        assert "15.03.2024" in text
        assert "20.06.2024" in text
        assert "{{DATE}}" not in text

    def test_unsupported_dates_replaced(self):
        """Dates NOT in intake should be replaced with {{DATE}}."""
        state = {
            "draft": {
                "draft_artifacts": [{
                    "text": "A meeting was held on 01.01.2020 to discuss the terms.",
                }],
            },
            "intake": {
                "facts": {
                    "chronology": [
                        {"date": "15.03.2024", "event": "Loan given"},
                    ],
                },
            },
        }
        result = self.node(state)
        text = result.update["draft"]["draft_artifacts"][0]["text"]
        assert "01.01.2020" not in text
        assert "{{DATE}}" in text

    def test_supported_amounts_not_replaced(self):
        """Amounts matching intake should NOT be replaced."""
        state = {
            "draft": {
                "draft_artifacts": [{
                    "text": "The plaintiff advanced Rs. 15,00,000/- to the defendant.",
                }],
            },
            "intake": {
                "facts": {
                    "amounts": {"principal": 1500000},
                },
            },
        }
        result = self.node(state)
        text = result.update["draft"]["draft_artifacts"][0]["text"]
        assert "15,00,000" in text
        assert "{{AMOUNT}}" not in text

    def test_unsupported_amounts_replaced(self):
        """Amounts NOT in intake should be replaced with {{AMOUNT}}."""
        state = {
            "draft": {
                "draft_artifacts": [{
                    "text": "The defendant paid Rs. 5,00,000/- on an earlier date.",
                }],
            },
            "intake": {
                "facts": {
                    "amounts": {"principal": 1500000},
                },
            },
        }
        result = self.node(state)
        text = result.update["draft"]["draft_artifacts"][0]["text"]
        assert "{{AMOUNT}}" in text

    def test_routes_to_lkb_compliance(self):
        state = {
            "draft": {"draft_artifacts": [{"text": "Clean draft."}]},
            "intake": {"facts": {}},
        }
        result = self.node(state)
        assert result.goto == "lkb_compliance"


# ===========================================================================
# D) Assembler Tests
# ===========================================================================

class TestAssembler:
    """Test assembler_node: section dict → formatted document."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.assembler import assembler_node
        self.node = assembler_node

    def test_dict_format_produces_text(self):
        """v4.0 dict format should produce readable text."""
        state = {
            "filled_sections": {
                "court_heading": "IN THE COURT OF THE CIVIL JUDGE",
                "title": "PLAINT",
                "facts": "The plaintiff lent Rs.15,00,000 to the defendant.",
                "prayer": "WHEREFORE the plaintiff prays for a decree of Rs.15,00,000.",
                "verification": "Verified at Bengaluru on this day.",
            },
            "classify": {"doc_type": "money_recovery_plaint"},
        }
        result = self.node(state)
        draft = result.update.get("draft", {})
        artifacts = draft.get("draft_artifacts", [])
        assert len(artifacts) == 1
        text = artifacts[0]["text"]
        assert "CIVIL JUDGE" in text
        assert "PLAINT" in text
        assert "FACTS OF THE CASE" in text
        assert "15,00,000" in text
        assert "PRAYER" in text

    def test_dict_format_adds_headings(self):
        """Section headings should be added for named sections."""
        state = {
            "filled_sections": {
                "jurisdiction": "This court has territorial jurisdiction.",
                "facts": "Facts go here.",
            },
            "classify": {"doc_type": "money_recovery_plaint"},
        }
        result = self.node(state)
        text = result.update["draft"]["draft_artifacts"][0]["text"]
        assert "JURISDICTION" in text
        assert "FACTS OF THE CASE" in text

    def test_advocate_block_appended(self):
        """Advocate block should be appended when not in draft."""
        state = {
            "filled_sections": {"facts": "Facts.", "prayer": "Prayer."},
            "classify": {"doc_type": "money_recovery_plaint"},
        }
        result = self.node(state)
        text = result.update["draft"]["draft_artifacts"][0]["text"]
        assert "{{ADVOCATE_NAME}}" in text
        assert "Enrollment No." in text

    def test_list_format_backward_compat(self):
        """v3.0 list format should still work."""
        state = {
            "filled_sections": [
                {"section_id": "facts", "heading": "FACTS", "text": "Facts here."},
                {"section_id": "prayer", "heading": "PRAYER", "text": "Prayer here."},
            ],
            "classify": {"doc_type": "money_recovery_plaint"},
        }
        result = self.node(state)
        text = result.update["draft"]["draft_artifacts"][0]["text"]
        assert "Facts here." in text
        assert "Prayer here." in text

    def test_placeholder_collection(self):
        """Placeholders in text should be collected in metadata."""
        state = {
            "filled_sections": {
                "facts": "The plaintiff {{PLAINTIFF_NAME}} paid Rs. {{AMOUNT}} on {{DATE}}.",
            },
            "classify": {"doc_type": "money_recovery_plaint"},
        }
        result = self.node(state)
        placeholders = result.update["draft"]["draft_artifacts"][0]["placeholders_used"]
        keys = [p["key"] for p in placeholders]
        assert "PLAINTIFF_NAME" in keys
        assert "AMOUNT" in keys
        assert "DATE" in keys

    def test_routes_to_evidence_anchoring(self):
        state = {
            "filled_sections": {"facts": "Facts."},
            "classify": {"doc_type": "money_recovery_plaint"},
        }
        result = self.node(state)
        assert result.goto == "evidence_anchoring"


# ===========================================================================
# E) Draft Prompt Tests
# ===========================================================================

class TestDraftPrompt:
    """Test draft_prompt.py: exemplar loading, section keys, prompt building."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.prompts.draft_prompt import (
            get_section_keys,
            build_draft_system_prompt,
            build_draft_user_prompt,
        )
        self.get_keys = get_section_keys
        self.build_system = build_draft_system_prompt
        self.build_user = build_draft_user_prompt

    def test_section_keys_civil(self):
        keys = self.get_keys("money_recovery_plaint")
        assert "facts" in keys
        assert "prayer" in keys
        assert "jurisdiction" in keys
        assert "legal_basis" in keys
        assert len(keys) >= 10

    def test_section_keys_criminal(self):
        keys = self.get_keys("bail_application")
        assert "grounds" in keys
        assert "prayer" in keys

    def test_system_prompt_no_exemplar(self):
        """Exemplar removed — prompt should contain rules but no exemplar."""
        prompt = self.build_system("money_recovery_plaint")
        assert "EXEMPLAR" not in prompt
        assert len(prompt) > 300

    def test_system_prompt_contains_rules(self):
        prompt = self.build_system("money_recovery_plaint")
        assert "placeholder" in prompt.lower() or "PLACEHOLDER" in prompt
        assert "JSON" in prompt

    def test_user_prompt_includes_all_context(self):
        prompt = self.build_user(
            user_request="Draft a money recovery plaint",
            doc_type="money_recovery_plaint",
            law_domain="Civil",
            jurisdiction='{"state": "Karnataka", "city": "Bengaluru", "court_type": "City Civil Court"}',
            parties='{"primary": {"name": "Ram"}}',
            facts='{"summary": "Loan of Rs.15L"}',
            evidence='[{"type": "bank_transfer"}]',
            verified_provisions="Section 65 Indian Contract Act",
            limitation="Article 55 Limitation Act",
            court_fee_context="Court fee: Rs.5000",
            rag_context="Chunk 1: CPC provisions...",
        )
        assert "money recovery" in prompt.lower() or "money_recovery" in prompt
        assert "Ram" in prompt
        assert "15L" in prompt or "15,00,000" in prompt.lower()
        assert "Section 65" in prompt
        assert "Article 55" in prompt


# ===========================================================================
# F) Graph Compilation Tests
# ===========================================================================

class TestGraphCompilation:
    """Test drafting_graph.py: compilation, node count, node names."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.drafting_graph import get_drafting_graph
        self.get_graph = get_drafting_graph

    def test_graph_compiles(self):
        graph = self.get_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = self.get_graph()
        node_names = set(graph.nodes.keys()) - {"__start__", "__end__"}
        # 12 nodes: intake_classify + intake + classify + rag + enrichment + court_fee
        #           + draft_freetext + evidence_anchoring + lkb_compliance + postprocess
        #           + citation_validator + review
        assert len(node_names) >= 11, f"Expected >=11 nodes, got {len(node_names)}: {node_names}"

    def test_v5_pipeline_nodes_present(self):
        graph = self.get_graph()
        nodes = set(graph.nodes.keys())
        for expected in [
            "intake", "classify", "rag", "enrichment", "court_fee",
            "draft_freetext",
            "evidence_anchoring", "lkb_compliance", "postprocess",
            "citation_validator", "review",
        ]:
            assert expected in nodes, f"Missing v5.0 node: {expected}"

    def test_v4_nodes_removed(self):
        """v4.0/v3.0 nodes should NOT be in graph."""
        graph = self.get_graph()
        nodes = set(graph.nodes.keys())
        for removed in [
            "draft_single_call", "structural_gate", "assembler",
            "section_fixer", "template_loader", "outline_validator",
            "section_drafter", "section_validator", "draft",
        ]:
            assert removed not in nodes, f"v4.0/v3.0 node still present: {removed}"


# ===========================================================================
# G) State Definition Tests
# ===========================================================================

class TestStateDefinition:
    """Test DraftingState TypedDict has v4.0 fields."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.states.draftGraph import DraftingState
        self.state_cls = DraftingState

    def test_v4_fields_exist(self):
        annotations = self.state_cls.__annotations__
        assert "structural_issues" in annotations
        assert "citation_issues" in annotations
        assert "evidence_anchoring_issues" in annotations

    def test_filled_sections_union_type(self):
        annotations = self.state_cls.__annotations__
        filled_type = str(annotations["filled_sections"])
        assert "Dict" in filled_type or "dict" in filled_type
        assert "List" in filled_type or "list" in filled_type

    def test_core_fields_exist(self):
        annotations = self.state_cls.__annotations__
        for field in ["user_request", "intake", "classify", "rag", "draft", "review", "errors"]:
            assert field in annotations, f"Missing state field: {field}"


# ===========================================================================
# H) Settings Tests
# ===========================================================================

class TestSettings:
    """Test v4.0 settings are properly defined."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.config.settings import Settings
        self.settings_cls = Settings

    def test_review_max_tokens_default(self):
        fields = self.settings_cls.model_fields
        assert "REVIEW_MAX_TOKENS" in fields
        assert fields["REVIEW_MAX_TOKENS"].default is None

    def test_enrichment_llm_enabled_default(self):
        fields = self.settings_cls.model_fields
        assert "DRAFTING_ENRICHMENT_LLM_ENABLED" in fields
        assert fields["DRAFTING_ENRICHMENT_LLM_ENABLED"].default is True

    def test_citation_validator_enabled_default(self):
        fields = self.settings_cls.model_fields
        assert "DRAFTING_CITATION_VALIDATOR_ENABLED" in fields
        assert fields["DRAFTING_CITATION_VALIDATOR_ENABLED"].default is True


# ===========================================================================
# I) Postprocess Routing Tests
# ===========================================================================

class TestPostprocessRouting:
    """Test postprocess routes to citation_validator (not review)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.postprocess import postprocess_node
        self.node = postprocess_node

    def test_routes_to_citation_validator(self):
        state = {
            "draft": {
                "draft_artifacts": [{"text": "Simple draft text.", "doc_type": "plaint", "title": "Test"}],
            },
            "filled_sections": {},
        }
        result = self.node(state)
        # Should go to citation_validator (not review)
        assert result.goto in ("citation_validator", "__end__")

    def test_empty_artifacts_routes_to_citation_validator(self):
        state = {"draft": {"draft_artifacts": []}}
        result = self.node(state)
        assert result.goto == "citation_validator"


# ===========================================================================
# J) Entity Extraction Accuracy Tests
# ===========================================================================

class TestEntityExtraction:
    """Test section_validator entity extractors directly."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.section_validator import (
            _extract_dates,
            _extract_amounts,
            _extract_references,
            _extract_citations,
        )
        self.extract_dates = _extract_dates
        self.extract_amounts = _extract_amounts
        self.extract_refs = _extract_references
        self.extract_citations = _extract_citations

    def test_date_dd_mm_yyyy(self):
        dates = self.extract_dates("Payment was made on 15.03.2024.")
        assert len(dates) >= 1
        assert "15.03.2024" in dates[0]["raw"]

    def test_date_dd_month_yyyy(self):
        dates = self.extract_dates("On 15th March 2024, the loan was given.")
        assert len(dates) >= 1

    def test_date_month_dd_yyyy(self):
        dates = self.extract_dates("March 15, 2024 was the date of payment.")
        assert len(dates) >= 1

    def test_date_excludes_section_numbers(self):
        """Section 65 should NOT be extracted as a date."""
        dates = self.extract_dates("Under Section 65 of the Indian Contract Act")
        assert len(dates) == 0

    def test_amount_rs_format(self):
        amounts = self.extract_amounts("The amount of Rs. 15,00,000/- was advanced.")
        assert len(amounts) >= 1
        assert amounts[0]["value"] == 1500000.0

    def test_amount_lakh_format(self):
        amounts = self.extract_amounts("A sum of Rs. 8.5 lakhs was paid.")
        assert len(amounts) >= 1
        # RS regex matches "8.5" first, lakh regex matches "8.5 lakhs" → 850000
        values = [a["value"] for a in amounts]
        assert 850000.0 in values, f"Expected 850000.0 in {values}"

    def test_reference_cheque(self):
        refs = self.extract_refs("Payment via cheque No. 123456.")
        assert len(refs) >= 1
        assert refs[0]["subtype"] == "cheque"

    def test_reference_utr(self):
        refs = self.extract_refs("UTR: AXIB20240315123456")
        assert len(refs) >= 1
        assert refs[0]["subtype"] == "utr"

    def test_citation_air(self):
        cites = self.extract_citations("AIR 2020 SC 1234")
        assert len(cites) >= 1

    def test_citation_scc(self):
        cites = self.extract_citations("SCC 2019 Delhi 567")
        assert len(cites) >= 1

    def test_no_false_positive_on_clean_text(self):
        """Clean legal text without citations should return empty."""
        cites = self.extract_citations("The plaintiff is a resident of Bengaluru.")
        assert len(cites) == 0


# ===========================================================================
# SPEED BENCHMARK
# ===========================================================================

class TestDeterministicSpeed:
    """Benchmark speed of deterministic nodes (must complete in <100ms each)."""

    def _make_full_state(self):
        return {
            "filled_sections": {
                "court_heading": "IN THE COURT OF THE CIVIL JUDGE (SENIOR DIVISION), BENGALURU",
                "title": "ORIGINAL SUIT NO. ___ OF 2024\nPLAINT FOR RECOVERY OF MONEY",
                "parties": "Ram Kumar S/o Shiva Kumar ... PLAINTIFF\nVS\nSuresh Patel S/o Ramesh Patel ... DEFENDANT",
                "jurisdiction": "This Hon'ble Court has territorial and pecuniary jurisdiction.",
                "facts": (
                    "1. The Plaintiff is a resident of Bengaluru.\n"
                    "2. The Defendant is also a resident of Bengaluru.\n"
                    "3. On 15.03.2024, the Plaintiff advanced Rs.15,00,000 to the Defendant.\n"
                    "4. The amount was transferred via NEFT (UTR: AXIB20240315123456).\n"
                    "5. The Defendant failed to repay despite repeated demands."
                ),
                "legal_basis": "Section 65 of the Indian Contract Act, 1872.",
                "cause_of_action": "The cause of action arose on 20.06.2024.",
                "limitation": "Under Article 55 of the Limitation Act, 1963.",
                "valuation_court_fee": "The suit is valued at Rs.15,00,000.",
                "interest": "Interest at 12% per annum from 20.06.2024.",
                "prayer": "WHEREFORE the plaintiff prays for a decree of Rs.15,00,000.",
                "document_list": "Annexure A: Bank statement\nAnnexure B: WhatsApp chats",
                "verification": "Verified at Bengaluru.",
            },
            "classify": {"doc_type": "money_recovery_plaint"},
            "intake": {
                "facts": {
                    "chronology": [
                        {"date": "15.03.2024", "event": "Loan given"},
                        {"date": "20.06.2024", "event": "Default"},
                    ],
                    "amounts": {"principal": 1500000},
                },
                "evidence": [{"type": "bank_transfer", "ref": "AXIB20240315123456"}],
            },
            "mandatory_provisions": {
                "verified_provisions": [
                    {"section": "Section 65", "act": "Indian Contract Act"},
                ],
                "limitation": {"article": "55"},
            },
        }

    def test_structural_gate_speed(self):
        from app.agents.drafting_agents.nodes.structural_gate import structural_gate_node
        state = self._make_full_state()
        t0 = time.perf_counter()
        structural_gate_node(state)
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.1, f"structural_gate took {elapsed:.3f}s (>100ms)"

    def test_assembler_speed(self):
        from app.agents.drafting_agents.nodes.assembler import assembler_node
        state = self._make_full_state()
        t0 = time.perf_counter()
        assembler_node(state)
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.1, f"assembler took {elapsed:.3f}s (>100ms)"

    def test_evidence_anchoring_speed(self):
        from app.agents.drafting_agents.nodes.evidence_anchoring import evidence_anchoring_node
        state = self._make_full_state()
        # Assemble first to get draft artifact
        from app.agents.drafting_agents.nodes.assembler import assembler_node
        assembled = assembler_node(state)
        state["draft"] = assembled.update["draft"]
        t0 = time.perf_counter()
        evidence_anchoring_node(state)
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.1, f"evidence_anchoring took {elapsed:.3f}s (>100ms)"

    def test_citation_validator_speed(self):
        from app.agents.drafting_agents.nodes.citation_validator import citation_validator_node
        state = self._make_full_state()
        from app.agents.drafting_agents.nodes.assembler import assembler_node
        assembled = assembler_node(state)
        state["draft"] = assembled.update["draft"]
        t0 = time.perf_counter()
        citation_validator_node(state)
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.1, f"citation_validator took {elapsed:.3f}s (>100ms)"

    def test_full_deterministic_chain_speed(self):
        """Full chain: structural_gate + assembler + evidence_anchoring + citation_validator < 500ms."""
        from app.agents.drafting_agents.nodes.structural_gate import structural_gate_node
        from app.agents.drafting_agents.nodes.assembler import assembler_node
        from app.agents.drafting_agents.nodes.evidence_anchoring import evidence_anchoring_node
        from app.agents.drafting_agents.nodes.citation_validator import citation_validator_node

        state = self._make_full_state()
        t0 = time.perf_counter()

        structural_gate_node(state)
        assembled = assembler_node(state)
        state["draft"] = assembled.update["draft"]
        evidence_anchoring_node(state)
        citation_validator_node(state)

        elapsed = time.perf_counter() - t0
        assert elapsed < 0.5, f"Full deterministic chain took {elapsed:.3f}s (>500ms)"
