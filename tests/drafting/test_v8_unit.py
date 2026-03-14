"""v8.1 Unit Tests — Template Engine, Gap Fill, Document Merge.

Tests all v8.1 pipeline components that don't require LLM calls:
  - TemplateEngine: deterministic assembly, section generation, markers
  - gap_fill_prompt: parsing, merging, renumbering, prompt building
  - draft_template_fill helpers: facts summary, parties context, placeholders
  - Graph: draft_template_fill node registered
  - Routing: TEMPLATE_ENGINE_ENABLED flag

Run:  pytest tests/drafting/test_v8_unit.py -v
"""
from __future__ import annotations

import re
import sys

import pytest

sys.path.insert(0, ".")


# ===========================================================================
# Fixtures: minimal state data for template engine
# ===========================================================================

@pytest.fixture
def minimal_intake():
    return {
        "jurisdiction": {
            "city": "Bengaluru",
            "state": "Karnataka",
            "place": "Bengaluru",
        },
        "parties": {
            "primary": {
                "name": "Rajesh Kumar",
                "age": "45",
                "occupation": "Business",
                "address": "123 MG Road, Bengaluru",
            },
            "opposite": [
                {
                    "name": "ABC Pvt Ltd",
                    "age": "N/A",
                    "occupation": "Company",
                    "address": "456 Brigade Road, Bengaluru",
                }
            ],
        },
        "facts": {
            "summary": "Plaintiff entered into dealership agreement. Defendant terminated illegally.",
            "chronology": [
                {"date": "01.01.2024", "event": "Agreement signed"},
                {"date": "15.06.2024", "event": "Defendant terminated agreement"},
            ],
            "amounts": {"principal": "15,00,000", "interest": "2,50,000"},
            "cause_of_action_date": "15.06.2024",
        },
        "evidence": [
            {"type": "Agreement", "description": "Dealership agreement dated 01.01.2024"},
            {"type": "Notice", "description": "Legal notice dated 01.07.2024"},
            {"type": "Termination Letter", "description": "Termination letter dated 15.06.2024"},
        ],
    }


@pytest.fixture
def minimal_classify():
    return {
        "doc_type": "commercial_suit",
        "cause_type": "breach_dealership_franchise",
        "law_domain": "Civil",
    }


@pytest.fixture
def minimal_lkb_brief():
    from app.agents.drafting_agents.lkb import lookup
    entry = lookup("Civil", "breach_dealership_franchise")
    return entry or {
        "display_name": "Damages for breach of dealership agreement",
        "damages_categories": ["principal_amount", "loss_of_profit", "loss_of_goodwill"],
        "permitted_doctrines": ["breach_of_contract", "damages_s73"],
        "court_rules": {
            "default": {"court": "District Court", "heading": "IN THE COURT OF THE {court_type}", "format": "O.S. No."},
            "commercial": {"threshold": 300000, "act": "Commercial Courts Act, 2015"},
        },
        "procedural_prerequisites": ["section_12a_mediation", "arbitration_clause"],
        "limitation": {"article": "55", "period": "Three years", "from": "the date when the right to sue accrues"},
        "coa_type": "single_event",
        "court_fee_statute": {"Karnataka": "Karnataka Court Fees and Suits Valuation Act", "_default": "Court Fees Act, 1870"},
    }


@pytest.fixture
def minimal_mandatory_provisions():
    return {
        "limitation": {
            "article": "55",
            "period": "Three years",
            "from": "the date when the right to sue accrues",
            "description": "Three years from the date of breach",
        },
        "verified_provisions": [
            {"section": "Section 73", "act": "Indian Contract Act, 1872", "text": "Compensation for breach"},
            {"section": "Section 74", "act": "Indian Contract Act, 1872", "text": "Liquidated damages"},
        ],
    }


# ===========================================================================
# A) Template Engine Tests
# ===========================================================================

class TestTemplateEngine:
    """Test TemplateEngine.assemble(): deterministic section generation."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.templates.engine import TemplateEngine
        self.TemplateEngine = TemplateEngine

    def test_assemble_returns_string(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert isinstance(result, str)
        assert len(result) > 500

    def test_assemble_contains_generate_markers(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "{{GENERATE:FACTS" in result
        # v10.0: contract family uses BREACH_PARTICULARS gap (legacy: BREACH)
        assert "{{GENERATE:BREACH_PARTICULARS" in result or "{{GENERATE:BREACH}}" in result
        assert "{{GENERATE:DAMAGES" in result

    def test_assemble_contains_court_heading(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "IN THE COURT" in result
        assert "Bengaluru" in result

    def test_assemble_contains_parties(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "Rajesh Kumar" in result
        assert "ABC Pvt Ltd" in result
        assert "PLAINTIFF" in result
        assert "DEFENDANT" in result

    def test_assemble_contains_verification(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "VERIFICATION" in result
        assert "DEPONENT" in result

    def test_assemble_contains_advocate_block(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "{{ADVOCATE_NAME}}" in result

    def test_assemble_contains_limitation(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "LIMITATION" in result
        assert "Article 55" in result

    def test_limitation_none(self, minimal_intake, minimal_classify, minimal_lkb_brief):
        """article=NONE → no Article citation."""
        engine = self.TemplateEngine()
        prov = {"limitation": {"article": "NONE", "description": "No limitation applies to partition."}}
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=prov,
        )
        assert "LIMITATION" in result
        assert "No limitation applies" in result or "reasonable time" in result
        assert "Article NONE" not in result

    def test_limitation_unknown(self, minimal_intake, minimal_classify, minimal_lkb_brief):
        """article=UNKNOWN → placeholder when LKB also has no data."""
        engine = self.TemplateEngine()
        prov = {"limitation": {"article": "UNKNOWN"}}
        # Use LKB brief with UNKNOWN limitation too — otherwise the engine
        # falls back to LKB's real limitation article (correct behavior).
        lkb_with_unknown_lim = dict(minimal_lkb_brief)
        lkb_with_unknown_lim["limitation"] = {"article": "UNKNOWN"}
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=lkb_with_unknown_lim,
            mandatory_provisions=prov,
        )
        assert "{{LIMITATION_ARTICLE}}" in result

    def test_assemble_contains_prayer(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "PRAYER" in result
        # Prayer is now LLM-generated via {{GENERATE:PRAYER}} — verify gap constraints exist
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        cause_type = minimal_classify.get("cause_type", "breach_of_contract")
        gaps = resolve_gap_definitions(minimal_lkb_brief, cause_type)
        if gaps:
            prayer_gap = next((g for g in gaps if g["gap_id"] == "PRAYER"), None)
            assert prayer_gap is not None, "PRAYER gap should exist in gap_definitions"

    def test_assemble_contains_documents_list(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "LIST OF DOCUMENTS" in result
        assert "Annexure A" in result

    def test_assemble_contains_legal_basis(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        # Legal basis is now LLM-generated via {{GENERATE:LEGAL_BASIS}} marker
        assert "LEGAL_BASIS" in result or "LEGAL BASIS" in result

    def test_paragraph_numbering_continuous(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        # Extract all paragraph numbers from template sections
        numbers = [int(m.group(1)) for m in re.finditer(r"(?m)^(\d+)\.\s", result)]
        # They should be consecutive (ascending, no gaps within template parts)
        for i in range(1, len(numbers)):
            assert numbers[i] > numbers[i - 1], f"Non-ascending paragraphs: {numbers[i-1]} -> {numbers[i]}"

    def test_empty_intake_uses_placeholders(self, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        """Empty intake → placeholder values in parties/jurisdiction."""
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake={},
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "{{PLAINTIFF_NAME}}" in result
        assert "{{DEFENDANT_NAME}}" in result

    def test_commercial_has_maintainability(self, minimal_intake, minimal_lkb_brief, minimal_mandatory_provisions):
        """Commercial suit → includes maintainability section."""
        classify = {"doc_type": "commercial_suit", "cause_type": "breach_dealership_franchise", "law_domain": "Civil"}
        # Ensure LKB has commercial court rules so is_commercial triggers
        lkb = dict(minimal_lkb_brief)
        lkb["detected_court"] = {"court": "Commercial Court", "heading": "IN THE COURT OF THE {court_type}", "format": "O.S. No."}
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=classify,
            lkb_brief=lkb,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "COMMERCIAL COURT MAINTAINABILITY" in result
        assert "STATEMENT OF TRUTH" in result

    def test_non_commercial_no_maintainability(self, minimal_intake, minimal_lkb_brief, minimal_mandatory_provisions):
        """Non-commercial suit → no maintainability section."""
        classify = {"doc_type": "plaint", "cause_type": "money_recovery_loan", "law_domain": "Civil"}
        lkb = dict(minimal_lkb_brief)
        lkb["detected_court"] = {"court": "District Court", "heading": "IN THE COURT OF THE {court_type}", "format": "O.S. No."}
        engine = self.TemplateEngine()
        result = engine.assemble(
            intake=minimal_intake,
            classify=classify,
            lkb_brief=lkb,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "COMMERCIAL COURT MAINTAINABILITY" not in result


# ===========================================================================
# B) Gap Fill Prompt Tests
# ===========================================================================

class TestGapFillPrompt:
    """Test gap_fill_prompt.py: parsing, merging, renumbering."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.prompts.gap_fill_prompt import (
            build_gap_fill_system_prompt,
            build_gap_fill_user_prompt,
            parse_gap_fill_response,
            merge_template_with_gaps,
            renumber_paragraphs,
        )
        self.build_system = build_gap_fill_system_prompt
        self.build_user = build_gap_fill_user_prompt
        self.parse = parse_gap_fill_response
        self.merge = merge_template_with_gaps
        self.renumber = renumber_paragraphs

    # --- parse_gap_fill_response ---

    def test_parse_all_three_sections(self):
        response = (
            "{{GENERATE:FACTS}}\n"
            "5. The plaintiff entered into an agreement.\n\n"
            "{{GENERATE:BREACH}}\n"
            "8. The defendant breached the agreement.\n\n"
            "{{GENERATE:DAMAGES}}\n"
            "10. The plaintiff suffered damages of Rs. 15,00,000."
        )
        result = self.parse(response)
        assert "agreement" in result["facts"]
        assert "breached" in result["breach"]
        assert "damages" in result["damages"]

    def test_parse_with_start_para_marker(self):
        response = (
            "{{GENERATE:FACTS|start_para=5}}\n"
            "5. Facts paragraph one.\n\n"
            "{{GENERATE:BREACH}}\n"
            "Breach details.\n\n"
            "{{GENERATE:DAMAGES}}\n"
            "Damages details."
        )
        result = self.parse(response)
        assert "Facts paragraph one" in result["facts"]
        assert "Breach details" in result["breach"]
        assert "Damages details" in result["damages"]

    def test_parse_empty_response(self):
        result = self.parse("")
        assert result["facts"] == ""
        assert result["breach"] == ""
        assert result["damages"] == ""

    def test_parse_partial_response(self):
        """Only FACTS marker present."""
        response = "{{GENERATE:FACTS}}\nSome facts here."
        result = self.parse(response)
        assert "Some facts here" in result["facts"]
        assert result["breach"] == ""
        assert result["damages"] == ""

    # --- merge_template_with_gaps ---

    def test_merge_replaces_markers(self):
        template = (
            "HEADER\n\n"
            "{{GENERATE:FACTS|start_para=1}}\n\n"
            "{{GENERATE:BREACH}}\n\n"
            "{{GENERATE:DAMAGES}}\n\n"
            "FOOTER"
        )
        gaps = {
            "facts": "1. The plaintiff states...",
            "breach": "2. The defendant breached...",
            "damages": "3. Damages are Rs. 15 lakh.",
        }
        result = self.merge(template, gaps)
        assert "FACTS OF THE CASE" in result
        assert "BREACH PARTICULARS" in result
        assert "DAMAGES" in result
        assert "{{GENERATE:" not in result
        assert "HEADER" in result
        assert "FOOTER" in result

    def test_merge_unfilled_markers_become_placeholder(self):
        template = "{{GENERATE:FACTS|start_para=1}}\n{{GENERATE:BREACH}}\n{{GENERATE:DAMAGES}}"
        gaps = {"facts": "Some facts", "breach": "", "damages": ""}
        result = self.merge(template, gaps)
        assert "FACTS OF THE CASE" in result
        # Unfilled markers should become {{SECTION_NOT_GENERATED}}
        assert "{{SECTION_NOT_GENERATED}}" in result

    def test_merge_uses_injunction_specific_section_headings(self):
        template = (
            "{{GENERATE:FACTS|start_para=1}}\n\n"
            "{{GENERATE:BREACH}}\n\n"
            "{{GENERATE:DAMAGES}}"
        )
        gaps = {
            "facts": "1. The Plaintiff is in possession of the agricultural land.",
            "breach": "2. The Defendant attempted to trespass into the land.",
            "damages": "3. Monetary compensation is not an adequate remedy.",
        }
        result = self.merge(template, gaps, cause_type="permanent_injunction")
        assert "PLAINTIFF RIGHT AND DEFENDANT INTERFERENCE" in result
        assert "IRREPARABLE HARM AND BALANCE OF CONVENIENCE" in result
        assert "BREACH PARTICULARS" not in result
        assert "\nDAMAGES\n" not in result

    # --- renumber_paragraphs ---

    def test_renumber_continuous(self):
        text = "1. First para.\n3. Third para.\n7. Seventh para."
        result = self.renumber(text)
        # renumber_paragraphs replaces "N. " with "N." (counter + period)
        assert result.startswith("1.")
        assert "2." in result
        assert "3." in result
        # Original numbers should not remain
        assert "7." not in result

    def test_renumber_preserves_non_paragraph_numbers(self):
        text = "1. First para.\nRs. 15,00,000/- is claimed.\n2. Second para."
        result = self.renumber(text)
        assert "Rs. 15,00,000/-" in result
        # Should have paragraphs 1 and 2
        lines = result.split("\n")
        assert lines[0].startswith("1.")
        assert lines[2].startswith("2.")

    # --- build prompts ---

    def test_system_prompt_contains_rules(self):
        result = self.build_system()
        assert "RULES" in result
        assert "{{GENERATE:FACTS}}" in result
        assert "NEVER fabricate" in result

    def test_user_prompt_contains_user_facts_first(self):
        result = self.build_user(
            user_request="Draft a suit for damages",
            assembled_template="TEMPLATE HERE",
            facts_summary="Plaintiff signed agreement",
            parties_context="PLAINTIFF: Rajesh Kumar",
            evidence_context="Annexure A: Agreement",
            verified_provisions="Section 73 ICA",
            rag_context="Some RAG chunks",
            cause_type="breach_of_contract",
        )
        # User facts should be at the top
        facts_pos = result.find("USER FACTS:")
        template_pos = result.find("DOCUMENT TEMPLATE")
        assert facts_pos < template_pos, "User facts should appear before template"

    def test_user_prompt_includes_damages_categories(self):
        result = self.build_user(
            user_request="Draft suit",
            assembled_template="TEMPLATE",
            facts_summary="",
            parties_context="",
            evidence_context="",
            verified_provisions="",
            rag_context="",
            damages_categories=["principal_amount", "loss_of_profit"],
        )
        assert "DAMAGES CATEGORIES" in result
        assert "principal amount" in result
        assert "loss of profit" in result

    def test_user_prompt_includes_injunction_constraints(self):
        result = self.build_user(
            user_request="Draft a suit for permanent injunction over agricultural land.",
            assembled_template="TEMPLATE",
            facts_summary="Plaintiff in peaceful possession of agricultural land.",
            parties_context="",
            evidence_context="Revenue records.",
            verified_provisions="Section 38 Specific Relief Act, 1963",
            rag_context="",
            cause_type="permanent_injunction",
        )
        assert "INJUNCTION DRAFTING CONSTRAINTS" in result
        assert "do not plead a money damages claim or interest" in result.lower()

    def test_user_prompt_includes_contract_constraints(self):
        result = self.build_user(
            user_request="Draft a suit for damages for breach of contract under Section 73.",
            assembled_template="TEMPLATE",
            facts_summary="Plaintiff signed a contract and Defendant failed to perform.",
            parties_context="",
            evidence_context="Annexure P-1: Contract",
            verified_provisions="Section 73 Indian Contract Act, 1872",
            rag_context="",
            cause_type="breach_of_contract",
            damages_categories=["actual_loss"],
        )
        assert "CONTRACT DRAFTING CONSTRAINTS" in result
        assert "do not use repudiatory" in result.lower()
        assert "do not introduce additional loss heads" in result.lower()
        assert "do not add cause-of-action" in result.lower()
        assert "annexure p-1" in result.lower()
        assert "annexure p-2" in result.lower()
        assert "not a specific performance track" in result.lower()
        assert "{{TOTAL_SUIT_VALUE}}" in result


# ===========================================================================
# C) Draft Template Fill Helpers
# ===========================================================================

class TestDraftTemplateFillHelpers:
    """Test helper functions from draft_template_fill.py."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.draft_template_fill import (
            _build_facts_summary,
            _build_parties_context,
            _build_evidence_context,
            _build_verified_provisions,
            _build_rag_context,
            _strip_markdown_fences,
            _clean_encoding_artifacts,
            _collect_placeholders,
        )
        self.facts_summary = _build_facts_summary
        self.parties_context = _build_parties_context
        self.evidence_context = _build_evidence_context
        self.verified_provisions = _build_verified_provisions
        self.rag_context = _build_rag_context
        self.strip_fences = _strip_markdown_fences
        self.clean_encoding = _clean_encoding_artifacts
        self.collect_placeholders = _collect_placeholders

    # --- _build_facts_summary ---

    def test_facts_summary_includes_summary(self, minimal_intake):
        result = self.facts_summary(minimal_intake)
        assert "Plaintiff entered into dealership" in result

    def test_facts_summary_includes_chronology(self, minimal_intake):
        result = self.facts_summary(minimal_intake)
        assert "01.01.2024" in result
        assert "Agreement signed" in result

    def test_facts_summary_includes_amounts(self, minimal_intake):
        result = self.facts_summary(minimal_intake)
        assert "15,00,000" in result

    def test_facts_summary_empty_intake(self):
        result = self.facts_summary({})
        assert result == ""

    # --- _build_parties_context ---

    def test_parties_context(self, minimal_intake):
        result = self.parties_context(minimal_intake)
        assert "PLAINTIFF" in result
        assert "Rajesh Kumar" in result
        assert "DEFENDANT" in result
        assert "ABC Pvt Ltd" in result

    def test_parties_context_empty(self):
        result = self.parties_context({})
        assert result == ""

    # --- _build_evidence_context ---

    def test_evidence_context(self, minimal_intake):
        result = self.evidence_context(minimal_intake)
        assert "Annexure P-1" in result
        assert "Dealership agreement" in result
        assert "Annexure P-2" in result

    def test_evidence_context_empty(self):
        result = self.evidence_context({})
        assert result == ""

    # --- _build_verified_provisions ---

    def test_verified_provisions(self, minimal_mandatory_provisions):
        result = self.verified_provisions(minimal_mandatory_provisions)
        assert "Section 73" in result
        assert "Indian Contract Act" in result

    def test_verified_provisions_empty(self):
        result = self.verified_provisions({})
        assert result == ""

    # --- _build_rag_context ---

    def test_rag_context_limits_to_5(self):
        chunks = [{"text": f"Chunk {i} text", "source": {"book": f"Book {i}"}} for i in range(10)]
        result = self.rag_context({"chunks": chunks})
        # Should have [1] through [5] only
        assert "[5]" in result
        assert "[6]" not in result

    def test_rag_context_empty(self):
        result = self.rag_context({})
        assert result == ""

    # --- _strip_markdown_fences ---

    def test_strip_fences(self):
        text = "```text\nHello world\n```"
        assert self.strip_fences(text) == "Hello world"

    def test_strip_fences_plaintext(self):
        text = "```plaintext\nSome text\n```"
        assert self.strip_fences(text) == "Some text"

    def test_strip_fences_no_fences(self):
        text = "No fences here"
        assert self.strip_fences(text) == "No fences here"

    # --- _clean_encoding_artifacts ---

    def test_clean_encoding_removes_replacement_char(self):
        text = "Hello\ufffdWorld"
        assert "\ufffd" not in self.clean_encoding(text)

    def test_clean_encoding_removes_zero_width(self):
        text = "Hello\u200bWorld"
        assert "\u200b" not in self.clean_encoding(text)

    # --- _collect_placeholders ---

    def test_collect_placeholders(self):
        text = "The plaintiff {{PLAINTIFF_NAME}} claims Rs. {{TOTAL_SUIT_VALUE}}."
        result = self.collect_placeholders(text)
        keys = [p["key"] for p in result]
        assert "PLAINTIFF_NAME" in keys
        assert "TOTAL_SUIT_VALUE" in keys

    def test_collect_placeholders_skips_generate(self):
        text = "{{GENERATE:FACTS}} and {{PLAINTIFF_NAME}}"
        result = self.collect_placeholders(text)
        keys = [p["key"] for p in result]
        assert "PLAINTIFF_NAME" in keys
        # GENERATE markers should be excluded
        assert not any("GENERATE" in k for k in keys)

    def test_collect_placeholders_no_duplicates(self):
        text = "{{NAME}} is {{NAME}} and {{NAME}}"
        result = self.collect_placeholders(text)
        assert len(result) == 1


# ===========================================================================
# D) Graph Compilation Tests
# ===========================================================================

class TestGraphV8:
    """Test that graph includes v8.1 nodes."""

    def test_graph_has_draft_template_fill_node(self):
        from app.agents.drafting_agents.drafting_graph import get_drafting_graph
        graph = get_drafting_graph()
        node_names = list(graph.nodes.keys())
        assert "draft_template_fill" in node_names

    def test_graph_has_both_draft_nodes(self):
        from app.agents.drafting_agents.drafting_graph import get_drafting_graph
        graph = get_drafting_graph()
        node_names = list(graph.nodes.keys())
        assert "draft_freetext" in node_names
        assert "draft_template_fill" in node_names

    def test_graph_compiles_with_checkpointer(self):
        from app.agents.drafting_agents.drafting_graph import get_drafting_graph
        graph = get_drafting_graph(use_checkpointer=True)
        assert graph is not None

    def test_graph_singleton_exists(self):
        from app.agents.drafting_agents.drafting_graph import drafting_graph
        assert drafting_graph is not None


# ===========================================================================
# E) Template Engine Section Builders (detailed)
# ===========================================================================

class TestTemplateEngineSections:
    """Test individual section builders in TemplateEngine."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.templates.engine import TemplateEngine
        self.engine = TemplateEngine()

    def test_court_heading(self):
        court = {"court": "District Court", "heading": "IN THE COURT OF THE {court_type}", "format": "O.S. No."}
        jurisdiction = {"city": "Bengaluru"}
        result = self.engine._court_heading(court, jurisdiction)
        assert "IN THE COURT OF THE District Court" in result
        assert "AT Bengaluru" in result

    def test_court_heading_missing_city(self):
        court = {"court": "District Court", "heading": "IN THE COURT OF THE {court_type}", "format": "O.S. No."}
        jurisdiction = {}
        result = self.engine._court_heading(court, jurisdiction)
        assert "{{COURT_CITY}}" in result

    def test_parties_block(self):
        parties = {
            "primary": {"name": "John", "age": "30", "occupation": "Engineer", "address": "Delhi"},
            "opposite": [{"name": "Corp Ltd", "age": "N/A", "occupation": "Company", "address": "Mumbai"}],
        }
        result = self.engine._parties_block(parties)
        assert "John" in result
        assert "Corp Ltd" in result
        assert "PLAINTIFF" in result
        assert "DEFENDANT" in result

    def test_parties_block_empty(self):
        result = self.engine._parties_block({})
        assert "{{PLAINTIFF_NAME}}" in result
        assert "{{DEFENDANT_NAME}}" in result

    def test_limitation_section_with_article(self):
        lim = {"article": "55", "period": "Three years", "from": "the date of breach"}
        lkb = {}
        result = self.engine._limitation_section(lim, lkb)
        assert "Article 55" in result
        assert "three years" in result.lower()

    def test_limitation_section_none(self):
        lim = {"article": "NONE", "description": "No limitation applies."}
        result = self.engine._limitation_section(lim, {})
        assert "No limitation applies" in result
        assert "reasonable time" in result

    def test_limitation_section_special_reference(self):
        lim = {
            "article": "N/A",
            "reference": "Section 34(3) of the Arbitration and Conciliation Act, 1996",
            "act": "Arbitration and Conciliation Act, 1996",
            "period": "Three months and thirty days",
            "from": "the date of receipt of the award",
        }
        result = self.engine._limitation_section(lim, {})
        assert "Section 34(3)" in result
        assert "Limitation Act, 1963" not in result
        assert "three months" in result.lower()

    def test_limitation_section_unknown(self):
        lim = {"article": "UNKNOWN"}
        result = self.engine._limitation_section(lim, {})
        assert "{{LIMITATION_ARTICLE}}" in result

    def test_section_12a_mediation_done(self):
        intake = {}
        result = self.engine._section_12a(intake, "mediation was conducted and certificate issued")
        assert "SECTION 12A" in result
        assert "non-settlement" in result or "mediation" in result.lower()

    def test_section_12a_urgent(self):
        intake = {}
        result = self.engine._section_12a(intake, "urgent interim relief is needed")
        assert "SECTION 12A" in result
        assert "urgent" in result.lower()

    def test_section_12a_unknown(self):
        intake = {}
        result = self.engine._section_12a(intake, "just a normal suit")
        assert "SECTION 12A" in result
        assert "{{MEDIATION_STATUS" in result

    def test_arbitration_disclosure_present(self):
        intake = {}
        result = self.engine._arbitration_disclosure(intake, "agreement contains arbitration clause")
        assert "ARBITRATION DISCLOSURE" in result
        assert "Section 8" in result

    def test_arbitration_disclosure_absent(self):
        intake = {}
        result = self.engine._arbitration_disclosure(intake, "normal agreement")
        # When no arbitration mentioned in intake, section is skipped entirely
        assert result == ""

    def test_legal_basis_uses_doctrine_templates(self):
        lkb = {"permitted_doctrines": ["breach_of_contract", "damages_s73"]}
        self.engine._para = 0  # reset counter
        result = self.engine._legal_basis(lkb)
        assert "LEGAL BASIS" in result
        assert "breach" in result.lower()
        assert "Section 73" in result

    def test_prayer_includes_aggregate_decree(self):
        lkb = {"damages_categories": ["principal_amount", "loss_of_profit"]}
        result = self.engine._prayer(lkb)
        assert "PRAYER" in result
        assert "decree" in result.lower()
        assert "TOTAL_SUIT_VALUE" in result
        # Individual damage heads now in Schedule of Damages, not prayer
        schedule = self.engine._damages_schedule(lkb)
        assert "PRINCIPAL_AMOUNT_AMOUNT" in schedule
        assert "LOSS_OF_PROFIT_AMOUNT" in schedule

    def test_documents_list_with_evidence(self):
        evidence = [
            {"type": "Agreement", "description": "Dealership agreement"},
            {"type": "Notice", "description": "Legal notice"},
        ]
        result = self.engine._documents_list(evidence)
        assert "Annexure A" in result
        assert "Annexure B" in result
        assert "Dealership agreement" in result

    def test_documents_list_empty(self):
        result = self.engine._documents_list([])
        assert "{{DOCUMENTS_TO_BE_ANNEXED}}" in result

    def test_damages_schedule(self):
        lkb = {"damages_categories": ["principal_amount", "loss_of_goodwill"]}
        result = self.engine._damages_schedule(lkb)
        assert "SCHEDULE OF DAMAGES" in result
        assert "Principal amount" in result
        assert "Loss of goodwill" in result

    def test_cause_of_action_single_event(self):
        lkb = {"coa_type": "single_event"}
        facts = {"cause_of_action_date": "15.06.2024"}
        self.engine._para = 0
        result = self.engine._cause_of_action(lkb, facts)
        assert "CAUSE OF ACTION" in result
        assert "15.06.2024" in result
        assert "loss and" in result.lower()
        assert "not a continuing cause of action" not in result.lower()

    def test_cause_of_action_continuing(self):
        lkb = {"coa_type": "continuing"}
        facts = {}
        self.engine._para = 0
        result = self.engine._cause_of_action(lkb, facts)
        assert "continuing" in result.lower()

    def test_possession_licensee_template_uses_possession_core_sections(self):
        lkb = {
            "display_name": "Recovery of possession — revoked licence (licensee)",
            "required_reliefs": ["possession_decree", "mesne_profits_inquiry_order_xx_r12", "costs"],
            "alternative_acts": [
                {"act": "Indian Easements Act, 1882", "sections": ["Section 52", "Section 60", "Section 61", "Section 62", "Section 63"]},
            ],
            "court_fee_statute": {"Karnataka": "Karnataka Court Fees and Suits Valuation Act, 1958"},
        }
        facts = {
            "property_address": "Survey No. 45, Koramangala, Bengaluru",
            "revocation_date": "15.03.2024",
        }
        jurisdiction = {"city": "Bengaluru", "state": "Karnataka"}

        self.engine._para = 0
        title = self.engine._suit_title(lkb, {}, "recovery_of_possession_licensee")
        jurisdiction_text = self.engine._jurisdiction_section(jurisdiction, {}, False, "recovery_of_possession_licensee", facts)
        legal_basis = self.engine._legal_basis(lkb, "recovery_of_possession_licensee")
        cause = self.engine._cause_of_action(lkb, facts, "recovery_of_possession_licensee")
        interest = self.engine._interest_section(lkb, "recovery_of_possession_licensee")
        prayer = self.engine._prayer(lkb, "recovery_of_possession_licensee")

        assert "WITH MESNE PROFITS AND COSTS" in title
        assert "Section 16" in jurisdiction_text
        assert "cause of action arose" not in jurisdiction_text.lower()
        assert "Indian Easements Act, 1882" in legal_basis
        assert "revoked / came to an end" in cause
        assert interest == ""
        assert "recovery of possession" in prayer.lower()
        assert "Order XX Rule 12" in prayer
        assert "towards damages" not in prayer.lower()

    def test_permanent_injunction_template_uses_non_monetary_core_sections(self):
        lkb = {
            "display_name": "Suit for perpetual / permanent injunction",
            "required_reliefs": ["permanent_injunction_decree", "costs"],
            "court_fee_statute": {"Karnataka": "Karnataka Court Fees and Suits Valuation Act, 1958"},
        }
        facts = {
            "summary": "Plaintiff is in peaceful possession of agricultural land supported by revenue records and defendant is attempting to dispossess the plaintiff unlawfully.",
            "land_survey_number": "Survey No. 12",
            "property_address": "Survey No. 12, Hosakote Village, Bengaluru Rural",
            "cause_of_action_date": "15.03.2026",
        }
        jurisdiction = {"city": "Bengaluru", "state": "Karnataka"}

        self.engine._para = 0
        title = self.engine._suit_title(lkb, {}, "permanent_injunction")
        jurisdiction_text = self.engine._jurisdiction_section(jurisdiction, {}, False, "permanent_injunction", facts)
        legal_basis = self.engine._legal_basis(lkb, "permanent_injunction", facts)
        cause = self.engine._cause_of_action(lkb, facts, "permanent_injunction")
        valuation = self.engine._valuation_court_fee(lkb, facts, "Karnataka", None, "permanent_injunction")
        interest = self.engine._interest_section(lkb, "permanent_injunction")
        prayer = self.engine._prayer(lkb, "permanent_injunction")

        assert "WITH COSTS" in title
        assert "WITH INTEREST AND COSTS" not in title
        assert "Section 16" in jurisdiction_text
        assert "carries on business / resides" not in jurisdiction_text.lower()
        assert "Section 38" in legal_basis
        assert "Section 34 of the Code of Civil Procedure" not in legal_basis
        assert "15.03.2026" in cause
        assert "legal notice" not in cause.lower()
        assert "suit for injunction" in valuation.lower()
        assert interest == ""
        assert "permanent injunction" in prayer.lower()
        assert "towards damages" not in prayer.lower()

    def test_easement_template_uses_declaration_injunction_and_dual_schedule(self):
        lkb = {
            "display_name": "Suit for declaration / protection of easement rights",
            "required_reliefs": [
                "declaration_decree",
                "mandatory_injunction_decree",
                "permanent_injunction_decree",
                "costs",
            ],
            "court_fee_statute": {"Karnataka": "Karnataka Court Fees and Suits Valuation Act, 1958"},
        }
        facts = {
            "summary": "Plaintiff has been using a pathway for more than twenty years to access property and the defendant has now obstructed it.",
            "property_address": "Survey No. 12, Hosakote Village, Bengaluru Rural",
            "land_survey_number": "Survey No. 12",
            "pathway_description": "Cart track / pathway running through the Defendant's land to the Plaintiff's property",
            "pathway_measurements": "Width 10 feet, length 120 feet",
            "pathway_boundaries": "East: Defendant's field, West: Plaintiff's field, North: Village road, South: Canal",
            "cause_of_action_date": "15.03.2026",
        }
        jurisdiction = {"city": "Bengaluru", "state": "Karnataka"}

        self.engine._para = 0
        title = self.engine._suit_title(lkb, {}, "easement")
        jurisdiction_text = self.engine._jurisdiction_section(jurisdiction, {}, False, "easement", facts)
        legal_basis = self.engine._legal_basis(lkb, "easement", facts)
        cause = self.engine._cause_of_action(lkb, facts, "easement")
        prayer = self.engine._prayer(lkb, "easement")
        schedule = self.engine._schedule_of_easement(facts)

        assert "SUIT FOR SUIT FOR" not in title
        assert "EASEMENTARY RIGHT" in title
        assert "Section 16" in jurisdiction_text
        assert "Section 15" in legal_basis
        assert "Section 34" in legal_basis
        assert "Sections 38 and 39" in legal_basis
        assert "obstructed / threatened to obstruct" in cause
        assert "declaring" in prayer.lower()
        assert "mandatory injunction" in prayer.lower()
        assert "permanent injunction" in prayer.lower()
        assert "towards damages" not in prayer.lower()
        assert "SCHEDULE A - DOMINANT HERITAGE" in schedule
        assert "SCHEDULE B - PATHWAY / SERVIENT HERITAGE" in schedule


# ===========================================================================
# F) Integration: Template Assembly + Gap Fill + Merge
# ===========================================================================

class TestTemplateMergeIntegration:
    """Test full flow: assemble → parse mock LLM response → merge → renumber."""

    def test_full_flow(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        from app.agents.drafting_agents.templates.engine import TemplateEngine
        from app.agents.drafting_agents.prompts.gap_fill_prompt import (
            parse_gap_fill_response,
            merge_template_with_gaps,
            renumber_paragraphs,
        )
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions

        # Phase 1: Assemble template
        engine = TemplateEngine()
        cause_type = minimal_classify.get("cause_type", "")
        template = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )
        assert "{{GENERATE:FACTS" in template

        # Resolve gap_definitions for this cause type (v10.0)
        gap_defs = resolve_gap_definitions(minimal_lkb_brief, cause_type)

        # Phase 2: Simulate LLM response (use v10.0 gap IDs if available)
        if gap_defs:
            gap_ids = [g["gap_id"] for g in gap_defs]
            mock_parts = []
            for i, gid in enumerate(gap_ids):
                para = 5 + i * 2
                mock_parts.append(
                    f"{{{{GENERATE:{gid}}}}}\n"
                    f"{para}. Mock content for {gid} section.\n\n"
                    f"{para+1}. Additional paragraph for {gid}."
                )
            mock_llm = "\n\n".join(mock_parts)
        else:
            mock_llm = (
                "{{GENERATE:FACTS|start_para=5}}\n"
                "5. The Plaintiff entered into a dealership agreement on 01.01.2024.\n\n"
                "6. The Defendant illegally terminated the agreement on 15.06.2024.\n\n"
                "{{GENERATE:BREACH}}\n"
                "7. The Defendant breached the terms of the agreement.\n\n"
                "{{GENERATE:DAMAGES}}\n"
                "8. The Plaintiff suffered damages amounting to Rs. 15,00,000/-."
            )

        gaps = parse_gap_fill_response(mock_llm, gap_definitions=gap_defs)
        assert any(v for v in gaps.values())  # At least one gap filled

        # Phase 3: Merge
        merged = merge_template_with_gaps(template, gaps, cause_type=cause_type, gap_definitions=gap_defs)
        assert "{{GENERATE:" not in merged
        assert "FACTS" in merged  # Some FACTS heading present

        # Renumber
        final = renumber_paragraphs(merged)
        assert "IN THE COURT" in final
        assert "Rajesh Kumar" in final
        assert "VERIFICATION" in final
        assert "{{ADVOCATE_NAME}}" in final

        # Verify no gap markers remain
        assert "{{GENERATE:" not in final
        assert "{{SECTION_NOT_GENERATED}}" not in final

    def test_merge_with_missing_sections(self, minimal_intake, minimal_classify, minimal_lkb_brief, minimal_mandatory_provisions):
        """If LLM only generates FACTS, others become placeholders."""
        from app.agents.drafting_agents.templates.engine import TemplateEngine
        from app.agents.drafting_agents.prompts.gap_fill_prompt import (
            parse_gap_fill_response,
            merge_template_with_gaps,
        )
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions

        cause_type = minimal_classify.get("cause_type", "")
        engine = TemplateEngine()
        template = engine.assemble(
            intake=minimal_intake,
            classify=minimal_classify,
            lkb_brief=minimal_lkb_brief,
            mandatory_provisions=minimal_mandatory_provisions,
        )

        gap_defs = resolve_gap_definitions(minimal_lkb_brief, cause_type)
        mock_llm = "{{GENERATE:FACTS}}\nSome facts."
        gaps = parse_gap_fill_response(mock_llm, gap_definitions=gap_defs)
        merged = merge_template_with_gaps(template, gaps, cause_type=cause_type, gap_definitions=gap_defs)

        # Facts replaced
        assert "FACTS" in merged
        # Others should be {{SECTION_NOT_GENERATED}}
        assert "{{SECTION_NOT_GENERATED}}" in merged

    def test_merge_uses_possession_section_headings(self):
        from app.agents.drafting_agents.prompts.gap_fill_prompt import merge_template_with_gaps

        template = "{{GENERATE:FACTS}}\n\n{{GENERATE:BREACH}}\n\n{{GENERATE:DAMAGES}}"
        gaps = {
            "facts": "1. Facts text.",
            "breach": "2. Occupation text.",
            "damages": "3. Mesne profits text.",
        }
        merged = merge_template_with_gaps(template, gaps, cause_type="recovery_of_possession_licensee")

        assert "FACTS OF THE CASE" in merged
        assert "DEFENDANT'S UNAUTHORIZED OCCUPATION" in merged
        assert "MESNE PROFITS" in merged


# ===========================================================================
# G) Settings Flag Test
# ===========================================================================

class TestSettingsFlag:
    """Test TEMPLATE_ENGINE_ENABLED setting exists."""

    def test_template_engine_enabled_exists(self):
        from app.config.settings import Settings
        assert hasattr(Settings, "model_fields") or hasattr(Settings, "__fields__")
        # Check the field exists
        s = Settings.__fields__ if hasattr(Settings, "__fields__") else Settings.model_fields
        assert "TEMPLATE_ENGINE_ENABLED" in s

    def test_template_engine_default_false(self):
        from app.config import settings
        assert hasattr(settings, "TEMPLATE_ENGINE_ENABLED")
        # Default is False (v5.0 freetext stays default)
        assert settings.TEMPLATE_ENGINE_ENABLED is False
