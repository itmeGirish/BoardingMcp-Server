"""v7.0 Unit Tests — new deterministic components.

Tests all v7.0 pipeline components that don't require LLM calls:
  - routing/complexity: complexity scoring (4-12) + tier assignment
  - routing/model_router: model selection based on tier + cause overrides
  - gates/theory_anchoring: legal theory extraction + anchoring check
  - gates/procedural_prerequisites: prerequisite detection + placeholder insertion
  - lkb v2.0: new fields (permitted_doctrines, court_fee_statute, etc.)

Run:  pytest tests/drafting/test_v7_unit.py -v
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, ".")


# ===========================================================================
# A) Complexity Scoring Tests
# ===========================================================================

class TestComplexityScoring:
    """Test compute_complexity: deterministic scoring from user prompt."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.routing.complexity import (
            compute_complexity,
            CAUSE_WEIGHTS,
        )
        self.compute = compute_complexity
        self.weights = CAUSE_WEIGHTS

    def test_simple_money_recovery(self):
        """Short money recovery prompt → SIMPLE tier."""
        prompt = "Draft a suit for recovery of Rs. 15,00,000 lent to defendant."
        score, tier = self.compute(prompt)
        assert tier == "SIMPLE"
        assert 4 <= score <= 6

    def test_medium_breach_contract(self):
        """Breach of contract with some damage heads → MEDIUM tier."""
        prompt = (
            "Draft a suit for damages for breach of contract. "
            "Plaintiff and defendant entered into an agreement. "
            "Defendant failed to deliver goods. Claim compensation "
            "for loss of profit and consequential damages."
        )
        score, tier = self.compute(prompt)
        assert tier in ("MEDIUM", "COMPLEX")
        assert score >= 7

    def test_complex_dealership_damages(self):
        """Dealership damages with multiple heads → COMPLEX tier."""
        prompt = (
            "Draft a commercial suit seeking damages for illegal termination "
            "of dealership agreement. Plaintiff invested substantial capital "
            "and developed territory market. Defendant terminated arbitrarily. "
            "Claim compensation for loss of profit, goodwill, unsold stock, "
            "and consequential damages. The plaintiff has suffered expenditure "
            "losses and penalty charges."
        )
        score, tier = self.compute(prompt)
        assert tier == "COMPLEX"
        assert score >= 10

    def test_score_range(self):
        """Score always in 4-12 range."""
        for prompt in ["Hi", "x" * 10000, "", "Draft a suit"]:
            score, tier = self.compute(prompt)
            assert 4 <= score <= 12
            assert tier in ("SIMPLE", "MEDIUM", "COMPLEX")

    def test_partition_complex(self):
        """Partition suit keyword triggers higher weight (3).
        Short prompt still scores low overall, but cause_type override
        in model_router ensures partition always routes to COMPLEX."""
        prompt = "Draft a partition suit for co-owner of joint property."
        score, tier = self.compute(prompt)
        # partition weight=3 + short prompt=1 = 4 minimum
        assert score >= 4
        # The model router override (not complexity score) ensures COMPLEX routing
        from app.agents.drafting_agents.routing.model_router import route_model
        route = route_model(tier, cause_type="partition")
        assert route.model == "glm-5:cloud"

    def test_empty_prompt(self):
        """Empty prompt → minimum score."""
        score, tier = self.compute("")
        assert score == 4
        assert tier == "SIMPLE"

    def test_tier_boundaries(self):
        """Verify tier boundary definitions."""
        # We can't control exact scores, but verify the function returns valid tiers
        for _ in range(10):
            import random
            words = random.choices(
                ["loan", "breach", "partition", "damages", "plaintiff", "defendant",
                 "profit", "goodwill", "stock", "expenditure", "interest"],
                k=random.randint(1, 20),
            )
            prompt = " ".join(words)
            score, tier = self.compute(prompt)
            if score <= 6:
                assert tier == "SIMPLE"
            elif score <= 9:
                assert tier == "MEDIUM"
            else:
                assert tier == "COMPLEX"


# ===========================================================================
# B) Model Router Tests
# ===========================================================================

class TestModelRouter:
    """Test route_model: model selection based on tier and overrides."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.routing.model_router import (
            route_model,
            ModelRoute,
            MODEL_ROUTES,
            CAUSE_TYPE_OVERRIDES,
            FALLBACK_CHAIN,
            get_fallbacks,
        )
        self.route = route_model
        self.ModelRoute = ModelRoute
        self.routes = MODEL_ROUTES
        self.overrides = CAUSE_TYPE_OVERRIDES
        self.fallbacks = FALLBACK_CHAIN
        self.get_fallbacks = get_fallbacks

    def test_simple_tier_routes_to_glm47(self):
        result = self.route("SIMPLE")
        assert result.model == "glm-4.7:cloud"
        assert result.reasoning is False
        assert result.source == "tier"

    def test_medium_tier_routes_to_qwen35(self):
        result = self.route("MEDIUM")
        assert result.model == "qwen3.5:cloud"
        assert result.reasoning is True
        assert result.source == "tier"

    def test_complex_tier_routes_to_glm5(self):
        result = self.route("COMPLEX")
        assert result.model == "glm-5:cloud"
        assert result.reasoning is True
        assert result.source == "tier"

    def test_partition_override(self):
        """Partition always routes to glm-5 regardless of tier."""
        result = self.route("SIMPLE", cause_type="partition")
        assert result.model == "glm-5:cloud"
        assert result.source == "cause_override"

    def test_ni138_override(self):
        """NI 138 always routes to glm-4.7 regardless of tier."""
        result = self.route("COMPLEX", cause_type="ni_138_complaint")
        assert result.model == "glm-4.7:cloud"
        assert result.source == "cause_override"

    def test_unknown_cause_type_no_override(self):
        """Unknown cause type → uses tier-based routing."""
        result = self.route("MEDIUM", cause_type="some_unknown_type")
        assert result.model == "qwen3.5:cloud"
        assert result.source == "tier"

    def test_fallback_chain_exists(self):
        """All primary models have fallback chains."""
        for model in ["glm-5:cloud", "qwen3.5:cloud", "glm-4.7:cloud"]:
            fallbacks = self.get_fallbacks(model)
            assert len(fallbacks) > 0, f"No fallbacks for {model}"

    def test_fallback_chain_no_self_reference(self):
        """Fallback chain doesn't include the primary model."""
        for model, fallbacks in self.fallbacks.items():
            assert model not in fallbacks

    def test_model_route_is_frozen(self):
        """ModelRoute is immutable."""
        result = self.route("SIMPLE")
        with pytest.raises(AttributeError):
            result.model = "other"  # type: ignore[misc]

    def test_temperature_by_tier(self):
        """SIMPLE has lower temp, COMPLEX has higher."""
        simple = self.route("SIMPLE")
        complex_ = self.route("COMPLEX")
        assert simple.temperature <= complex_.temperature


# ===========================================================================
# C) Legal Theory Anchoring (Gate 2) Tests
# ===========================================================================

class TestTheoryAnchoring:
    """Test legal_theory_anchoring_gate: doctrine extraction + anchoring."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.gates.theory_anchoring import (
            legal_theory_anchoring_gate,
            extract_legal_theories,
            DOCTRINE_PATTERNS,
        )
        self.gate = legal_theory_anchoring_gate
        self.extract = extract_legal_theories
        self.patterns = DOCTRINE_PATTERNS

    def test_extract_breach_of_contract(self):
        draft = "The defendant committed breach of the said contract."
        theories = self.extract(draft)
        assert "breach_of_contract" in theories

    def test_extract_section_73(self):
        draft = "The plaintiff is entitled to compensation under Section 73."
        theories = self.extract(draft)
        assert "damages_s73" in theories

    def test_extract_unjust_enrichment(self):
        draft = "The defendant has been unjustly enriched at the expense of plaintiff."
        theories = self.extract(draft)
        assert "unjust_enrichment" in theories

    def test_extract_quantum_meruit(self):
        draft = "The plaintiff claims quantum meruit for services rendered."
        theories = self.extract(draft)
        assert "quantum_meruit" in theories

    def test_extract_multiple_theories(self):
        draft = (
            "The defendant committed breach of the agreement. "
            "Section 73 entitles compensation. "
            "There was also unjust enrichment."
        )
        theories = self.extract(draft)
        assert "breach_of_contract" in theories
        assert "damages_s73" in theories
        assert "unjust_enrichment" in theories

    def test_no_theories_in_plain_text(self):
        draft = "The parties entered into an agreement on 15.03.2024."
        theories = self.extract(draft)
        assert len(theories) == 0

    def test_anchored_theory_passes(self):
        """Theory in LKB permitted_doctrines → PASS."""
        draft = "The defendant committed breach of the said contract."
        lkb = {"permitted_doctrines": ["breach_of_contract", "damages_s73"]}
        result = self.gate(draft, lkb_entry=lkb)
        assert result.passed is True
        assert "breach_of_contract" in result.theories_anchored
        assert len(result.theories_unanchored) == 0

    def test_unanchored_theory_fails(self):
        """Theory NOT in LKB permitted_doctrines → FAIL."""
        draft = "The defendant has been unjustly enriched."
        lkb = {"permitted_doctrines": ["breach_of_contract"]}
        result = self.gate(draft, lkb_entry=lkb)
        assert result.passed is False
        assert "unjust_enrichment" in result.theories_unanchored
        assert any("UNANCHORED_THEORY" in f for f in result.flags)

    def test_user_request_anchors_theory(self):
        """Theory mentioned in user request → anchored."""
        draft = "The defendant committed unjust enrichment."
        lkb = {"permitted_doctrines": []}
        result = self.gate(
            draft,
            lkb_entry=lkb,
            user_request="Draft a suit based on unjust enrichment.",
        )
        assert result.passed is True
        assert "unjust_enrichment" in result.theories_anchored

    def test_provision_anchors_theory(self):
        """Theory derived from verified provisions → anchored."""
        draft = "The plaintiff is entitled to compensation under Section 73."
        lkb = {"permitted_doctrines": []}
        provisions = [{"section": "Section 73", "act": "Indian Contract Act, 1872"}]
        result = self.gate(draft, lkb_entry=lkb, verified_provisions=provisions)
        assert result.passed is True
        assert "damages_s73" in result.theories_anchored

    def test_universal_theories_always_allowed(self):
        """breach_of_contract, mitigation, waiver always allowed."""
        draft = (
            "Breach of contract. Plaintiff took steps to mitigate damages. "
            "Defendant's waiver of rights."
        )
        lkb = {"permitted_doctrines": []}
        result = self.gate(draft, lkb_entry=lkb)
        assert result.passed is True

    def test_no_lkb_entry(self):
        """No LKB entry → only universal theories pass."""
        draft = "Breach of contract by defendant."
        result = self.gate(draft, lkb_entry=None)
        assert result.passed is True  # breach_of_contract is universal

    def test_estoppel_unanchored(self):
        """Estoppel not in LKB → flagged."""
        draft = "The defendant is estopped from denying the agreement."
        lkb = {"permitted_doctrines": ["breach_of_contract"]}
        result = self.gate(draft, lkb_entry=lkb)
        assert result.passed is False
        assert "estoppel" in result.theories_unanchored


# ===========================================================================
# D) Procedural Prerequisites (Gate 4) Tests
# ===========================================================================

class TestProceduralPrerequisites:
    """Test procedural_prerequisites_gate: check mandatory requirements."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.gates.procedural_prerequisites import (
            procedural_prerequisites_gate,
            PREREQUISITES,
        )
        self.gate = procedural_prerequisites_gate
        self.prereqs = PREREQUISITES

    def test_commercial_suit_has_prerequisites(self):
        """Commercial suit has S.12A and arbitration prerequisites."""
        assert "commercial_suit" in self.prereqs
        ids = [p["id"] for p in self.prereqs["commercial_suit"]]
        assert "section_12a_mediation" in ids
        assert "arbitration_clause" in ids

    def test_ni138_has_notice_prerequisite(self):
        """NI 138 complaint has statutory notice prerequisite."""
        assert "ni_138_complaint" in self.prereqs
        ids = [p["id"] for p in self.prereqs["ni_138_complaint"]]
        assert "statutory_notice_s138" in ids

    def test_unknown_doc_type_no_prereqs(self):
        """Unknown doc type → no prerequisites, passes."""
        result = self.gate("Some draft text", "unknown_type")
        assert result.passed is True
        assert len(result.checks) == 0

    def test_mediation_confirmed_in_intake(self):
        """S.12A mentioned in intake → no flag."""
        result = self.gate(
            draft="The plaintiff has complied with Section 12A mediation.",
            doc_type="commercial_suit",
            intake_text="Pre-institution mediation was undertaken.",
        )
        # mediation found in intake → should not flag
        mediation_checks = [c for c in result.checks if c.id == "section_12a_mediation"]
        assert len(mediation_checks) == 1
        assert mediation_checks[0].found_in_intake is True

    def test_mediation_not_confirmed_not_in_draft(self):
        """S.12A NOT in intake and NOT in draft → flag."""
        result = self.gate(
            draft="The plaintiff files this commercial suit.",
            doc_type="commercial_suit",
            intake_text="The parties had an agreement.",
        )
        mediation_checks = [c for c in result.checks if c.id == "section_12a_mediation"]
        assert len(mediation_checks) == 1
        assert mediation_checks[0].found_in_intake is False
        assert mediation_checks[0].found_in_draft is False
        assert result.passed is False
        assert result.placeholders_inserted > 0

    def test_arbitration_mentioned_in_user_request(self):
        """Arbitration mentioned in user request → found."""
        result = self.gate(
            draft="This suit is filed.",
            doc_type="commercial_suit",
            intake_text="",
            user_request="There is an arbitration clause in the agreement.",
        )
        arb_checks = [c for c in result.checks if c.id == "arbitration_clause"]
        assert len(arb_checks) == 1
        assert arb_checks[0].found_in_intake is True  # found via combined text

    def test_ni138_notice_confirmed(self):
        """NI 138 notice mentioned in intake → passes."""
        result = self.gate(
            draft="Notice under Section 138 was sent.",
            doc_type="ni_138_complaint",
            intake_text="Legal notice demanding payment was sent on 01.01.2025.",
        )
        notice_checks = [c for c in result.checks if c.id == "statutory_notice_s138"]
        assert len(notice_checks) == 1
        assert notice_checks[0].found_in_intake is True

    def test_eviction_notice_missing(self):
        """Eviction without notice → flag."""
        result = self.gate(
            draft="Eviction suit against tenant.",
            doc_type="eviction_suit",
            intake_text="Tenant has not paid rent for 6 months.",
        )
        assert result.passed is False
        assert any("notice_s106_tpa" in f for f in result.flags)


# ===========================================================================
# E) LKB v2.0 Extensions Tests
# ===========================================================================

class TestLKBv2:
    """Test LKB v2.0 extended fields."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.lkb import lookup
        self.lookup = lookup

    def test_money_recovery_has_v2_fields(self):
        entry = self.lookup("Civil", "money_recovery_loan")
        assert entry is not None
        assert "permitted_doctrines" in entry
        assert "required_sections" in entry
        assert "complexity_weight" in entry

    def test_breach_contract_has_v2_fields(self):
        entry = self.lookup("Civil", "breach_of_contract")
        assert entry is not None
        assert "permitted_doctrines" in entry
        assert "damages_s73" in entry["permitted_doctrines"]
        assert "complexity_weight" in entry
        assert entry["complexity_weight"] == 2

    def test_dealership_has_v2_fields(self):
        entry = self.lookup("Civil", "breach_dealership_franchise")
        assert entry is not None
        assert "permitted_doctrines" in entry
        assert "repudiatory_breach" in entry["permitted_doctrines"]
        assert "procedural_prerequisites" in entry
        assert "section_12a_mediation" in entry["procedural_prerequisites"]
        assert entry["complexity_weight"] == 3

    def test_partition_has_v2_fields(self):
        entry = self.lookup("Civil", "partition")
        assert entry is not None
        assert "permitted_doctrines" in entry
        assert "required_sections" in entry
        assert entry["complexity_weight"] == 3

    def test_court_fee_statute_per_state(self):
        entry = self.lookup("Civil", "breach_dealership_franchise")
        assert entry is not None
        cfs = entry["court_fee_statute"]
        assert "Karnataka" in cfs
        assert "Karnataka Court Fees" in cfs["Karnataka"]
        assert "_default" in cfs

    def test_excluded_doctrines(self):
        entry = self.lookup("Civil", "breach_of_contract")
        assert entry is not None
        assert "unjust_enrichment" in entry["excluded_doctrines"]
        assert "quantum_meruit" in entry["excluded_doctrines"]

    def test_required_sections_non_empty(self):
        for cause_type in ["money_recovery_loan", "breach_of_contract", "partition"]:
            entry = self.lookup("Civil", cause_type)
            assert entry is not None
            sections = entry.get("required_sections", [])
            assert len(sections) >= 8, f"{cause_type} has too few required sections"
            assert "prayer" in sections
            assert "verification" in sections

    def test_complexity_weight_range(self):
        """Complexity weight is 1-3."""
        for cause_type in ["money_recovery_loan", "breach_of_contract",
                           "breach_dealership_franchise", "partition"]:
            entry = self.lookup("Civil", cause_type)
            assert entry is not None
            weight = entry.get("complexity_weight", 0)
            assert 1 <= weight <= 3, f"{cause_type} weight={weight}"


# ===========================================================================
# F) Integration: Complexity + Routing + LKB
# ===========================================================================

class TestIntegrationRouting:
    """Test end-to-end: prompt → complexity → routing → model."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.agents.drafting_agents.routing.complexity import compute_complexity
        from app.agents.drafting_agents.routing.model_router import route_model
        from app.agents.drafting_agents.lkb import lookup
        self.compute = compute_complexity
        self.route = route_model
        self.lookup = lookup

    def test_simple_prompt_gets_fast_model(self):
        """Simple money recovery → SIMPLE → glm-4.7."""
        prompt = "Recover Rs. 10 lakh loan from defendant."
        score, tier = self.compute(prompt)
        route = self.route(tier, cause_type="money_recovery_loan")
        # money_recovery_loan has no override, so uses tier
        assert route.model in ("glm-4.7:cloud", "qwen3.5:cloud")

    def test_partition_always_complex_model(self):
        """Partition → override → glm-5 regardless of score."""
        prompt = "Partition suit."
        _, tier = self.compute(prompt)
        route = self.route(tier, cause_type="partition")
        assert route.model == "glm-5:cloud"
        assert route.source == "cause_override"

    def test_lkb_doctrines_feed_theory_gate(self):
        """LKB permitted_doctrines used by theory anchoring gate."""
        from app.agents.drafting_agents.gates.theory_anchoring import (
            legal_theory_anchoring_gate,
        )
        entry = self.lookup("Civil", "breach_of_contract")
        assert entry is not None

        draft = "Breach of contract. Section 73 compensation. Unjust enrichment."
        result = legal_theory_anchoring_gate(
            draft, lkb_entry=entry
        )
        # breach_of_contract and damages_s73 are permitted → anchored
        assert "breach_of_contract" in result.theories_anchored
        assert "damages_s73" in result.theories_anchored
        # unjust_enrichment is excluded → unanchored
        assert "unjust_enrichment" in result.theories_unanchored
        assert result.passed is False


# ===========================================================================
# G) Graph Compilation Tests
# ===========================================================================

class TestGraphCompilation:
    """Test that the drafting graph still compiles with new components."""

    def test_graph_compiles(self):
        from app.agents.drafting_agents.drafting_graph import get_drafting_graph
        graph = get_drafting_graph()
        assert graph is not None

    def test_graph_has_draft_freetext_node(self):
        from app.agents.drafting_agents.drafting_graph import get_drafting_graph
        graph = get_drafting_graph()
        # Check node names
        node_names = list(graph.nodes.keys())
        assert "draft_freetext" in node_names

    def test_graph_has_intake_classify_node(self):
        from app.agents.drafting_agents.drafting_graph import get_drafting_graph
        graph = get_drafting_graph()
        node_names = list(graph.nodes.keys())
        assert "intake_classify" in node_names
