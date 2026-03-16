"""Group 4 — Injunction & Declaratory Reliefs.

Flattened from civil.py SUBSTANTIVE_CAUSES. No conditional fields.
"""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    _civil_court_rules,
    _entry,
)

# ---------------------------------------------------------------------------
# CAUSES
# ---------------------------------------------------------------------------

CAUSES: dict = {

    # ── permanent_injunction ──────────────────────────────────────────────
    "permanent_injunction": _entry(
        registry_kind="cause",
        code="permanent_injunction",
        display_name="Suit for perpetual / permanent injunction",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 36", "Section 37", "Section 38"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Section 20"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When the right to sue accrues — for continuing interference, each fresh act restarts the clock (residuary — no specific article for injunction suits)"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["plaintiff_right", "defendant_threat", "irreparable_harm"],
        required_reliefs=["permanent_injunction_decree", "costs"],
        doc_type_keywords=["permanent injunction", "restrain", "prohibit", "injunction suit"],
        mandatory_inline_sections=[
            {
                "section": "PLAINTIFF RIGHT AND DEFENDANT INTERFERENCE",
                "placement": "after jurisdiction",
                "instruction": "Nature of right, specific acts threatening it, continuing nature.",
            },
            {
                "section": "INADEQUACY OF DAMAGES / NEED FOR INJUNCTION",
                "placement": "after facts",
                "instruction": "Why damages are not an adequate final remedy and why the continuing or threatened invasion warrants final injunctive relief. Avoid interim-application formulae.",
            },
        ],
        facts_must_cover=[
            "Nature of plaintiff's right — if POSSESSION-based (revenue records, cultivation, long settlement): plead settled, peaceful, open, continuous possession with documentary basis (RTC/Pahani/Khasra/tax receipts); if TITLE-based: plead title chain with sale deed/lease/statutory right. Do NOT over-plead title when the case is really about possession",
            "Specific acts of defendant threatening or invading the right (dates, nature, frequency) — plead each interference event as a separate numbered paragraph",
            "Whether invasion is actual or apprehended — if apprehended, basis for reasonable apprehension",
            "Why damages would be inadequate remedy (immovable property is unique, continuing wrong, multiplicity of suits)",
            "Plaintiff's conduct — no delay, no acquiescence, prompt action on knowledge of threat",
            "For immovable property suits: SCHEDULE OF PROPERTY with survey/khasra number, area/extent, village/tehsil/district, boundaries (E/W/N/S)",
            "That defendant has NO lawful right to interfere with plaintiff's possession (not necessarily that defendant has 'no title' — avoid unnecessary title disputes)",
        ],
        prayer_template=[
            "Pass a decree of perpetual injunction restraining the Defendant, his agents, servants, and all persons claiming through or under him from {{SPECIFIC_ACTS_TO_BE_RESTRAINED}} in respect of the suit property/right",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper in the facts and circumstances of the case",
        ],
        defensive_points=[
            "Pre-empt 'delay / acquiescence' defence: plead dates showing prompt action upon knowledge of threat",
            "Pre-empt 'S.41 SRA bar' defence: screen the present clauses in Section 41, including clause (ha) inserted in 2018, and plead why no statutory bar applies",
            "Pre-empt 'adequate remedy at law' defence: plead why damages cannot compensate (unique property, continuing wrong, multiplicity of suits)",
            "Pre-empt 'no legal right' defence: plead documentary basis of right (title deed, registered agreement, statutory entitlement)",
            "Pre-empt the contention that final injunctive relief would be inequitable or unnecessary by pleading the continuing invasion and inadequacy of damages",
        ],
        mandatory_averments=[
            {
                "averment": "legal_right_of_plaintiff",
                "provision": "Section 38(3), Specific Relief Act, 1963",
                "instruction": "Plead the specific right to or enjoyment of property that the defendant is invading or threatening (S.38(3) chapeau). For obligation-based injunctions (e.g., negative covenant under S.42 SRA), the obligation under S.38(1) is the basis. Without a subsisting right or obligation, injunction cannot issue.",
            },
            {
                "averment": "inadequacy_of_damages",
                "provision": "Section 38(3)(c), Specific Relief Act, 1963",
                "instruction": "Plead specifically why compensation in money would not afford adequate relief — unique property, continuing wrong, irreversible harm. Also consider S.38(3)(b) where no standard exists to ascertain damage.",
            },
        ],
        evidence_checklist=[
            "Title deed / sale deed / lease agreement / statutory notification establishing right",
            "Photographs / videos of defendant's encroachment or threatening acts",
            "Legal notice sent to defendant and reply (if any)",
            "Revenue records / khasra / survey map for immovable property disputes",
            "Witnesses to defendant's acts of interference",
        ],
        drafting_red_flags=[
            "Three mandatory elements: (1) plaintiff legal right, (2) invasion/threat by defendant, (3) damages inadequate.",
            "Section 41 SRA must be screened in its current amended form, including clause (ha) for notified infrastructure project contracts.",
            "Delay and acquiescence may disentitle plaintiff — plead promptness.",
            "For property-based injunctions: declaration of title may be needed as ancillary relief under S.34 SRA if title is disputed.",
            "Negative covenant injunction (S.42 SRA): if based on contract, plead the specific negative term breached.",
        ],
        # ── v11.0 Layer 2: Document Components ──
        available_reliefs=[
            {"type": "injunction", "subtype": "permanent", "statute": "S.38 SRA",
             "prayer_text": "decree of perpetual injunction restraining the Defendant, his agents, servants, and all persons claiming through or under him from {{SPECIFIC_ACTS_TO_BE_RESTRAINED}}"},
            {"type": "costs", "statute": "S.35 CPC",
             "prayer_text": "costs of the suit"},
            {"type": "general",
             "prayer_text": "such other and further relief(s) as this Hon'ble Court may deem fit and proper"},
        ],
        jurisdiction_basis="Section 16(d) CPC — situs of property — MANDATORY where the suit concerns rights in or to immovable property. Proviso: where relief is purely by personal obedience of the defendant (prohibitory restraint only), suit may alternatively be filed where defendant resides/carries on business (S.16 proviso). Section 20 CPC governs where the subject-matter is not immovable property (e.g., trade-secret injunction, negative covenant under S.42 SRA)",
        valuation_basis="State-specific — POSSESSION-based injunction (no title dispute): many states prescribe fixed court fee (Delhi, AP, Telangana, Rajasthan). TITLE-contested or Karnataka/Maharashtra: ad valorem on market value of property. Use {{COURT_FEE_AMOUNT}} if state-specific rate is unknown. For pecuniary jurisdiction: value of the right sought to be protected",
        complexity_weight=2,
    ),

    # ── mandatory_injunction ──────────────────────────────────────────────
    "mandatory_injunction": _entry(
        registry_kind="cause",
        code="mandatory_injunction",
        display_name="Suit for mandatory injunction / removal / restoration",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 37", "Section 39"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Section 20"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When the right to sue accrues — for continuing interference, each fresh act restarts the clock (residuary — no specific article for mandatory injunction suits)"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["status_quo_ante", "wrongful_change_or_obstruction"],
        required_reliefs=["mandatory_injunction_decree", "costs"],
        doc_type_keywords=["mandatory injunction", "removal", "restore", "demolition"],
        facts_must_cover=[
            "Plaintiff's existing right or possession over the property / pathway",
            "Defendant's specific wrongful act — encroachment, obstruction, or alteration with measurements and survey reference",
            "When the encroachment / wrongful change occurred (date or approximate period)",
            "Status quo ante — what the position was before the Defendant's wrongful act",
            "What restoration or removal the Plaintiff seeks",
        ],
        prayer_template=[
            "Pass a decree of mandatory injunction directing the Defendant to remove / undo the wrongful obstruction, encroachment, or alteration and restore the position as it existed prior to the Defendant's unlawful acts",
            "Pass a decree of permanent injunction restraining the Defendant from repeating the wrongful act",
            "In the alternative, award damages if restoration is impracticable",
            "Award costs of the suit",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        mandatory_averments=[
            {
                "averment": "subsisting_obligation",
                "provision": "Section 39, Specific Relief Act, 1963",
                "instruction": "Plead the specific obligation that the Defendant is bound to perform or refrain from breaching, with documentary basis.",
            },
            {
                "averment": "wrongful_act_altering_status_quo",
                "provision": "Section 39, Specific Relief Act, 1963",
                "instruction": "Plead the specific wrongful act (encroachment, obstruction, alteration) that changed the status quo, with dates and measurements.",
            },
        ],
        defensive_points=[
            "Pre-empt 'delay / acquiescence' defence: plead dates showing prompt action — delay is MORE fatal for mandatory injunction than prohibitory",
            "Pre-empt 'hardship / impossibility' defence: plead that restoration is physically feasible and that Defendant's hardship does not outweigh Plaintiff's right",
            "Pre-empt 'construction complete' defence: plead both mandatory injunction (demolition/removal) and alternative damages if restoration is impracticable",
        ],
        evidence_checklist=[
            "Survey map / site plan showing encroachment / obstruction with measurements",
            "Photographs / videos of the wrongful alteration (before and after if available)",
            "Title deed / ownership document establishing Plaintiff's right",
            "Legal notice demanding removal / restoration and reply (if any)",
            "Revenue records / municipal records of the property",
        ],
        drafting_red_flags=[
            "Mandatory injunction is discretionary and comparatively stricter than a prohibitory injunction; plead the subsisting obligation, the wrongful change/obstruction, and why restoration of the status quo is necessary.",
            "S.39 SRA: mandatory injunction to prevent breach of obligation — more stringent than prohibitory injunction.",
            "Delay is MORE fatal for mandatory injunction than prohibitory — prompt action essential.",
            "If unauthorized construction is complete, court may award damages instead of demolition — plead both alternatives.",
        ],
        complexity_weight=2,
    ),
}
