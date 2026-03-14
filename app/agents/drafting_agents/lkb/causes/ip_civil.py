"""Group 8 — Intellectual Property (civil) causes.

Covers: passing off, copyright infringement, patent infringement,
design infringement.
"""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    _civil_and_commercial_rules,
    _entry,
)

CAUSES: dict = {
    # ── passing_off ──────────────────────────────────────────────────

    "passing_off": _entry(
        registry_kind="cause",
        code="passing_off",
        display_name="Suit for passing off / unfair competition",
        primary_acts=[
            {"act": "Trade Marks Act, 1999", "sections": ["Section 27(2)", "Section 134"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "113",
            "period": "Three years",
            "from": "When right to sue accrues (first passing off or discovery)",
        },
        court_rules=_civil_and_commercial_rules(nature_keywords=["trade mark", "brand", "commercial", "IP"]),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "plaintiff_goodwill_reputation", "defendant_misrepresentation",
            "damage_or_likelihood",
        ],
        required_reliefs=["permanent_injunction_against_passing_off", "damages_or_account_of_profits", "delivery_up", "costs"],
        doc_type_keywords=["passing off", "trade mark infringement", "unfair competition", "brand imitation"],
        facts_must_cover=[
            "Plaintiff's goodwill and reputation — duration of use, market share, geographic reach",
            "Defendant's misrepresentation — how the defendant's mark/get-up/packaging causes confusion",
            "Damage or likelihood of damage — actual confusion instances, diversion of customers, dilution",
        ],
        prayer_template=[
            "Pass a decree of permanent injunction restraining the Defendant from passing off its goods/services as those of the Plaintiff by using {{INFRINGING_MARK_OR_GETUP}}",
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- / direct an account of profits",
            "Direct the Defendant to deliver up all infringing goods, labels, packaging, and promotional material",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Classical trinity: (1) goodwill, (2) misrepresentation, (3) damage.",
            "S.134 TM Act: special jurisdiction where plaintiff carries on business.",
            "If value > Rs.3 lakh, Commercial Court jurisdiction.",
        ],
        complexity_weight=3,
    ),

    # ── copyright_infringement_civil ─────────────────────────────────

    "copyright_infringement_civil": _entry(
        registry_kind="cause",
        code="copyright_infringement_civil",
        display_name="Civil suit for copyright infringement",
        primary_acts=[
            {"act": "Copyright Act, 1957", "sections": ["Section 51 (infringement)", "Section 55 (civil remedies)", "Section 62 (jurisdiction)"]},
            {"act": "Code of Civil Procedure, 1908", "sections": []},
        ],
        limitation={
            "article": "113",
            "period": "Three years",
            "from": "When right to sue accrues (date of each infringing act)",
        },
        court_rules=_civil_and_commercial_rules(nature_keywords=["copyright", "IP", "commercial"]),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "copyright_ownership", "work_description",
            "infringement_details", "damages_computation",
        ],
        required_reliefs=["permanent_injunction", "damages_or_account_of_profits", "delivery_up_of_infringing_copies", "costs"],
        doc_type_keywords=["copyright infringement", "piracy", "copy", "reproduction without licence"],
        facts_must_cover=[
            "Plaintiff's copyright ownership — original work, date of creation, registration (if any)",
            "Description of the copyrighted work — nature (literary, artistic, musical, etc.)",
            "Defendant's specific infringing acts — reproduction, distribution, public performance, adaptation",
            "Damage suffered — loss of revenue, market dilution, or basis for account of profits",
        ],
        prayer_template=[
            "Pass a decree of permanent injunction restraining the Defendant from reproducing, distributing, or otherwise infringing the Plaintiff's copyright in {{WORK_DESCRIPTION}}",
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- / direct an account of profits at the Plaintiff's election",
            "Direct delivery up and destruction of all infringing copies in the Defendant's possession",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "S.62 Copyright Act: special jurisdiction — suit where plaintiff resides or carries on business.",
            "S.55: damages OR account of profits — not both.",
            "If value > Rs.3 lakh, Commercial Court has jurisdiction.",
        ],
        complexity_weight=3,
    ),

    # ── patent_infringement_civil ────────────────────────────────────

    "patent_infringement_civil": _entry(
        registry_kind="cause",
        code="patent_infringement_civil",
        display_name="Civil suit for patent infringement",
        primary_acts=[
            {"act": "Patents Act, 1970", "sections": ["Section 48 (rights)", "Section 104 (suit for infringement)", "Section 104A (burden of proof for process patents)"]},
            {"act": "Code of Civil Procedure, 1908", "sections": []},
        ],
        limitation={
            "article": "113",
            "period": "Three years",
            "from": "When right to sue accrues (date of each infringing act)",
        },
        court_rules=_civil_and_commercial_rules(nature_keywords=["patent", "IP", "commercial"]),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "patent_details", "claims_infringed",
            "infringement_particulars", "damages_or_account",
        ],
        required_reliefs=["permanent_injunction", "damages_or_account_of_profits", "delivery_up_or_destruction", "costs"],
        doc_type_keywords=["patent infringement", "patent violation", "process patent"],
        facts_must_cover=[
            "Patent details — patent number, date of grant, claims relied upon",
            "Specific claims infringed — claim-by-claim mapping to Defendant's product/process",
            "Defendant's infringing acts — manufacture, sale, import, use of patented invention",
            "Damage suffered — lost sales, royalty basis, or account of profits",
        ],
        prayer_template=[
            "Pass a decree of permanent injunction restraining the Defendant from manufacturing, selling, offering for sale, importing, or using the patented invention covered by Patent No. {{PATENT_NUMBER}}",
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- / direct an account of profits",
            "Direct delivery up or destruction of all infringing articles",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "S.104: suit in District Court having jurisdiction — not below District Court.",
            "S.104A: for process patents, burden on defendant to prove different process.",
            "S.107: defendant may counterclaim for revocation of patent.",
        ],
        complexity_weight=3,
    ),

    # ── design_infringement_civil ────────────────────────────────────

    "design_infringement_civil": _entry(
        registry_kind="cause",
        code="design_infringement_civil",
        display_name="Civil suit for design infringement",
        primary_acts=[
            {"act": "Designs Act, 2000", "sections": ["Section 22 (piracy of registered design)"]},
            {"act": "Code of Civil Procedure, 1908", "sections": []},
        ],
        limitation={
            "article": "113",
            "period": "Three years",
            "from": "When right to sue accrues",
        },
        court_rules=_civil_and_commercial_rules(nature_keywords=["design", "IP", "commercial"]),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "design_registration_details", "infringement_particulars",
            "damages_computation",
        ],
        required_reliefs=["injunction", "damages_or_account_of_profits", "costs"],
        doc_type_keywords=["design infringement", "registered design piracy", "design piracy"],
        facts_must_cover=[
            "Design registration details — registration number, date of registration, class",
            "Description of the registered design — visual features, shape, configuration",
            "Defendant's infringing acts — application of the design to articles for sale",
            "Damage suffered or statutory damages under S.22 Designs Act",
        ],
        prayer_template=[
            "Pass a decree of permanent injunction restraining the Defendant from applying, importing, or selling articles bearing the Plaintiff's registered design No. {{DESIGN_NUMBER}}",
            "Pass a decree for damages / direct an account of profits",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "S.22 Designs Act: statutory damages cap of Rs.25,000 per design — relevant for valuation and court fee.",
        ],
        complexity_weight=2,
    ),
}
