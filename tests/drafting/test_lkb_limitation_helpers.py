from __future__ import annotations

import sys

sys.path.insert(0, ".")


def test_article_limitation_details():
    from app.agents.drafting_agents.lkb.limitation import get_limitation_reference_details

    details = get_limitation_reference_details({"article": "55"})
    assert details["kind"] == "limitation_article"
    assert details["short_citation"] == "Article 55"
    assert details["act"] == "Limitation Act, 1963"


def test_special_statute_limitation_details():
    from app.agents.drafting_agents.lkb.limitation import get_limitation_reference_details

    details = get_limitation_reference_details({
        "article": "N/A",
        "reference": "S.34(3) A&C Act",
        "act": "Arbitration and Conciliation Act, 1996",
    })
    assert details["kind"] == "statutory_reference"
    assert details["citation"] == "Section 34(3) of the Arbitration and Conciliation Act, 1996"
    assert details["short_citation"] == "Section 34(3)"


def test_special_statute_limitation_verified_provision():
    from app.agents.drafting_agents.lkb.limitation import build_limitation_verified_provision

    provision = build_limitation_verified_provision({
        "article": "N/A",
        "reference": "Section 69 of the Consumer Protection Act, 2019",
        "act": "Consumer Protection Act, 2019",
        "description": "Complaint limitation",
    })
    assert provision == {
        "section": "Section 69",
        "act": "Consumer Protection Act, 2019",
        "text": "Complaint limitation",
        "source": "",
    }


def test_none_limitation_does_not_create_verified_provision():
    from app.agents.drafting_agents.lkb.limitation import build_limitation_verified_provision

    assert build_limitation_verified_provision({"article": "NONE"}) is None


def test_unknown_limitation_details_do_not_require_citation():
    from app.agents.drafting_agents.lkb.limitation import get_limitation_reference_details

    details = get_limitation_reference_details({"article": "UNKNOWN"})
    assert details["kind"] == "unknown"
    assert details["requires_citation"] is False


def test_single_accrual_normalized_to_single_event():
    from app.agents.drafting_agents.lkb.limitation import normalize_coa_type

    assert normalize_coa_type("single_accrual") == "single_event"


def test_lookup_multi_no_cross_domain_fallback():
    """lookup_multi for non-civil domain returns empty — domain boundaries are hard."""
    from app.agents.drafting_agents.lkb import lookup_multi

    entries = lookup_multi("Family", ["money_recovery_loan", "breach_of_contract"])
    assert len(entries) == 0  # no cross-domain fallback

    # But Civil domain resolves correctly
    civil_entries = lookup_multi("Civil", ["money_recovery_loan", "breach_of_contract"])
    assert len(civil_entries) == 2
    assert all(isinstance(entry, dict) for entry in civil_entries)


def test_catalog_fixups_for_wrong_limitation_articles():
    from app.agents.drafting_agents.lkb import lookup

    assert lookup("Civil", "conversion")["limitation"]["article"] == "91(a)"
    assert lookup("Civil", "trespass_goods_movable")["limitation"]["article"] == "91(b)"
    assert lookup("Civil", "copyright_infringement_civil")["limitation"]["article"] == "113"
    assert lookup("Civil", "patent_infringement_civil")["limitation"]["article"] == "113"
    assert lookup("Civil", "design_infringement_civil")["limitation"]["article"] == "113"


def test_catalog_uses_unknown_when_one_flattened_article_would_be_misleading():
    from app.agents.drafting_agents.lkb import lookup

    assert lookup("Civil", "money_recovery_loan")["limitation"]["article"] == "UNKNOWN"
    assert lookup("Civil", "summary_suit_instrument")["limitation"]["article"] == "UNKNOWN"
    assert lookup("Civil", "recovery_specific_movable")["limitation"]["article"] == "UNKNOWN"
    assert lookup("Civil", "partition")["limitation"]["article"] == "UNKNOWN"
    assert lookup("Civil", "eviction")["limitation"]["article"] == "UNKNOWN"
    assert lookup("Civil", "trespass_immovable")["limitation"]["article"] == "UNKNOWN"


def test_entry_factory_now_exposes_all_generator_fields():
    from app.agents.drafting_agents.lkb import lookup

    entry = lookup("Civil", "money_recovery_loan")
    for key in ("defensive_points", "terminology", "court_fee_statute", "detected_court"):
        assert key in entry


def test_template_engine_does_not_inject_contract_doctrines_without_lkb_support():
    from app.agents.drafting_agents.templates.engine import TemplateEngine

    engine = TemplateEngine()
    result = engine._legal_basis({
        "permitted_doctrines": [],
        "primary_acts": [
            {"act": "Indian Succession Act, 1925", "sections": ["Section 276"]},
        ],
    })
    assert "Indian Succession Act, 1925" in result
    assert "breach of contract" not in result.lower()
    assert "section 73" not in result.lower()


def test_cause_groups_do_not_silently_duplicate_codes():
    from app.agents.drafting_agents.lkb.causes import CAUSE_GROUPS, SUBSTANTIVE_CAUSES

    total_listed = sum(len(meta["causes"]) for meta in CAUSE_GROUPS.values())
    assert total_listed == len(SUBSTANTIVE_CAUSES)
