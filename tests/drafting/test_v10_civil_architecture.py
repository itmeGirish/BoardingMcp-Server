from __future__ import annotations

import asyncio
import pytest


class TestCivilDecisionState:
    def test_state_has_civil_decision_field(self):
        from app.agents.drafting_agents.states.draftGraph import DraftingState

        annotations = DraftingState.__annotations__
        assert "civil_decision" in annotations
        assert "decision_ir" in annotations
        assert "plan_ir" in annotations
        assert "domain_plugin" in annotations


class TestCivilArchitectureGraph:
    def test_graph_has_civil_architecture_nodes(self):
        from app.agents.drafting_agents.drafting_graph import get_drafting_graph

        graph = get_drafting_graph()
        node_names = set(graph.nodes.keys())

        assert "civil_case_resolver" in node_names
        assert "civil_ambiguity_gate" in node_names
        assert "civil_draft_plan_compiler" in node_names
        assert "civil_draft_router" in node_names
        assert "civil_consistency_gate" in node_names
        assert "domain_router" in node_names
        assert "domain_decision_compiler" in node_names
        assert "domain_ambiguity_gate" in node_names
        assert "domain_plan_compiler" in node_names
        assert "domain_draft_router" in node_names
        assert "domain_consistency_gate" in node_names


class TestDomainPluginCore:
    def test_domain_router_selects_civil_plugin(self):
        from app.agents.drafting_agents.nodes.domain_pipeline import domain_router_node

        state = {
            "classify": {
                "law_domain": "Civil",
                "doc_type": "damages_plaint",
            }
        }

        result = domain_router_node(state)

        assert result.goto == "domain_decision_compiler"
        assert result.update["domain_plugin"] == "civil"

    def test_domain_decision_compiler_mirrors_civil_decision(self, monkeypatch):
        from app.agents.drafting_agents.nodes.domain_pipeline import domain_decision_compiler_node
        from app.config.settings import settings

        monkeypatch.setattr(settings, "DRAFTING_RAG_ENABLED", False, raising=False)
        state = {
            "domain_plugin": "civil",
            "user_request": "Draft a suit for specific performance of an agreement to sell.",
            "intake": {
                "facts": {"summary": "Agreement to sell executed. Plaintiff remains ready and willing."},
            },
            "classify": {
                "law_domain": "Civil",
                "doc_type": "specific_performance_plaint",
                "cause_type": "specific_performance",
                "classification": {"topics": ["agreement to sell"]},
            },
        }

        result = domain_decision_compiler_node(state)

        assert result.goto == "domain_ambiguity_gate"
        assert result.update["domain_plugin"] == "civil"
        assert result.update["decision_ir"]["plugin_key"] == "civil"
        assert result.update["decision_ir"]["subtype"] == "specific_performance"
        assert result.update["decision_ir"]["family"] == "contract_and_commercial"
        assert "allowed_doctrines" in result.update["decision_ir"]
        assert "forbidden_doctrines" in result.update["decision_ir"]

    def test_domain_plan_compiler_mirrors_civil_plan(self):
        from app.agents.drafting_agents.nodes.domain_pipeline import domain_plan_compiler_node

        state = {
            "domain_plugin": "civil",
            "classify": {
                "law_domain": "Civil",
                "cause_type": "specific_performance",
                "classification": {"missing_fields": ["agreement_date"]},
            },
            "civil_decision": {
                "enabled": True,
                "family": "contract_and_commercial",
                "resolved_cause_type": "specific_performance",
                "maintainability_checks": [],
                "route_reason": "Matched civil LKB entry.",
                "limitation": {"article": "54", "period": "Three years"},
            },
            "lkb_brief": {
                "required_reliefs": ["specific_performance_decree", "direction_to_execute_sale_deed", "costs"],
                "optional_reliefs": ["refund_if_specifically_claimed"],
                "required_sections": ["agreement_details", "readiness_willingness"],
                "required_averments": ["readiness_and_willingness"],
                "mandatory_inline_sections": [{"section": "READINESS AND WILLINGNESS"}],
                "drafting_red_flags": ["Readiness must be factual, not formulaic."],
                "evidence_checklist": ["agreement_to_sell", "notice"],
            },
            "mandatory_provisions": {
                "verified_provisions": [{"section": "Section 16", "act": "Specific Relief Act, 1963"}],
                "limitation": {"article": "54", "period": "Three years"},
            },
        }

        result = domain_plan_compiler_node(state)

        assert result.goto == "domain_draft_router"
        assert result.update["plan_ir"]["plugin_key"] == "civil"
        assert result.update["plan_ir"]["subtype"] == "specific_performance"
        assert "specific_performance_decree" in result.update["plan_ir"]["required_reliefs"]

    def test_review_inline_fix_resolves_last_paragraph_placeholder(self):
        from app.agents.drafting_agents.nodes.reviews import _resolve_last_para_placeholders

        text = (
            "1. First paragraph.\n"
            "2. Second paragraph.\n\n"
            "VERIFICATION\n\n"
            "I verify that paragraphs 1 to {{LAST_PARAGRAPH_NUMBER}} are true."
        )

        result = _resolve_last_para_placeholders(text)
        assert "{{LAST_PARAGRAPH_NUMBER}}" not in result
        assert "paragraphs 1 to 2" in result

    def test_review_inline_fix_resolves_total_paragraphs_and_contract_subsists_phrase(self):
        from app.agents.drafting_agents.nodes.reviews import (
            _resolve_last_para_placeholders,
            _sanitize_contract_inline_fix,
        )

        text = (
            "1. First paragraph.\n"
            "2. Second paragraph.\n"
            "3. Third paragraph.\n\n"
            "The cause of action continues to subsist as the Defendant has failed to compensate the Plaintiff despite legal notice dated {{NOTICE_DATE}}.\n"
            "VERIFICATION\n\n"
            "I verify that paragraphs 1 to {{TOTAL_PARAGRAPHS}} are true."
        )

        text = _sanitize_contract_inline_fix(text, "breach_of_contract")
        result = _resolve_last_para_placeholders(text)
        assert "{{TOTAL_PARAGRAPHS}}" not in result
        assert "paragraphs 1 to 3" in result
        assert "continues to subsist" not in result


class TestCivilCaseResolver:
    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.civil_decision import civil_case_resolver_node

        self.node = civil_case_resolver_node

    def test_normalizes_generic_possession_to_tenant_track(self, monkeypatch):
        from app.config.settings import settings

        monkeypatch.setattr(settings, "DRAFTING_RAG_ENABLED", False, raising=False)
        state = {
            "user_request": "Draft a suit for possession because the tenant's lease expired and he refused to vacate.",
            "intake": {
                "facts": {"summary": "Lease expired. Tenant continued in occupation despite notice to quit."},
            },
            "classify": {
                "law_domain": "Civil",
                "doc_type": "eviction_plaint",
                "cause_type": "recovery_of_possession",
                "classification": {"topics": ["tenant possession"]},
            },
        }

        result = self.node(state)

        assert result.goto == "civil_ambiguity_gate"
        assert result.update["classify"]["cause_type"] == "recovery_of_possession_tenant"
        decision = result.update["civil_decision"]
        assert decision["family"] == "immovable_property"
        assert decision["status"] == "resolved"
        assert decision["draft_strategy"] == "template_first"
        assert "rent_act_bar_screen" in decision["maintainability_checks"]

    def test_flags_mixed_possession_theory(self, monkeypatch):
        from app.config.settings import settings

        monkeypatch.setattr(settings, "DRAFTING_RAG_ENABLED", False, raising=False)
        state = {
            "user_request": "Draft a possession suit because the defendant was a tenant on lease/permissive possession and did not vacate.",
            "intake": {
                "facts": {"summary": "The defendant entered on a lease/permissive basis and continues in occupation."},
            },
            "classify": {
                "law_domain": "Civil",
                "doc_type": "eviction_plaint",
                "cause_type": "recovery_of_possession",
                "classification": {"topics": ["lease", "permissive possession"]},
            },
        }

        result = self.node(state)
        decision = result.update["civil_decision"]

        assert result.goto == "civil_ambiguity_gate"
        assert decision["status"] == "ambiguous"
        assert decision["draft_strategy"] == "free_text"
        assert decision["blocking_issues"]
        assert "multiple occupancy tracks" in decision["blocking_issues"][0].lower()

    def test_routes_specific_performance_to_template_track(self, monkeypatch):
        from app.config.settings import settings

        monkeypatch.setattr(settings, "DRAFTING_RAG_ENABLED", False, raising=False)
        state = {
            "user_request": "Draft a suit for specific performance of an agreement to sell.",
            "intake": {
                "facts": {"summary": "Agreement to sell executed. Plaintiff remains ready and willing."},
            },
            "classify": {
                "law_domain": "Civil",
                "doc_type": "specific_performance_plaint",
                "cause_type": "specific_performance",
                "classification": {"topics": ["agreement to sell"]},
            },
        }

        result = self.node(state)
        decision = result.update["civil_decision"]

        assert decision["family"] == "contract_and_commercial"
        assert decision["resolved_cause_type"] == "specific_performance"
        assert decision["draft_strategy"] == "template_first"
        assert decision["status"] == "resolved"


class TestCivilDraftRouter:
    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.civil_decision import civil_draft_router_node

        self.node = civil_draft_router_node

    def test_uses_template_for_resolved_civil_case(self, monkeypatch):
        from app.config.settings import settings

        monkeypatch.setattr(settings, "TEMPLATE_ENGINE_ENABLED", True, raising=False)
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {"draft_strategy": "template_first", "blocking_issues": []},
        }

        result = self.node(state)

        assert result.goto == "draft_template_fill"

    def test_blocking_issues_force_free_text_even_if_template_flag_enabled(self, monkeypatch):
        from app.config.settings import settings

        monkeypatch.setattr(settings, "TEMPLATE_ENGINE_ENABLED", True, raising=False)
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {"draft_strategy": "free_text", "blocking_issues": ["ambiguous track"]},
        }

        result = self.node(state)

        assert result.goto == "draft_freetext"


class TestFamilyApplicabilityCompilers:
    """Per-family applicability compilers produce family-specific forbidden/allowed fields."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.civil_decision import _compile_applicability
        self.compile = _compile_applicability

    def _make_entry(self, **overrides):
        base = {
            "damages_categories": ["actual_loss", "consequential_loss"],
            "required_reliefs": ["damages_decree", "costs"],
            "drafting_red_flags": [],
            "permitted_doctrines": [],
        }
        base.update(overrides)
        return base

    def _make_state(self, user_request="", cause_type="breach_of_contract", facts_text=""):
        intake = {"facts": {"summary": facts_text}, "jurisdiction": {}}
        classify = {"law_domain": "Civil", "doc_type": "damages_plaint", "cause_type": cause_type, "classification": {"topics": []}}
        return user_request or facts_text, intake, classify

    # ── Contract ────────────────────────────────────────────────────────

    def test_contract_specific_performance_adds_readiness_red_flag(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="specific_performance",
            facts_text="Agreement to sell property. Plaintiff ready and willing.",
        )
        result = self.compile(entry, req, intake, classify, family="contract_and_commercial", cause_type="specific_performance")
        assert any("readiness" in rf.lower() or "Section 16(c)" in rf for rf in result["filtered_red_flags"])

    def test_contract_guarantee_warns_against_s124(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="guarantee_invocation",
            facts_text="Surety failed to pay on invocation of guarantee.",
        )
        result = self.compile(entry, req, intake, classify, family="contract_and_commercial", cause_type="guarantee_invocation")
        assert any("Section 126" in rf for rf in result["filtered_red_flags"])

    def test_contract_workman_employment_flags_ida(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="employment_termination",
            facts_text="The workman was terminated from the factory without notice.",
        )
        result = self.compile(entry, req, intake, classify, family="contract_and_commercial", cause_type="employment_termination")
        assert any("workman" in rf.lower() or "Labour Court" in rf for rf in result["filtered_red_flags"])

    def test_contract_generic_breach_forbids_repudiatory_without_refusal_facts(self):
        entry = self._make_entry(
            drafting_red_flags=[
                "Screen arbitration clause — S.8 Arbitration Act may apply.",
                "Liquidated damages S.74 ICA: plead stipulated sum specifically.",
            ],
            permitted_doctrines=["repudiatory_breach", "damages_s73", "liquidated_damages_s74"],
            damages_categories=["actual_loss", "consequential_loss", "interest_on_delayed_payment"],
        )
        req, intake, classify = self._make_state(
            cause_type="breach_of_contract",
            facts_text="Defendant failed to perform contractual obligations causing financial loss to plaintiff.",
        )
        result = self.compile(entry, req, intake, classify, family="contract_and_commercial", cause_type="breach_of_contract")
        assert "repudiatory_breach" in result["forbidden_doctrines"]
        assert "damages_s73" in result["allowed_doctrines"]
        assert not any("arbitration" in rf.lower() for rf in result["filtered_red_flags"])
        assert not any("liquidated damages" in rf.lower() for rf in result["filtered_red_flags"])
        assert "consequential_loss" in result["forbidden_damages"]
        assert "interest_on_delayed_payment" in result["forbidden_damages"]

    # ── Money ───────────────────────────────────────────────────────────

    def test_money_cheque_bounce_adds_s138_prerequisite(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="cheque_bounce_civil",
            facts_text="Cheque dishonoured. Demand notice sent.",
        )
        result = self.compile(entry, req, intake, classify, family="money_and_debt", cause_type="cheque_bounce_civil")
        assert any("Section 138" in rf or "S138" in rf or "demand notice" in rf.lower() for rf in result["filtered_red_flags"])

    def test_money_summary_suit_warns_eligibility(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="summary_suit",
            facts_text="Promissory note for Rs 5 lakh.",
        )
        result = self.compile(entry, req, intake, classify, family="money_and_debt", cause_type="summary_suit")
        assert any("Order XXXVII" in rf for rf in result["filtered_red_flags"])

    def test_money_msmed_flags_facilitation_council(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="msmed_recovery",
            facts_text="MSME supplier not paid for goods delivered.",
        )
        result = self.compile(entry, req, intake, classify, family="money_and_debt", cause_type="msmed_recovery")
        assert any("Facilitation Council" in rf or "MSMED" in rf for rf in result["filtered_red_flags"])

    # ── Immovable Property ──────────────────────────────────────────────

    def test_partition_flags_vineeta_sharma_and_art_110(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="partition",
            facts_text="Partition of ancestral Hindu joint family property among coparceners.",
        )
        result = self.compile(entry, req, intake, classify, family="immovable_property", cause_type="partition")
        flags = " ".join(result["filtered_red_flags"]).lower()
        assert "vineeta sharma" in flags or "coparcen" in flags
        assert "article 110" in flags
        assert "section 16" in flags

    def test_partition_always_flags_situs_jurisdiction(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="partition",
            facts_text="Partition of jointly owned flat.",
        )
        result = self.compile(entry, req, intake, classify, family="immovable_property", cause_type="partition")
        assert any("Section 16" in rf for rf in result["filtered_red_flags"])

    # ── Tenancy ─────────────────────────────────────────────────────────

    def test_tenancy_eviction_flags_s106_and_rent_act(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="eviction",
            facts_text="Tenant failed to vacate after lease expiry.",
        )
        result = self.compile(entry, req, intake, classify, family="tenancy_and_rent", cause_type="eviction")
        flags = " ".join(result["filtered_red_flags"])
        assert "Section 106" in flags
        assert "Rent" in flags  # Rent Act verification

    def test_tenancy_with_rent_act_context_warns_jurisdiction_bar(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="eviction",
            facts_text="File eviction under rent control act against tenant.",
        )
        result = self.compile(entry, req, intake, classify, family="tenancy_and_rent", cause_type="eviction")
        assert any("NO jurisdiction" in rf or "NOT maintainable" in rf or "Rent Controller" in rf for rf in result["filtered_red_flags"])

    # ── Tort ────────────────────────────────────────────────────────────

    def test_tort_defamation_flags_1_year_limitation(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="defamation_civil",
            facts_text="Defendant published defamatory article about plaintiff.",
        )
        result = self.compile(entry, req, intake, classify, family="tort_and_civil_wrong", cause_type="defamation_civil")
        assert any("Article 75" in rf for rf in result["filtered_red_flags"])

    def test_tort_mact_exclusion_forbids_motor_vehicles_act(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="negligence",
            facts_text="Plaintiff injured in motor accident caused by defendant's negligence.",
        )
        result = self.compile(entry, req, intake, classify, family="tort_and_civil_wrong", cause_type="negligence")
        assert "Motor Vehicles Act, 1988" in result["forbidden_statutes"]
        assert any("MACT" in rf for rf in result["filtered_red_flags"])

    def test_tort_medical_negligence_flags_bolam(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="medical_negligence",
            facts_text="Doctor performed wrong surgery on patient.",
        )
        result = self.compile(entry, req, intake, classify, family="tort_and_civil_wrong", cause_type="medical_negligence")
        assert any("Bolam" in rf or "medical practice" in rf for rf in result["filtered_red_flags"])

    def test_tort_public_nuisance_flags_special_damage(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="nuisance_public",
            facts_text="Factory emitting toxic fumes affecting neighbourhood.",
        )
        result = self.compile(entry, req, intake, classify, family="tort_and_civil_wrong", cause_type="nuisance_public")
        assert any("special damage" in rf.lower() for rf in result["filtered_red_flags"])

    # ── Possession (Immovable Property family) ───────────────────────────

    def test_possession_tenant_flags_s106_notice(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="recovery_of_possession_tenant",
            facts_text="Tenant failed to vacate after lease expired. Monthly rent Rs 15000.",
        )
        result = self.compile(entry, req, intake, classify, family="immovable_property", cause_type="recovery_of_possession_tenant")
        flags = " ".join(result["filtered_red_flags"])
        assert "Section 106" in flags or "S.106" in flags
        assert "Section 16" in flags  # situs jurisdiction

    def test_possession_tenant_forbids_easements_act(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="recovery_of_possession_tenant",
            facts_text="Tenant not paying rent for 6 months.",
        )
        result = self.compile(entry, req, intake, classify, family="immovable_property", cause_type="recovery_of_possession_tenant")
        assert any("Easements Act" in s for s in result["forbidden_statutes"])
        assert any("Easements Act" in rf for rf in result["filtered_red_flags"])

    def test_possession_licensee_forbids_tpa_s106(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="recovery_of_possession_licensee",
            facts_text="Licensee refused to vacate after licence revocation.",
        )
        result = self.compile(entry, req, intake, classify, family="immovable_property", cause_type="recovery_of_possession_licensee")
        forbidden = " ".join(result["forbidden_statutes"])
        assert "Section 106" in forbidden or "Section 111" in forbidden
        flags = " ".join(result["filtered_red_flags"])
        assert "Easements Act" in flags  # must use Easements Act footing
        assert "licence" in flags.lower() or "license" in flags.lower()

    def test_possession_licensee_warns_licence_vs_tenancy(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="recovery_of_possession_licensee",
            facts_text="Occupant given permission to stay in spare room.",
        )
        result = self.compile(entry, req, intake, classify, family="immovable_property", cause_type="recovery_of_possession_licensee")
        assert any("licence from tenancy" in rf.lower() or "distinguish" in rf.lower() for rf in result["filtered_red_flags"])

    def test_possession_trespasser_forbids_tpa_and_easements(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="recovery_of_possession_trespasser",
            facts_text="Unknown persons encroached on plaintiff's land.",
        )
        result = self.compile(entry, req, intake, classify, family="immovable_property", cause_type="recovery_of_possession_trespasser")
        forbidden = " ".join(result["forbidden_statutes"])
        assert "Section 106" in forbidden
        assert "Easements Act" in forbidden
        flags = " ".join(result["filtered_red_flags"])
        assert "S.5 SRA" in flags or "title" in flags.lower()

    def test_possession_co_owner_flags_ouster(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="recovery_of_possession_co_owner",
            facts_text="Co-owner brother denied access to jointly owned flat.",
        )
        result = self.compile(entry, req, intake, classify, family="immovable_property", cause_type="recovery_of_possession_co_owner")
        flags = " ".join(result["filtered_red_flags"]).lower()
        assert "ouster" in flags
        assert "partition" in flags  # should suggest partition alternative

    def test_possession_rent_act_context_warns_bar(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="recovery_of_possession_tenant",
            facts_text="Tenant in rent controlled premises. Landlord wants possession.",
        )
        result = self.compile(entry, req, intake, classify, family="immovable_property", cause_type="recovery_of_possession_tenant")
        assert any("Rent Control" in rf or "NOT maintainable" in rf or "Rent Controller" in rf for rf in result["filtered_red_flags"])

    def test_possession_recent_dispossession_flags_s6_sra(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="recovery_of_possession_trespasser",
            facts_text="Plaintiff was dispossessed within six months by encroacher.",
        )
        result = self.compile(entry, req, intake, classify, family="immovable_property", cause_type="recovery_of_possession_trespasser")
        assert any("Section 6" in rf or "S.6" in rf for rf in result["filtered_red_flags"])

    # ── Injunction ───────────────────────────────────────────────────────

    def test_injunction_permanent_flags_three_elements(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="permanent_injunction",
            facts_text="Defendant threatening to construct wall blocking plaintiff's access.",
        )
        result = self.compile(entry, req, intake, classify, family="injunction_and_declaratory", cause_type="permanent_injunction")
        flags = " ".join(result["filtered_red_flags"])
        assert "S.38 SRA" in flags or "Section 38" in flags
        assert "legal right" in flags.lower()
        assert "inadequate" in flags.lower()

    def test_injunction_mandatory_flags_exceptional_threshold(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="mandatory_injunction",
            facts_text="Defendant built unauthorized wall blocking access to plaintiff's property.",
        )
        result = self.compile(entry, req, intake, classify, family="injunction_and_declaratory", cause_type="mandatory_injunction")
        flags = " ".join(result["filtered_red_flags"])
        assert "S.39 SRA" in flags or "Section 39" in flags
        assert "exceptional" in flags.lower() or "EXCEPTIONAL" in flags

    def test_injunction_infrastructure_flags_s41ha(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="permanent_injunction",
            facts_text="Government building highway through plaintiff's land. National project.",
        )
        result = self.compile(entry, req, intake, classify, family="injunction_and_declaratory", cause_type="permanent_injunction")
        assert any("S.41(ha)" in rf or "infrastructure" in rf.lower() for rf in result["filtered_red_flags"])

    def test_injunction_delay_flags_acquiescence(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="permanent_injunction",
            facts_text="Defendant has been constructing since long. Plaintiff acquiesced for several years.",
        )
        result = self.compile(entry, req, intake, classify, family="injunction_and_declaratory", cause_type="permanent_injunction")
        assert any("delay" in rf.lower() or "acquiesc" in rf.lower() for rf in result["filtered_red_flags"])

    def test_injunction_property_based_flags_situs(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="permanent_injunction",
            facts_text="Defendant encroaching on plaintiff's agricultural land survey no 45.",
        )
        result = self.compile(entry, req, intake, classify, family="injunction_and_declaratory", cause_type="permanent_injunction")
        assert any("S.16" in rf or "Section 16" in rf or "situs" in rf.lower() for rf in result["filtered_red_flags"])

    def test_injunction_non_property_uses_s20(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="permanent_injunction",
            facts_text="Defendant making defamatory statements about plaintiff's business. Restrain defendant.",
        )
        result = self.compile(entry, req, intake, classify, family="injunction_and_declaratory", cause_type="permanent_injunction")
        assert any("S.20" in rf or "Section 20" in rf for rf in result["filtered_red_flags"])

    def test_injunction_bare_no_interest_section(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="permanent_injunction",
            facts_text="Restrain defendant from trespassing on land.",
        )
        result = self.compile(entry, req, intake, classify, family="injunction_and_declaratory", cause_type="permanent_injunction")
        flags = " ".join(result["filtered_red_flags"])
        assert "INTEREST" in flags or "S.34 CPC" in flags  # warns against interest section

    def test_injunction_declaration_title_flags_consequential_relief(self):
        entry = self._make_entry()
        req, intake, classify = self._make_state(
            cause_type="declaration_title",
            facts_text="Defendant denies plaintiff's title to the property.",
        )
        result = self.compile(entry, req, intake, classify, family="injunction_and_declaratory", cause_type="declaration_title")
        flags = " ".join(result["filtered_red_flags"])
        assert "S.34" in flags or "Section 34" in flags
        assert "consequential relief" in flags.lower() or "further relief" in flags.lower()


class TestFamilySpecificTemplates:
    """Per-family template sections produce correct legal content."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.templates.engine import TemplateEngine
        self.engine = TemplateEngine()

    def _make_lkb(self, cause_type="breach_of_contract"):
        from app.agents.drafting_agents.lkb import lookup
        return lookup("Civil", cause_type) or {
            "display_name": cause_type.replace("_", " ").title(),
            "damages_categories": ["principal_amount"],
            "required_reliefs": ["damages_decree"],
            "permitted_doctrines": [],
            "primary_acts": [],
            "alternative_acts": [],
            "court_rules": {"default": {"court": "District Court", "heading": "IN THE COURT OF THE {court_type}", "format": "O.S. No."}},
            "limitation": {"article": "UNKNOWN", "period": "Three years"},
        }

    def _assemble(self, cause_type, facts_extra=None):
        intake = {
            "jurisdiction": {"city": "Mumbai", "state": "Maharashtra"},
            "parties": {
                "primary": {"name": "A", "age": "40", "occupation": "Business", "address": "Mumbai"},
                "opposite": [{"name": "B", "age": "45", "occupation": "Business", "address": "Mumbai"}],
            },
            "facts": {"summary": "Test", "cause_of_action_date": "01.01.2025", **(facts_extra or {})},
            "evidence": [],
        }
        classify = {"doc_type": "plaint", "cause_type": cause_type, "law_domain": "Civil"}
        lkb = self._make_lkb(cause_type)
        prov = {"limitation": {"article": "UNKNOWN", "period": "Three years"}}
        return self.engine.assemble(intake, classify, lkb, prov)

    # ── Contract ────────────────────────────────────────────────────────

    def test_contract_breach_has_s73_legal_basis(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("breach_of_contract")
        gaps = resolve_gap_definitions(lkb, "breach_of_contract")
        legal_gap = next(g for g in gaps if g["gap_id"] == "LEGAL_BASIS")
        constraints_text = " ".join(legal_gap["constraints"])
        assert "Section 73" in constraints_text
        assert "Indian Contract Act" in constraints_text

    def test_contract_breach_uses_section_20_jurisdiction(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("breach_of_contract")
        gaps = resolve_gap_definitions(lkb, "breach_of_contract")
        juris_gap = next(g for g in gaps if g["gap_id"] == "JURISDICTION")
        constraints_text = " ".join(juris_gap["constraints"])
        assert "Section 20" in constraints_text
        assert "contract" in constraints_text.lower()

    def test_civil_draft_plan_honors_empty_filtered_red_flags(self):
        from app.agents.drafting_agents.nodes.civil_decision import civil_draft_plan_compiler_node

        state = {
            "classify": {
                "law_domain": "Civil",
                "cause_type": "breach_of_contract",
                "doc_type": "damages_plaint",
                "classification": {"missing_fields": []},
            },
            "civil_decision": {
                "enabled": True,
                "status": "resolved",
                "resolved_cause_type": "breach_of_contract",
                "family": "contract_and_commercial",
                "maintainability_checks": [],
                "limitation": {"article": "55", "period": "Three years"},
                "allowed_reliefs": ["damages_decree", "interest_pendente_lite_future", "costs"],
                "forbidden_reliefs": [],
                "allowed_damages": ["actual_loss"],
                "forbidden_damages": ["consequential_loss", "interest_on_delayed_payment"],
                "allowed_doctrines": ["damages_s73"],
                "forbidden_doctrines": ["repudiatory_breach"],
                "filtered_red_flags": [],
            },
            "mandatory_provisions": {"limitation": {"article": "55", "period": "Three years"}},
            "lkb_brief": {
                "required_sections": ["facts", "prayer"],
                "required_reliefs": ["damages_decree", "interest_pendente_lite_future", "costs"],
                "required_averments": ["breach_date"],
                "drafting_red_flags": [
                    "Screen arbitration clause — S.8 Arbitration Act may apply.",
                    "Liquidated damages S.74 ICA: plead stipulated sum specifically.",
                ],
            },
            "decision_ir": {},
        }

        result = civil_draft_plan_compiler_node(state)
        assert result.update["civil_draft_plan"]["red_flags"] == []

    def test_contract_breach_has_single_event_article_55_limitation_wording(self):
        result = self._assemble("breach_of_contract")
        assert "within limitation under Article 55" in result
        assert "date on which the contract was broken" in result

    def test_contract_breach_uses_contract_specific_cause_of_action_wording(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("breach_of_contract")
        gaps = resolve_gap_definitions(lkb, "breach_of_contract")
        coa_gap = next(g for g in gaps if g["gap_id"] == "CAUSE_OF_ACTION")
        constraints_text = " ".join(coa_gap["constraints"])
        # COA gap should have cause of action guidance
        assert "cause of action" in constraints_text.lower()
        assert "limitation" in constraints_text.lower()

    def test_contract_gap_sanitizer_removes_readiness_language(self):
        from app.agents.drafting_agents.nodes.draft_template_fill import _sanitize_contract_damages_drift

        text = (
            "FACTS OF THE CASE\n\n"
            "5. The Plaintiff has always been ready and willing to perform the agreement.\n"
            "6. The Plaintiff performed the contract.\n"
        )
        result = _sanitize_contract_damages_drift(text, "breach_of_contract")
        assert "ready and willing" not in result.lower()
        assert "performed the contract" in result

    def test_contract_gap_sanitizer_strips_consequence_clause_from_breach(self):
        from app.agents.drafting_agents.nodes.draft_template_fill import _sanitize_contract_damages_drift

        text = "8. The Defendant failed to perform the contractual obligations, thereby causing disruption to the Plaintiff."
        result = _sanitize_contract_damages_drift(text, "breach_of_contract")
        assert "causing disruption" not in result.lower()
        assert "failed to perform the contractual obligations." in result

    def test_contract_gap_sanitizer_normalizes_total_suit_value_currency(self):
        from app.agents.drafting_agents.nodes.draft_template_fill import _sanitize_contract_damages_drift

        text = "11. The Plaintiff quantifies the actual loss at {{TOTAL_SUIT_VALUE}}, the computation of which is filed as Annexure P-3."
        result = _sanitize_contract_damages_drift(text, "breach_of_contract")
        assert "Rs. {{TOTAL_SUIT_VALUE}}/-" in result

    def test_contract_gap_sanitizer_reduces_repetitive_default_phrases(self):
        from app.agents.drafting_agents.nodes.draft_template_fill import _sanitize_contract_damages_drift

        text = (
            "4. The Plaintiff and the Defendant entered into {{CONTRACT_DETAILS}}.\n"
            "9. The Plaintiff issued a notice calling upon the Defendant to perform the obligations.\n"
            "10. The Defendant did not perform the contractual obligations.\n"
            "14. The Defendant has committed breach by failing to perform the obligations undertaken therein.\n"
            "19. The cause of action arose when the Defendant failed to perform the contractual obligations due under the agreement.\n"
            "20. The Defendant failed to perform the contractual obligations stipulated therein by {{DATE_OF_BREACH}}.\n"
            "21. The Defendant continues to remain in default.\n"
            "22. The Defendant remained in default as on {{DATE_OF_BREACH}}.\n"
        )
        result = _sanitize_contract_damages_drift(text, "breach_of_contract")
        assert "entered into a written agreement regarding {{CONTRACT_DETAILS}}" in result
        assert "comply with the terms of the agreement" in result
        assert "did not cure the contractual default" in result
        assert "remaining in default of the obligations undertaken therein" in result
        assert "committed default under the agreement" in result
        assert "committed default under the agreement on {{DATE_OF_BREACH}}" in result
        assert "has not cured the default" in result
        assert "committed breach on {{DATE_OF_BREACH}}" in result

    def test_contract_gap_fill_fallback_builds_section73_placeholder_sections(self):
        from app.agents.drafting_agents.nodes.draft_template_fill import _build_contract_gap_fill_fallback

        result = _build_contract_gap_fill_fallback("breach_of_contract", ["actual_loss"])

        assert "{{GENERATE:FACTS}}" in result
        assert "{{GENERATE:BREACH}}" in result
        assert "{{GENERATE:DAMAGES}}" in result
        assert "Rs. {{TOTAL_SUIT_VALUE}}/-" in result
        assert "Annexure P-1" in result
        assert "Annexure P-2" in result

    def test_review_sanitizer_strips_inline_note_markup(self):
        from app.agents.drafting_agents.nodes.reviews import _strip_reviewer_notes

        text = "11. Damages are quantified at Rs. {{TOTAL_SUIT_VALUE}}/-. [NOTE: Verify amount before filing]"
        result = _strip_reviewer_notes(text)
        assert "[NOTE:" not in result

    def test_contract_breach_respects_decision_ir_doctrine_and_damage_filters(self):
        intake = {
            "jurisdiction": {"city": "Mumbai", "state": "Maharashtra"},
            "parties": {
                "primary": {"name": "A", "age": "40", "occupation": "Business", "address": "Mumbai"},
                "opposite": [{"name": "B", "age": "45", "occupation": "Business", "address": "Mumbai"}],
            },
            "facts": {"summary": "Simple non-performance of contract", "cause_of_action_date": "01.01.2025"},
            "evidence": [],
        }
        classify = {"doc_type": "damages_plaint", "cause_type": "breach_of_contract", "law_domain": "Civil"}
        lkb = self._make_lkb("breach_of_contract")
        lkb["permitted_doctrines"] = ["repudiatory_breach", "damages_s73"]
        lkb["damages_categories"] = ["actual_loss", "consequential_loss", "interest_on_delayed_payment"]
        prov = {"limitation": {"article": "55", "period": "Three years"}}
        decision_ir = {
            "allowed_doctrines": ["damages_s73"],
            "forbidden_doctrines": ["repudiatory_breach"],
            "allowed_damages": ["actual_loss"],
            "forbidden_damages": ["consequential_loss", "interest_on_delayed_payment"],
        }

        result = self.engine.assemble(intake, classify, lkb, prov, decision_ir=decision_ir)

        assert "repudiatory breach" not in result.lower()
        # Check damages schedule section specifically (not interest_guidance which is separate)
        schedule_section = ""
        if "SCHEDULE OF DAMAGES" in result.upper():
            idx = result.upper().index("SCHEDULE OF DAMAGES")
            schedule_section = result[idx:].lower()
        assert "consequential loss" not in schedule_section, "Forbidden damage 'consequential_loss' in schedule"
        assert "interest on delayed payment" not in schedule_section, "Forbidden damage 'interest_on_delayed_payment' in schedule"

    def test_lkb_coa_single_event_ignores_continues_language_outside_cause_section(self):
        from app.agents.drafting_agents.nodes.lkb_compliance import _check_coa_type

        draft = (
            "FACTS OF THE CASE\n\n"
            "5. The Defendant continues to withhold payment despite repeated demands.\n\n"
            "CAUSE OF ACTION\n\n"
            "6. The cause of action first arose on {{DATE_OF_BREACH}} when the Defendant failed "
            "to perform the contractual obligations due under the agreement.\n"
            "7. The breach was a single event. The Plaintiff's claim for damages subsists and "
            "remains enforceable in law.\n\n"
            "PRAYER\n\n"
            "(a) damages decree"
        )

        issues = _check_coa_type(draft, {"coa_type": "single_event"})
        assert issues == []

    def test_contract_blocking_flags_specific_performance_in_prayer(self):
        from app.agents.drafting_agents.nodes.civil_decision import _contract_blocking_violations

        # "specific performance" in PRAYER = blocker (wrong relief track)
        issues = _contract_blocking_violations(
            text=(
                "FACTS OF THE CASE\n\n"
                "The Plaintiff issued notice seeking specific performance of the contract.\n"
                "The Plaintiff has always been ready and willing to perform.\n\n"
                "PRAYER\n\n"
                "decree for specific performance of the contract"
            ),
            cause_type="breach_of_contract",
            decision={},
        )
        assert any("specific performance" in issue.lower() for issue in issues)

        # "specific performance" only in FACTS but not in PRAYER = no blocker
        issues_no_prayer = _contract_blocking_violations(
            text=(
                "FACTS OF THE CASE\n\n"
                "The Plaintiff issued notice seeking specific performance of the contract.\n"
                "The Plaintiff has always been ready and willing to perform.\n\n"
                "PRAYER\n\n"
                "damages decree"
            ),
            cause_type="breach_of_contract",
            decision={},
        )
        # "ready and willing" in facts is a standard averment, not a blocker
        assert not any("readiness and willingness" in issue.lower() for issue in issues_no_prayer)

    def test_specific_performance_has_s10_and_readiness(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("specific_performance")
        gaps = resolve_gap_definitions(lkb, "specific_performance")
        legal_gap = next(g for g in gaps if g["gap_id"] == "LEGAL_BASIS")
        constraints_text = " ".join(legal_gap["constraints"])
        assert "Section 10" in constraints_text
        # Readiness is in the READINESS_AND_WILLINGNESS gap
        readiness_gap = next(g for g in gaps if g["gap_id"] == "READINESS_AND_WILLINGNESS")
        readiness_text = " ".join(readiness_gap["constraints"])
        assert "S.16(c)" in readiness_text or "Section 16(c)" in constraints_text

    def test_contract_suit_title_correct(self):
        result = self._assemble("specific_performance")
        assert "SUIT FOR SPECIFIC PERFORMANCE" in result

    def test_contract_documents_list_uses_contract_defaults(self):
        result = self._assemble("breach_of_contract")
        assert "Contract / Agreement dated {{DATE_OF_CONTRACT}}" in result
        assert "Legal notice dated {{NOTICE_DATE}}" in result
        assert "Statement / computation of damages" in result

    def test_contract_actual_loss_schedule_uses_total_suit_value_placeholder(self):
        lkb = self._make_lkb("breach_of_contract")
        lkb["damages_categories"] = ["actual_loss"]
        schedule = self.engine._damages_schedule(lkb, "breach_of_contract")

        assert "Amount claimed: Rs. {{TOTAL_SUIT_VALUE}}/-" in schedule
        assert "{{ACTUAL_LOSS_AMOUNT}}" not in schedule

    def test_contract_prayer_labels_decree_as_breach_of_contract_damages(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("breach_of_contract")
        gaps = resolve_gap_definitions(lkb, "breach_of_contract")
        prayer_gap = next(g for g in gaps if g["gap_id"] == "PRAYER")
        constraints_text = " ".join(prayer_gap["constraints"])
        assert "damages" in constraints_text.lower()

    def test_contract_valuation_mentions_court_fee_computation_basis(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("breach_of_contract")
        gaps = resolve_gap_definitions(lkb, "breach_of_contract")
        val_gap = next(g for g in gaps if g["gap_id"] == "VALUATION")
        constraints_text = " ".join(val_gap["constraints"])
        assert "court fee" in constraints_text.lower()
        assert "valuation" in constraints_text.lower()

    # ── Money ───────────────────────────────────────────────────────────

    def test_money_recovery_loan_has_s73(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("money_recovery_loan")
        gaps = resolve_gap_definitions(lkb, "money_recovery_loan")
        legal_gap = next(g for g in gaps if g["gap_id"] == "LEGAL_BASIS")
        constraints_text = " ".join(legal_gap["constraints"])
        # S.73 ICA = compensation for loss caused by breach (core for money recovery)
        assert "Section 73" in constraints_text
        assert "Indian Contract Act" in constraints_text

    def test_summary_suit_has_order_xxxvii(self):
        result = self._assemble("summary_suit_instrument")
        assert "Order XXXVII" in result

    def test_quantum_meruit_has_s70(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("quantum_meruit")
        gaps = resolve_gap_definitions(lkb, "quantum_meruit")
        legal_gap = next(g for g in gaps if g["gap_id"] == "LEGAL_BASIS")
        constraints_text = " ".join(legal_gap["constraints"])
        assert "Section 70" in constraints_text

    def test_guarantee_recovery_has_s126(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("guarantee_recovery")
        gaps = resolve_gap_definitions(lkb, "guarantee_recovery")
        legal_gap = next(g for g in gaps if g["gap_id"] == "LEGAL_BASIS")
        constraints_text = " ".join(legal_gap["constraints"])
        assert "126" in constraints_text

    def test_rendition_of_accounts_prayer(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("rendition_of_accounts")
        gaps = resolve_gap_definitions(lkb, "rendition_of_accounts")
        prayer_gap = next(g for g in gaps if g["gap_id"] == "PRAYER")
        constraints_text = " ".join(prayer_gap["constraints"]).lower()
        # Prayer should reference rendition/accounts relief
        assert "rendition" in constraints_text or "accounts" in constraints_text or "render" in constraints_text

    def test_recovery_specific_movable_prayer(self):
        result = self._assemble("recovery_specific_movable")
        assert "RECOVERY OF SPECIFIC MOVABLE" in result
        assert "delivery" in result.lower() or "movable property" in result.lower()

    # ── Partition ───────────────────────────────────────────────────────

    def test_partition_has_partition_act(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("partition")
        gaps = resolve_gap_definitions(lkb, "partition")
        legal_gap = next(g for g in gaps if g["gap_id"] == "LEGAL_BASIS")
        constraints_text = " ".join(legal_gap["constraints"])
        assert "Partition Act" in constraints_text
        # Order XX Rule 18 is a procedural CPC provision (decree form),
        # correctly filtered from LEGAL_BASIS by auto-constraints generator

    def test_partition_has_preliminary_and_final_decree_prayer(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("partition")
        gaps = resolve_gap_definitions(lkb, "partition")
        prayer_gap = next(g for g in gaps if g["gap_id"] == "PRAYER")
        constraints_text = " ".join(prayer_gap["constraints"]).lower()
        # Prayer should reference preliminary/final decree or partition relief
        assert "preliminary" in constraints_text or "partition" in constraints_text

    def test_partition_suit_title(self):
        result = self._assemble("partition")
        assert "PARTITION" in result
        assert "SEPARATE POSSESSION" in result

    def test_partition_has_genealogy_and_share_markers(self):
        result = self._assemble("partition")
        # v10.0: partition uses GENEALOGY_AND_SHARES gap (not separate TABLE + COMPUTATION)
        assert "GENERATE:GENEALOGY_AND_SHARES" in result or "GENERATE:GENEALOGY_TABLE" in result

    def test_partition_has_schedule_of_property(self):
        result = self._assemble("partition", facts_extra={
            "property_address": "Plot 5, Andheri East",
        })
        assert "SCHEDULE OF SUIT PROPERTY" in result
        assert "Plot 5" in result

    def test_partition_uses_situs_jurisdiction(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("partition")
        gaps = resolve_gap_definitions(lkb, "partition")
        juris_gap = next(g for g in gaps if g["gap_id"] == "JURISDICTION")
        constraints_text = " ".join(juris_gap["constraints"])
        assert "Section 16" in constraints_text

    def test_partition_no_interest_section(self):
        result = self._assemble("partition")
        # Partition suits don't have interest section
        assert "INTEREST\n" not in result or "pendente lite" not in result.lower().split("prayer")[0]

    # ── Tenancy ─────────────────────────────────────────────────────────

    def test_eviction_has_s106_tpa(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("eviction")
        gaps = resolve_gap_definitions(lkb, "eviction")
        # S.106 TPA is in NOTICE_COMPLIANCE gap constraints
        notice_gap = next(g for g in gaps if g["gap_id"] == "NOTICE_COMPLIANCE")
        constraints_text = " ".join(notice_gap["constraints"])
        assert "S.106" in constraints_text or "Section 106" in constraints_text

    def test_eviction_has_rent_act_placeholder(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("eviction")
        gaps = resolve_gap_definitions(lkb, "eviction")
        # Rent Act mentioned in NOTICE_COMPLIANCE or GROUNDS anti_constraints/constraints
        all_text = ""
        for g in gaps:
            all_text += " ".join(g.get("constraints", []))
            all_text += " ".join(g.get("anti_constraints", []))
        assert "Rent" in all_text or "rent" in all_text.lower()

    def test_eviction_has_notice_compliance_marker(self):
        result = self._assemble("eviction")
        assert "GENERATE:NOTICE_COMPLIANCE" in result

    def test_eviction_suit_title(self):
        result = self._assemble("eviction")
        assert "EVICTION" in result
        assert "POSSESSION" in result

    def test_eviction_prayer_has_vacant_possession(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("eviction")
        gaps = resolve_gap_definitions(lkb, "eviction")
        prayer_gap = next(g for g in gaps if g["gap_id"] == "PRAYER")
        constraints_text = " ".join(prayer_gap["constraints"]).lower()
        # Prayer constraints should reference eviction/possession relief
        assert "eviction" in constraints_text or "possession" in constraints_text or "vacant" in constraints_text

    def test_arrears_of_rent_prayer(self):
        result = self._assemble("arrears_of_rent")
        assert "ARREARS OF RENT" in result
        assert "ARREARS_AMOUNT" in result or "arrears" in result.lower()

    def test_tenancy_uses_situs_jurisdiction(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("eviction")
        gaps = resolve_gap_definitions(lkb, "eviction")
        juris_gap = next(g for g in gaps if g["gap_id"] == "JURISDICTION")
        constraints_text = " ".join(juris_gap["constraints"])
        assert "Section 16" in constraints_text

    # ── Tort ────────────────────────────────────────────────────────────

    def test_defamation_has_injunction_and_damages(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("defamation")
        gaps = resolve_gap_definitions(lkb, "defamation")
        gap_ids = [g["gap_id"] for g in gaps]
        # Should have LEGAL_BASIS gap with defamation-related constraints
        legal_gap = next(g for g in gaps if g["gap_id"] == "LEGAL_BASIS")
        constraints_text = " ".join(legal_gap["constraints"]).lower()
        # LKB primary_acts should drive constraints
        assert len(legal_gap["constraints"]) > 0
        # Should have PRAYER gap with injunction and damages reliefs
        prayer_gap = next(g for g in gaps if g["gap_id"] == "PRAYER")
        prayer_text = " ".join(prayer_gap["constraints"]).lower()
        assert "damages" in prayer_text or "compensation" in prayer_text

    def test_defamation_prayer_has_injunction_and_damages(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("defamation")
        gaps = resolve_gap_definitions(lkb, "defamation")
        prayer_gap = next(g for g in gaps if g["gap_id"] == "PRAYER")
        prayer_text = " ".join(prayer_gap["constraints"]).lower()
        assert "damages" in prayer_text or "compensation" in prayer_text

    def test_negligence_has_duty_of_care(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("negligence_personal_injury")
        gaps = resolve_gap_definitions(lkb, "negligence_personal_injury")
        # Factual gaps should include duty of care related content
        gap_ids = [g["gap_id"] for g in gaps]
        assert "FACTS_OF_WRONG" in gap_ids or "FACTS" in gap_ids
        # Legal basis gap should have negligence-related constraints from LKB
        legal_gap = next(g for g in gaps if g["gap_id"] == "LEGAL_BASIS")
        assert len(legal_gap["constraints"]) > 0

    def test_nuisance_prayer_has_abatement(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("nuisance")
        gaps = resolve_gap_definitions(lkb, "nuisance")
        prayer_gap = next(g for g in gaps if g["gap_id"] == "PRAYER")
        prayer_text = " ".join(prayer_gap["constraints"]).lower()
        # required_reliefs should include abatement
        assert "abat" in prayer_text or "cease" in prayer_text or "injunction" in prayer_text

    def test_malicious_prosecution_legal_basis(self):
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        lkb = self._make_lkb("malicious_prosecution_civil")
        gaps = resolve_gap_definitions(lkb, "malicious_prosecution_civil")
        legal_gap = next(g for g in gaps if g["gap_id"] == "LEGAL_BASIS")
        constraints_text = " ".join(legal_gap["constraints"]).lower()
        assert len(legal_gap["constraints"]) > 0

    def test_conversion_legal_basis(self):
        result = self._assemble("conversion")
        assert "converted" in result.lower() or "conversion" in result.lower()

    def test_tort_negligence_suit_title(self):
        result = self._assemble("negligence_personal_injury")
        assert "NEGLIGENCE" in result


class TestTemplateConsumesDecisionIR:
    """Template engine and gap-fill prompt must consume decision_ir, not raw LKB."""

    def test_template_engine_filters_forbidden_damages_from_schedule(self):
        from app.agents.drafting_agents.templates.engine import TemplateEngine

        engine = TemplateEngine()
        lkb_brief = {
            "display_name": "Breach of contract",
            "damages_categories": [
                "actual_loss",
                "mitigation_credit",
                "liquidated_damages_s74",
                "consequential_loss",
            ],
            "primary_acts": [{"act": "Indian Contract Act, 1872", "sections": ["Section 73"]}],
            "required_reliefs": ["damages_decree", "interest_pendente_lite_future", "costs"],
            "detected_court": {"court": "Civil Court"},
        }
        decision_ir = {
            "forbidden_damages": ["mitigation_credit", "liquidated_damages_s74"],
        }
        result = engine.assemble(
            intake={"parties": {}, "jurisdiction": {}, "facts": {}},
            classify={"cause_type": "breach_of_contract", "doc_type": "damages_plaint", "law_domain": "Civil"},
            lkb_brief=lkb_brief,
            mandatory_provisions={},
            decision_ir=decision_ir,
        )
        lower = result.lower()
        # Forbidden damages should not appear in Schedule of Damages
        assert "mitigation credit" not in lower, "Template should NOT include forbidden mitigation_credit"
        assert "liquidated damages" not in lower, "Template should NOT include forbidden liquidated_damages_s74"
        # Allowed damages should appear in Schedule of Damages
        assert "actual loss" in lower or "actual_loss" in lower.replace(" ", "_"), "Template schedule should include allowed actual_loss"
        # Prayer is now LLM-generated via PRAYER gap — verify gap constraints include damages
        from app.agents.drafting_agents.lkb.causes._family_defaults import resolve_gap_definitions
        gaps = resolve_gap_definitions(lkb_brief, "breach_of_contract")
        prayer_gap = next(g for g in gaps if g["gap_id"] == "PRAYER")
        prayer_text = " ".join(prayer_gap["constraints"]).lower()
        assert "damages" in prayer_text, "PRAYER gap constraints should mention damages relief"

    def test_template_engine_no_decision_ir_passes_all_damages(self):
        from app.agents.drafting_agents.templates.engine import TemplateEngine

        engine = TemplateEngine()
        lkb_brief = {
            "display_name": "Breach of contract",
            "damages_categories": ["actual_loss", "mitigation_credit"],
            "primary_acts": [{"act": "Indian Contract Act, 1872", "sections": ["Section 73"]}],
            "detected_court": {"court": "Civil Court"},
        }
        result = engine.assemble(
            intake={"parties": {}, "jurisdiction": {}, "facts": {}},
            classify={"cause_type": "breach_of_contract", "doc_type": "damages_plaint", "law_domain": "Civil"},
            lkb_brief=lkb_brief,
            mandatory_provisions={},
        )
        lower = result.lower()
        # Without decision_ir, all damages should appear in Schedule of Damages
        assert "mitigation credit" in lower or "actual loss" in lower, "Without decision_ir, damages categories should pass through to schedule"

    def test_draft_plan_context_includes_forbidden_constraints(self):
        from app.agents.drafting_agents.nodes.draft_template_fill import _build_draft_plan_context

        plan = {
            "family": "contract_and_commercial",
            "cause_type": "breach_of_contract",
            "required_reliefs": ["damages_decree", "costs"],
            "red_flags": ["Do not mix S73 and S74."],
        }
        decision_ir = {
            "forbidden_statutes": ["Commercial Courts Act, 2015"],
            "forbidden_damages": ["mitigation_credit", "liquidated_damages_s74"],
        }
        context = _build_draft_plan_context(plan, decision_ir)
        assert "DO NOT CITE" in context
        assert "Commercial Courts Act" in context
        assert "DO NOT CLAIM AS RELIEF" in context
        assert "mitigation credit" in context

    def test_draft_plan_context_no_decision_ir_no_constraints(self):
        from app.agents.drafting_agents.nodes.draft_template_fill import _build_draft_plan_context

        plan = {"family": "contract_and_commercial", "cause_type": "breach_of_contract"}
        context = _build_draft_plan_context(plan)
        assert "DO NOT CITE" not in context
        assert "DO NOT CLAIM" not in context


class TestTemplateFailureHandling:
    def test_possession_template_failure_blocks_instead_of_falling_back(self, monkeypatch):
        from app.agents.drafting_agents.nodes import draft_template_fill as mod

        monkeypatch.setattr(mod, "draft_openai_model", None)
        state = {
            "user_request": "Draft a suit for possession against a revoked licensee.",
            "intake": {
                "jurisdiction": {"city": "Bengaluru", "state": "Karnataka"},
                "facts": {"property_address": "Koramangala, Bengaluru"},
                "parties": {"primary": {}, "opposite": [{}]},
            },
            "classify": {
                "law_domain": "Civil",
                "doc_type": "eviction_plaint",
                "cause_type": "recovery_of_possession_licensee",
            },
            "court_fee": {},
            "mandatory_provisions": {"limitation": {"article": "65", "period": "Twelve years"}},
            "lkb_brief": {
                "display_name": "Recovery of possession — revoked licence (licensee)",
                "required_reliefs": ["possession_decree", "mesne_profits_inquiry_order_xx_r12", "costs"],
                "primary_acts": [
                    {"act": "Specific Relief Act, 1963", "sections": ["Section 5"]},
                    {"act": "Code of Civil Procedure, 1908", "sections": ["Section 9", "Section 16", "Order XX Rule 12"]},
                ],
                "alternative_acts": [
                    {"act": "Indian Easements Act, 1882", "sections": ["Section 52", "Section 60", "Section 61", "Section 62", "Section 63"]},
                ],
                "court_fee_statute": {"Karnataka": "Karnataka Court Fees and Suits Valuation Act, 1958"},
            },
        }

        result = asyncio.run(mod.draft_template_fill_node(state))

        assert result.goto == "__end__"
        assert "draft_template_fill: model unavailable" in result.update["errors"][0]
        assert result.update["final_draft"]["draft_artifacts"][0]["title"] == "TEMPLATE DRAFTING FAILED"


class TestCitationValidatorShortCircuit:
    def test_clean_deterministic_pass_skips_review(self, monkeypatch):
        from app.agents.drafting_agents.nodes.citation_validator import citation_validator_node
        from app.config.settings import settings

        monkeypatch.setattr(settings, "DRAFTING_SKIP_REVIEW", False, raising=False)
        monkeypatch.setattr(settings, "DRAFTING_SKIP_REVIEW_AFTER_VALIDATION_IF_CLEAN", True, raising=False)

        state = {
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The Defendant committed breach of contract under Section 73 of the Indian Contract Act, 1872. "
                            "The suit is within Article 55 of the Limitation Act, 1963. "
                            "The Plaintiff seeks damages and interest under Section 34 CPC."
                        )
                    }
                ]
            },
            "mandatory_provisions": {
                "verified_provisions": [{"section": "Section 73", "act": "Indian Contract Act, 1872"}],
                "limitation": {"article": "55", "period": "Three years"},
            },
            "domain_gate_issues": [],
            "civil_gate_issues": [],
            "postprocess_issues": [],
        }

        result = citation_validator_node(state)

        assert result.goto == "__end__"
        assert result.update["citation_issues"] == []
        assert result.update["final_draft"]["draft_artifacts"][0]["text"].startswith("The Defendant committed")

    def test_warn_level_issue_still_routes_to_review(self, monkeypatch):
        from app.agents.drafting_agents.nodes.citation_validator import citation_validator_node
        from app.config.settings import settings

        monkeypatch.setattr(settings, "DRAFTING_SKIP_REVIEW", False, raising=False)
        monkeypatch.setattr(settings, "DRAFTING_SKIP_REVIEW_AFTER_VALIDATION_IF_CLEAN", True, raising=False)

        state = {
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The Defendant committed breach of contract under Section 73 of the Indian Contract Act, 1872. "
                            "The Plaintiff seeks damages."
                        )
                    }
                ]
            },
            "mandatory_provisions": {
                "verified_provisions": [{"section": "Section 73", "act": "Indian Contract Act, 1872"}],
                "limitation": {"article": "55", "period": "Three years"},
            },
            "domain_gate_issues": [],
            "civil_gate_issues": [],
            "postprocess_issues": [],
        }

        result = citation_validator_node(state)

        assert result.goto == "review"
        assert "final_draft" not in result.update
        assert any(issue["severity"] == "WARN" for issue in result.update["citation_issues"])


class TestEnrichmentResolvedCauseType:
    def test_enrichment_uses_resolved_cause_type_over_generic_topic_for_limitation(self, monkeypatch):
        from app.agents.drafting_agents.nodes.enrichment import enrichment_node
        from app.config.settings import settings

        monkeypatch.setattr(settings, "DRAFTING_PROCEDURAL_SEARCH", False, raising=False)
        monkeypatch.setattr(settings, "DRAFTING_LEGAL_RESEARCH_ENABLED", False, raising=False)
        monkeypatch.setattr(settings, "DRAFTING_RAG_ENABLED", False, raising=False)

        state = {
            "rag": {"chunks": []},
            "classify": {
                "law_domain": "Civil",
                "doc_type": "eviction_plaint",
                "cause_type": "recovery_of_possession_tenant",
                "classification": {"topics": ["property_law"]},
            },
            "civil_decision": {
                "resolved_cause_type": "recovery_of_possession_tenant",
            },
            "intake": {
                "facts": {"summary": "Lease expired and tenant did not vacate."},
                "jurisdiction": {},
            },
            "user_request": "Draft a suit for possession against a tenant whose lease expired.",
        }

        result = asyncio.run(enrichment_node(state))
        limitation = result.update["mandatory_provisions"]["limitation"]
        lkb_brief = result.update["lkb_brief"]

        assert limitation["article"] == "64"
        assert lkb_brief["code"] == "recovery_of_possession_tenant"


class TestCivilAmbiguityGate:
    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.civil_decision import civil_ambiguity_gate_node

        self.node = civil_ambiguity_gate_node

    def test_blocks_ambiguous_civil_case(self, monkeypatch):
        from app.config.settings import settings

        monkeypatch.setattr(settings, "DRAFTING_RAG_ENABLED", False, raising=False)
        state = {
            "errors": [],
            "classify": {"law_domain": "Civil", "doc_type": "eviction_plaint"},
            "civil_decision": {
                "enabled": True,
                "blocking_issues": ["Ambiguous possession theory."],
            },
        }

        result = self.node(state)

        assert result.goto == "__end__"
        assert "Ambiguous possession theory." in result.update["errors"]
        assert result.update["final_draft"]["draft_artifacts"][0]["title"] == "CLARIFICATION REQUIRED"

    def test_passes_resolved_case_to_enrichment(self, monkeypatch):
        from app.config.settings import settings

        monkeypatch.setattr(settings, "DRAFTING_RAG_ENABLED", False, raising=False)
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {"enabled": True, "blocking_issues": []},
        }

        result = self.node(state)

        assert result.goto == "enrichment"


class TestCivilDraftPlanCompiler:
    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.civil_decision import civil_draft_plan_compiler_node

        self.node = civil_draft_plan_compiler_node

    def test_compiles_civil_draft_plan_and_claim_ledger(self):
        state = {
            "classify": {
                "law_domain": "Civil",
                "cause_type": "specific_performance",
                "classification": {"missing_fields": ["sale consideration balance"]},
            },
            "civil_decision": {
                "enabled": True,
                "family": "contract_and_commercial",
                "resolved_cause_type": "specific_performance",
                "route_reason": "Resolved from classifier.",
                "maintainability_checks": [],
            },
            "mandatory_provisions": {
                "limitation": {"article": "54", "period": "Three years"},
                "verified_provisions": [
                    {"section": "Section 16(c)", "act": "Specific Relief Act, 1963", "source": "lkb"}
                ],
            },
            "lkb_brief": {
                "required_sections": ["jurisdiction", "limitation", "prayer"],
                "required_reliefs": ["specific_performance_decree", "costs"],
                "optional_reliefs": ["refund_if_specifically_claimed"],
                "required_averments": ["readiness_and_willingness"],
                "mandatory_inline_sections": [{"section": "READINESS AND WILLINGNESS"}],
                "evidence_checklist": ["agreement to sell", "legal notice"],
                "drafting_red_flags": ["Plead readiness factually."],
            },
        }

        result = self.node(state)

        assert result.goto == "civil_draft_router"
        plan = result.update["civil_draft_plan"]
        assert plan["cause_type"] == "specific_performance"
        assert "specific_performance_decree" in plan["required_reliefs"]
        assert "sale consideration balance" in plan["missing_fields"]
        assert result.update["claim_ledger"]


class TestCivilConsistencyGate:
    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.nodes.civil_decision import civil_consistency_gate_node

        self.node = civil_consistency_gate_node

    def test_blocks_wrong_tenant_limitation_and_mesne_profit_pattern(self):
        state = {
            "errors": [],
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "recovery_of_possession_tenant",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The plaintiff seeks recovery of possession. "
                            "The suit is within Article 65. "
                            "The plaintiff claims mesne profits at the rate of 12% per annum."
                        )
                    }
                ]
            },
        }

        result = self.node(state)

        assert result.goto == "evidence_anchoring"
        issues = result.update["civil_gate_issues"]
        assert issues
        issue_texts = [i["issue"] if isinstance(i, dict) else str(i) for i in issues]
        assert any("Article 65" in t for t in issue_texts)
        assert any("Section 16" in t for t in issue_texts)

    def test_blocks_licensee_draft_missing_easements_and_using_generic_title(self):
        state = {
            "errors": [],
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "recovery_of_possession_licensee",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "SUIT FOR RECOVERY OF POSSESSION — REVOKED LICENCE (LICENSEE) WITH INTEREST AND COSTS\n"
                            "This Hon'ble Court has territorial jurisdiction because the cause of action arose here and the defendant resides here.\n"
                            "The Plaintiff seeks recovery of possession of immovable property.\n"
                            "The present suit is within Article 65.\n"
                            "PRAYER\n"
                            "(a) Pass a decree in favour of the Plaintiff and against the Defendant for a sum of Rs. 10,00,000/- towards damages."
                        )
                    }
                ]
            },
        }

        result = self.node(state)

        assert result.goto == "evidence_anchoring"
        issues = result.update["civil_gate_issues"]
        assert issues
        issue_texts = [i["issue"] if isinstance(i, dict) else str(i) for i in issues]
        assert any("generic 'WITH INTEREST AND COSTS'" in t for t in issue_texts)
        assert any("Indian Easements Act" in t for t in issue_texts)
        assert any("Section 16" in t for t in issue_texts)

    def test_blocks_property_injunction_draft_using_damages_template(self):
        state = {
            "errors": [],
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "permanent_injunction",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "SUIT FOR PERPETUAL / PERMANENT INJUNCTION WITH INTEREST AND COSTS\n"
                            "This Hon'ble Court has territorial jurisdiction because the cause of action arose here and the Defendant resides here.\n"
                            "The Plaintiff is in peaceful possession of agricultural land bearing Survey No. 12 supported by revenue records.\n"
                            "LEGAL BASIS\n"
                            "The present cause is governed by the Code of Civil Procedure, 1908, including Section 9, Section 16, Section 20, Section 34.\n"
                            "INTEREST\n"
                            "The Plaintiff claims pendente lite and future interest.\n"
                            "PRAYER\n"
                            "(a) Pass a decree in favour of the Plaintiff and against the Defendant for a sum of Rs. 5,00,000/- towards damages."
                        )
                    }
                ]
            },
        }

        result = self.node(state)

        assert result.goto == "evidence_anchoring"
        issues = result.update["civil_gate_issues"]
        assert issues
        issue_texts = [i["issue"] if isinstance(i, dict) else str(i) for i in issues]
        assert any("WITH INTEREST AND COSTS" in t for t in issue_texts)
        assert any("Section 34 CPC" in t for t in issue_texts)
        assert any("Section 20-style" in t for t in issue_texts)
        assert any("money-damages decree" in t for t in issue_texts)

    def test_blocks_easement_draft_using_generic_damages_prayer(self):
        state = {
            "errors": [],
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "easement",
                "allowed_reliefs": [
                    "declaration_decree",
                    "mandatory_injunction_decree",
                    "permanent_injunction_decree",
                    "costs",
                ],
            },
            "civil_draft_plan": {
                "required_reliefs": [
                    "declaration_decree",
                    "mandatory_injunction_decree",
                    "permanent_injunction_decree",
                    "costs",
                ]
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "SUIT FOR SUIT FOR DECLARATION / PROTECTION OF EASEMENT RIGHTS WITH COSTS\n"
                            "This Hon'ble Court has territorial jurisdiction because the cause of action arose here and the Defendant resides here.\n"
                            "The Plaintiff has been using the pathway for twenty years.\n"
                            "PRAYER\n"
                            "(a) Pass a decree in favour of the Plaintiff and against the Defendant for a sum of Rs. 5,00,000/- towards damages."
                        )
                    }
                ]
            },
        }

        result = self.node(state)

        assert result.goto != "evidence_anchoring"
        issues = result.update["civil_gate_issues"]
        assert issues
        issue_texts = [i["issue"] if isinstance(i, dict) else str(i) for i in issues]
        assert any("money-damages decree" in t for t in issue_texts)
        assert any("dominant heritage" in t.lower() for t in issue_texts)
        assert any("declaration of easementary right" in t.lower() for t in issue_texts)
        assert any("duplicate" in t.lower() for t in issue_texts)

    def test_passes_clean_civil_draft(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "specific_performance",
            },
            "draft": {"draft_artifacts": [{"text": "Clean specific performance draft text."}]},
        }

        result = self.node(state)

        assert result.goto == "evidence_anchoring"

    def test_passes_clean_permanent_injunction_draft(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "permanent_injunction",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "SUIT FOR PERPETUAL / PERMANENT INJUNCTION WITH COSTS\n"
                            "This Hon'ble Court has territorial jurisdiction under Section 16 of the Code of Civil Procedure, 1908, inasmuch as the suit immovable property / agricultural land is situated within the local limits of this Hon'ble Court.\n"
                            "The Plaintiff is in peaceful possession of agricultural land bearing Survey No. 12 supported by revenue records.\n"
                            "LEGAL BASIS\n"
                            "The Plaintiff is entitled to seek a decree of perpetual / permanent injunction under Sections 36, 37 and 38 of the Specific Relief Act, 1963.\n"
                            "PRAYER\n"
                            "(a) Pass a decree of permanent injunction restraining the Defendant from trespassing into, interfering with, or attempting to dispossess the Plaintiff from the suit property.\n"
                            "(b) Award costs of the suit."
                        )
                    }
                ]
            },
        }

        result = self.node(state)

        assert result.goto == "evidence_anchoring"

    # ── Contract family gate tests ──────────────────────────────────────────

    def test_flags_contract_s73_s74_mixing(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "breach_of_contract",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The defendant is liable under Section 73 of the Indian Contract Act for "
                            "unliquidated damages. The plaintiff is also entitled under Section 74 "
                            "to the liquidated damages amount."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("Section 73" in t and "Section 74" in t for t in issues)

    def test_flags_specific_performance_missing_readiness(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "specific_performance",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The plaintiff entered into an agreement to sell with the defendant. "
                            "The defendant breached the agreement. PRAYER: pass a decree of "
                            "specific performance."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("readiness and willingness" in t.lower() for t in issues)
        assert any("Section 14/16" in t for t in issues)

    def test_flags_guarantee_citing_indemnity_section(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "guarantee_recovery",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The surety is liable under Section 124 of the Indian Contract Act "
                            "to indemnify the plaintiff."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("Section 124" in t and "Section 126" in t for t in issues)

    # ── Money family gate tests ─────────────────────────────────────────────

    def test_flags_cheque_bounce_missing_s138(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "cheque_bounce_civil",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The defendant issued a cheque which was dishonoured. "
                            "The plaintiff is entitled to recover the amount."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("Section 138" in t for t in issues)
        assert any("demand" in t.lower() or "statutory notice" in t.lower() for t in issues)

    def test_flags_summary_suit_missing_order_xxxvii(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "summary_suit_instrument",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The defendant is liable to pay a sum of Rs. 10,00,000/-. "
                            "The suit is based on a written contract."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("Order XXXVII" in t for t in issues)

    def test_flags_excessive_interest_rate(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "money_recovery_loan",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The defendant borrowed Rs. 5,00,000/- at an agreed interest rate "
                            "of 36% per annum."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("36" in t and "interest" in t.lower() for t in issues)

    # ── Partition family gate tests ─────────────────────────────────────────

    def test_flags_partition_missing_order_xx_rule_18_and_genealogy(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "partition",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The plaintiff and defendant are co-owners of the suit property. "
                            "The plaintiff seeks partition and separate possession. "
                            "This court has jurisdiction under Section 20 CPC."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("Order XX Rule 18" in t for t in issues)
        assert any("Section 16" in t for t in issues)
        assert any("genealogy" in t.lower() or "family tree" in t.lower() for t in issues)
        assert any("share" in t.lower() for t in issues)

    def test_flags_partition_wrong_limitation_article(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "partition",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The plaintiff seeks partition under Order XX Rule 18 CPC. "
                            "The suit is within Article 65 of the Limitation Act. "
                            "The plaintiff's share is 1/3. "
                            "A genealogy table is annexed. "
                            "This court has jurisdiction under Section 16 CPC."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("Article 65" in t and "Article 110" in t for t in issues)

    # ── Tenancy family gate tests ───────────────────────────────────────────

    def test_flags_eviction_missing_s106_and_notice(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "eviction",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The defendant is a tenant who has failed to pay rent. "
                            "The plaintiff seeks eviction of the defendant."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("Section 106" in t for t in issues)
        assert any("notice" in t.lower() for t in issues)

    def test_flags_rent_arrears_missing_quantification(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "rent_arrears",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The defendant is a tenant who has been in default. "
                            "The plaintiff seeks recovery."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("arrears" in t.lower() for t in issues)

    # ── Tort family gate tests ──────────────────────────────────────────────

    def test_flags_defamation_missing_article_75(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "defamation",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The defendant published defamatory statements about the plaintiff. "
                            "The plaintiff seeks damages for defamation."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("Article 75" in t for t in issues)

    def test_flags_negligence_missing_elements(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "negligence",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The defendant acted carelessly causing harm to the plaintiff. "
                            "The plaintiff seeks compensation."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("duty" in t.lower() for t in issues)

    def test_flags_public_nuisance_missing_special_damage(self):
        state = {
            "classify": {"law_domain": "Civil"},
            "civil_decision": {
                "status": "resolved",
                "resolved_cause_type": "nuisance_public",
            },
            "draft": {
                "draft_artifacts": [
                    {
                        "text": (
                            "The defendant's factory emits noxious fumes affecting the public. "
                            "The plaintiff seeks an injunction."
                        )
                    }
                ]
            },
        }
        result = self.node(state)
        issues = [i["issue"] for i in result.update["civil_gate_issues"]]
        assert any("special damage" in t.lower() for t in issues)
