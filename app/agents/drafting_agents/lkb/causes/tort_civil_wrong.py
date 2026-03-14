"""Group 5 — Tort / Civil Wrong causes.

Covers: negligence (personal injury & property damage), defamation,
nuisance, trespass (immovable & movable), business disparagement,
conversion, false imprisonment, malicious prosecution, fraud/deceit,
wrongful seizure, illegal distress, tortious interference, and
compensation for acts under enactment.
"""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    _civil_and_commercial_rules,
    _civil_court_rules,
    _entry,
)

CAUSES: dict = {
    # ── tortious_negligence flattened into two sub-types ──────────────

    "negligence_personal_injury": _entry(
        registry_kind="cause",
        code="negligence_personal_injury",
        display_name="Damages for negligence — personal injury / bodily harm",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Negligence", "Duty of care"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19", "Section 20"]},
        ],
        limitation={
            "article": "113",
            "period": "Three years",
            "from": "When the plaintiff first sustains ascertainable damage from the negligent act (not the date of the act itself)",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["duty_of_care", "breach_of_duty", "causation_and_damage"],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["negligence", "tort", "duty of care", "damages", "personal injury", "bodily harm"],
        permitted_doctrines=["duty_breach_causation", "res_ipsa_loquitur", "contributory_negligence", "volenti_non_fit_injuria"],
        procedural_prerequisites=[
            "section_80_cpc_notice_if_government_defendant",
            "mact_forum_screen_if_vehicle_accident",
            "consumer_forum_screen_if_service_deficiency",
        ],
        facts_must_cover=[
            "Duty of care owed by Defendant to Plaintiff — relationship giving rise to duty",
            "Specific act or omission constituting breach of duty",
            "Factual causation — how the breach caused the injury (but-for test)",
            "Nature and extent of bodily injury or harm sustained",
        ],
        prayer_template=[
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for injuries sustained due to the Defendant's negligence",
            "Award interest on the decretal amount at such rate as this Hon'ble Court deems fit",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "If motor vehicle accident, MACT has exclusive jurisdiction.",
            "If service deficiency, Consumer Protection Act forum has concurrent jurisdiction.",
            "Professional negligence requires expert evidence.",
            "Res ipsa loquitur shifts evidential burden — plead specifically.",
            "Art 73 Limitation Act may apply to bodily injury (1 year) instead of Art 113 (3 years) — verify for specific injury type.",
        ],
        complexity_weight=2,
    ),

    "negligence_property_damage": _entry(
        registry_kind="cause",
        code="negligence_property_damage",
        display_name="Damages for negligence — property damage / economic loss",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Negligence", "Duty of care"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19", "Section 20"]},
        ],
        limitation={
            "article": "113",
            "period": "Three years",
            "from": "When the plaintiff first suffers ascertainable property damage attributable to the negligent act",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["duty_of_care", "breach_of_duty", "causation_and_damage"],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["negligence", "tort", "duty of care", "damages", "property damage", "economic loss"],
        permitted_doctrines=["duty_breach_causation", "res_ipsa_loquitur", "contributory_negligence", "volenti_non_fit_injuria"],
        procedural_prerequisites=[
            "section_80_cpc_notice_if_government_defendant",
            "mact_forum_screen_if_vehicle_accident",
            "consumer_forum_screen_if_service_deficiency",
        ],
        facts_must_cover=[
            "Duty of care owed by Defendant to Plaintiff — relationship giving rise to duty",
            "Specific act or omission constituting breach of duty",
            "Factual causation — how the breach caused the property damage or economic loss",
            "Nature, extent, and value of property damaged or economic loss suffered",
        ],
        prayer_template=[
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for property damage / economic loss caused by the Defendant's negligence",
            "Award interest on the decretal amount at such rate as this Hon'ble Court deems fit",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "If motor vehicle accident, MACT has exclusive jurisdiction.",
            "If service deficiency, Consumer Protection Act forum has concurrent jurisdiction.",
            "Professional negligence requires expert evidence.",
            "Res ipsa loquitur shifts evidential burden — plead specifically.",
        ],
        complexity_weight=2,
    ),

    # ── defamation (flattened — default Art 75, one year) ────────────

    "defamation": _entry(
        registry_kind="cause",
        code="defamation",
        display_name="Suit for damages for defamation",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Libel", "Slander", "Defamation"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19"]},
        ],
        limitation={
            "article": "75 / 76",
            "period": "One year",
            "from": "When defamatory matter is published",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "defamatory_statement", "publication_to_third_parties",
            "falsity_and_malice", "damage_to_reputation",
        ],
        required_reliefs=["damages_decree", "permanent_injunction_against_repetition", "costs"],
        doc_type_keywords=["defamation", "libel", "slander", "false allegations", "social media defamation"],
        damages_categories=["general_damages", "aggravated_damages", "exemplary_damages_if_malice"],
        permitted_doctrines=["innuendo", "fair_comment", "qualified_privilege", "absolute_privilege"],
        facts_must_cover=[
            "Exact words or substance of the defamatory statement (verbatim if written/libel, substance if oral/slander)",
            "Medium of publication: newspaper, social media post, letter, TV broadcast, oral in meeting — with date(s)",
            "Identity of third parties to whom the statement was published (or class of persons if mass media)",
            "That the statement refers to the plaintiff (by name, or by description identifiable to those who know the plaintiff — innuendo)",
            "That the statement is false — plead falsity specifically, not merely 'defamatory'",
            "Malice: if claiming aggravated/exemplary damages, plead defendant's knowledge of falsity or reckless disregard",
            "Damage to reputation: loss of business, social ostracism, mental distress, specific instances of changed treatment by third parties",
            "For slander (oral): special damages with particularity unless slander per se (imputation of crime / disease / unchastity / professional incompetence)",
        ],
        prayer_template=[
            "Pass a decree awarding damages of Rs. {{CLAIM_AMOUNT}}/- to the Plaintiff as compensation for injury to reputation",
            "Pass a decree of permanent injunction restraining the Defendant from further publishing, circulating, or repeating the said defamatory statements or any statements of similar import",
            "Direct the Defendant to publish an unconditional apology in {{PUBLICATION_MEDIUM}} at the Defendant's cost",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper in the facts and circumstances of the case",
        ],
        defensive_points=[
            "Pre-empt 'truth / justification' defence: plead falsity with specific facts showing statements untrue; anticipate what defendant might claim as 'true'",
            "Pre-empt 'fair comment on matter of public interest' defence: plead that statements are assertions of fact, not comment; or if comment, actuated by malice",
            "Pre-empt 'qualified privilege' defence (reports of proceedings, employer reference): plead malice to defeat privilege — ill-will, improper motive, or reckless publication",
            "Pre-empt 'consent' defence: plead plaintiff never authorised publication",
            "Pre-empt 'limitation' defence: plead the exact date of publication and, for online material, the facts of upload and continued accessibility with precision",
        ],
        mandatory_averments=[
            {
                "averment": "defamatory_imputation",
                "provision": "Law of Torts — Defamation",
                "instruction": "Set out the exact words complained of (for libel) or their substance (for slander). If meaning is not plain, plead innuendo — the special facts known to readers/listeners that give the words defamatory meaning.",
            },
            {
                "averment": "publication_to_third_parties",
                "provision": "Law of Torts — Publication",
                "instruction": "Plead that the statement was communicated to at least one person other than the plaintiff. Identify the medium, date, and audience.",
            },
        ],
        evidence_checklist=[
            "Copy/screenshot of defamatory publication (newspaper cutting, social media screenshot with URL and timestamp, letter)",
            "Notarized printout of online content under Section 65B Indian Evidence Act / S.63 BSA with certificate",
            "Witness statements from persons who read/heard the defamatory matter",
            "Evidence of plaintiff's standing/reputation before the publication (profession, social standing, awards)",
            "Evidence of actual damage: loss of clients, cancelled contracts, social exclusion, medical records for mental distress",
            "Legal notice demanding retraction and defendant's response (if any)",
        ],
        drafting_red_flags=[
            "Limitation ONLY ONE YEAR (Art 75/76) — verify dates meticulously.",
            "For slander, special damages must be proved unless slander per se (imputation of criminal offence, loathsome disease, unchastity of woman, professional incompetence).",
            "Truth is complete defence — only plead if statements demonstrably false.",
            "Online defamation: S.79 IT Act gives intermediary immunity; target the original publisher. S.66A struck down (Shreya Singhal).",
            "If the publication concerns public officials or public bodies, plead falsity, malice, and the absence of privilege/public-interest protection with particularity.",
        ],
        complexity_weight=2,
    ),

    # ── nuisance ─────────────────────────────────────────────────────

    "nuisance": _entry(
        registry_kind="cause",
        code="nuisance",
        display_name="Abatement of nuisance and damages",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Private Nuisance"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 38", "Section 39"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Section 19"]},
        ],
        alternative_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 91"]},
        ],
        limitation={
            "article": "73",
            "period": "One year (continuing nuisance: fresh cause of action accrues daily — S.22 Limitation Act)",
            "from": "When nuisance first affects plaintiff",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["nuisance_description", "interference_with_enjoyment"],
        required_reliefs=["injunction_abate_nuisance", "damages_if_claimed", "costs"],
        doc_type_keywords=["nuisance", "noise pollution", "obstruction", "interference"],
        facts_must_cover=[
            "Plaintiff's use and enjoyment of land/property that is being interfered with",
            "Nature of the nuisance — noise, fumes, vibration, obstruction, pollution, encroachment",
            "Unreasonableness of the interference — frequency, duration, severity",
            "Continuity or repetition of the nuisance (dates and duration)",
            "Damage suffered — health effects, loss of amenity, depreciation of property value",
        ],
        prayer_template=[
            "Pass a decree of mandatory injunction directing the Defendant to abate / remove the nuisance",
            "Pass a decree of permanent injunction restraining the Defendant from continuing or repeating the said nuisance",
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for loss suffered",
            "Award costs of the suit",
        ],
        procedural_prerequisites=["section_91_cpc_standing_screen", "section_80_cpc_notice_if_government_defendant"],
        drafting_red_flags=[
            "For a representative public-nuisance suit under Section 91 CPC, the proper route is by the Advocate-General or by two or more persons with leave of court. Section 91(2) separately preserves private suits.",
            "Coming to the nuisance NOT a defence in Indian law.",
            "If a prescriptive easement is asserted in answer to the claim, verify Section 15 of the Easements Act and plead the exact right claimed; do not cite Section 26 as a general right to commit nuisance.",
        ],
        coa_type="continuing",
        complexity_weight=2,
    ),

    # ── trespass_immovable (flattened — default Art 65, 12 years) ────

    # ── trespass_goods_movable ───────────────────────────────────────

    "trespass_goods_movable": _entry(
        registry_kind="cause",
        code="trespass_goods_movable",
        display_name="Civil action for trespass / interference with goods",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Trespass to goods"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19"]},
        ],
        limitation={
            "article": "91(b)",
            "period": "Three years",
            "from": "When the movable property is wrongfully taken, injured, or wrongfully detained",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "movable_description", "interference_details", "loss_or_detention",
        ],
        required_reliefs=["damages_decree", "injunction_against_repetition", "costs"],
        doc_type_keywords=["trespass to goods", "movable interference", "detention of goods"],
        facts_must_cover=[
            "Description of the goods — nature, quantity, value",
            "Plaintiff's possession or right to immediate possession of the goods",
            "Specific act of DIRECT interference by Defendant — taking, damaging, using, moving",
            "Damage caused to the goods or loss suffered by Plaintiff",
        ],
        prayer_template=[
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for trespass to / interference with the Plaintiff's goods",
            "Pass a decree of permanent injunction restraining the Defendant from further interference with the said goods",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Trespass = DIRECT interference with goods. Consequential damage is negligence, not trespass.",
            "Distinct from conversion (appropriation) and detinue (wrongful retention).",
        ],
        complexity_weight=2,
    ),

    # ── business_disparagement ───────────────────────────────────────

    "business_disparagement": _entry(
        registry_kind="cause",
        code="business_disparagement",
        display_name="Civil action for business disparagement / injurious falsehood",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Malicious falsehood"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "113",
            "period": "Three years",
            "from": "When right to sue accrues",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "false_statement", "publication", "malice", "special_damage",
        ],
        required_reliefs=["damages_decree", "injunction_against_repetition", "costs"],
        doc_type_keywords=["business disparagement", "malicious falsehood", "trade libel"],
        facts_must_cover=[
            "The false statement made by Defendant about Plaintiff's goods, services, or business",
            "Malice or dishonesty — Defendant knew the statement was false or was reckless as to its truth",
            "Publication — to whom, when, and by what medium the false statement was communicated",
            "Special damage — actual pecuniary loss suffered (loss of specific customers, cancelled orders, quantified revenue loss)",
        ],
        prayer_template=[
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for special damage suffered due to the Defendant's malicious falsehood",
            "Pass a decree of permanent injunction restraining the Defendant from publishing or repeating the said disparaging statements",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Special damage MANDATORY — general reputational injury insufficient.",
        ],
        complexity_weight=2,
    ),

    # ── conversion ───────────────────────────────────────────────────

    "conversion": _entry(
        registry_kind="cause",
        code="conversion",
        display_name="Suit for damages for conversion of property",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Conversion"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19"]},
        ],
        limitation={
            "article": "91(a)",
            "period": "Three years",
            "from": "When the plaintiff first learns in whose possession the converted property is, or from the conversion trigger recognised by the governing article",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "movable_description", "conversion_act", "plaintiff_entitlement", "value_of_goods",
        ],
        required_reliefs=["damages_for_value_of_goods_converted", "interest", "costs"],
        doc_type_keywords=["conversion", "wrongful exercise of dominion", "appropriation of goods"],
        facts_must_cover=[
            "Description of the property converted — nature, quantity, value",
            "Plaintiff's ownership or right to immediate possession",
            "Defendant's specific act of dominion — appropriation, sale, destruction, refusal to return",
            "That the act was inconsistent with Plaintiff's rights as owner",
            "Value of the goods at the date of conversion",
        ],
        alternative_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 7", "Section 8"]},
        ],
        drafting_red_flags=[
            "Conversion = wrongful exercise of dominion inconsistent with owner's rights. Distinct from trespass (mere interference) and detinue (wrongful detention).",
            "Damages typically = market value at date of conversion.",
            "If specific recovery sought (not just damages), SRA S.7/S.8 apply.",
        ],
        complexity_weight=2,
    ),

    # ── false_imprisonment_civil ─────────────────────────────────────

    "false_imprisonment_civil": _entry(
        registry_kind="cause",
        code="false_imprisonment_civil",
        display_name="Civil suit for damages for false imprisonment",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["False imprisonment"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19", "Section 20"]},
        ],
        limitation={
            "article": "74",
            "period": "One year",
            "from": "When the imprisonment ends",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "detention_details", "absence_of_lawful_authority", "damage",
        ],
        required_reliefs=["damages_decree", "exemplary_damages_if_claimed", "costs"],
        doc_type_keywords=["false imprisonment", "wrongful detention", "unlawful confinement"],
        facts_must_cover=[
            "Act of Defendant that caused the restraint of Plaintiff's liberty",
            "That the restraint was TOTAL — no reasonable means of escape available",
            "Duration of imprisonment — from when to when",
            "Absence of lawful authority for the detention",
        ],
        prayer_template=[
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for false imprisonment",
            "Award exemplary damages for the high-handed and unlawful conduct of the Defendant",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Limitation ONLY ONE YEAR (Art 74) — verify dates.",
            "Total restraint of liberty required — mere obstruction of one route is not false imprisonment.",
            "Knowledge of plaintiff not necessary — imprisonment can exist without plaintiff knowing.",
        ],
        complexity_weight=2,
    ),

    # ── malicious_prosecution_civil ──────────────────────────────────

    "malicious_prosecution_civil": _entry(
        registry_kind="cause",
        code="malicious_prosecution_civil",
        display_name="Civil suit for damages for malicious prosecution",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Malicious prosecution"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19", "Section 20"]},
        ],
        limitation={
            "article": "77",
            "period": "One year",
            "from": "When plaintiff is acquitted or prosecution terminated",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "prosecution_details", "termination_in_favour",
            "absence_of_reasonable_cause", "malice", "damage",
        ],
        required_reliefs=["damages_decree", "costs"],
        doc_type_keywords=["malicious prosecution", "false case", "wrongful prosecution damages"],
        facts_must_cover=[
            "That the Defendant initiated or continued a criminal prosecution against the Plaintiff",
            "That the prosecution terminated in Plaintiff's favour — acquittal, discharge, or withdrawal",
            "Absence of reasonable and probable cause for the prosecution",
            "Malice — the prosecution was actuated by an improper motive, not bona fide pursuit of justice",
        ],
        prayer_template=[
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for malicious prosecution",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Limitation ONLY ONE YEAR (Art 77).",
            "ALL FOUR elements: (1) defendant prosecuted, (2) ended in plaintiff favour, (3) no reasonable cause, (4) malice.",
        ],
        complexity_weight=3,
    ),

    # ── fraud_misrepresentation_standalone ────────────────────────────

    "fraud_misrepresentation_standalone": _entry(
        registry_kind="cause",
        code="fraud_misrepresentation_standalone",
        display_name="Civil suit for damages for fraud / deceit",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Fraud / Deceit"]},
            {"act": "Indian Contract Act, 1872", "sections": ["Section 17"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 19"]},
        ],
        limitation={
            "article": "113",
            "period": "Three years",
            "from": "When right to sue accrues (when fraud is discovered or could have been discovered with reasonable diligence — S.17 Limitation Act applies)",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "false_representation", "knowledge_of_falsity",
            "intention_to_induce", "reliance_and_damage",
        ],
        required_reliefs=["damages_decree", "interest", "costs"],
        doc_type_keywords=["fraud", "deceit", "misrepresentation", "cheating civil"],
        facts_must_cover=[
            "The false representation of fact made by Defendant — exact words or substance",
            "That Defendant knew the representation was false or was recklessly indifferent to its truth",
            "That the representation was made with the intention of inducing Plaintiff to act on it",
            "That Plaintiff acted on the representation — specific reliance",
            "Damage suffered as a result — quantified financial loss",
        ],
        prayer_template=[
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for fraud / deceit perpetrated by the Defendant",
            "Award interest on the decretal amount at such rate as this Hon'ble Court deems fit",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Distinguish tort of deceit (standalone damages suit) from S.17/19 ICA (rescission/cancellation of contract induced by fraud).",
            "S.17 Limitation Act extends limitation from discovery of fraud — plead discovery date specifically.",
            "All 5 elements: (1) false representation, (2) of fact, (3) known to be false, (4) made to induce, (5) plaintiff acted on it and suffered damage.",
        ],
        complexity_weight=2,
    ),

    # ── wrongful_seizure_compensation ────────────────────────────────

    "wrongful_seizure_compensation": _entry(
        registry_kind="cause",
        code="wrongful_seizure_compensation",
        display_name="Compensation for wrongful seizure of movable property under legal process",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Wrongful seizure"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19"]},
        ],
        limitation={
            "article": "80",
            "period": "One year",
            "from": "The date of the seizure",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "seizure_details", "legal_process_under_which_seized",
            "wrongfulness_basis", "damage",
        ],
        required_reliefs=["damages_decree", "return_of_property_if_applicable", "costs"],
        doc_type_keywords=["wrongful seizure", "illegal seizure", "attachment wrong", "movable seized"],
        facts_must_cover=[
            "The legal process under which the seizure was purportedly made",
            "Description of the goods seized — nature, quantity, value",
            "Basis of wrongfulness — no authority, wrong property seized, excess seizure",
            "Damage suffered by Plaintiff as a result of the seizure",
        ],
        drafting_red_flags=[
            "Limitation ONLY ONE YEAR (Art 80).",
            "Applies to seizure under legal process — not to private taking (which is trespass/conversion).",
        ],
        complexity_weight=2,
    ),

    # ── illegal_distress_compensation ────────────────────────────────

    "illegal_distress_compensation": _entry(
        registry_kind="cause",
        code="illegal_distress_compensation",
        display_name="Compensation for illegal / irregular / excessive distress",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Distress"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19"]},
        ],
        limitation={
            "article": "79",
            "period": "One year",
            "from": "The date of the distress",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "distress_details", "illegality_or_irregularity", "damage",
        ],
        required_reliefs=["damages_decree", "costs"],
        doc_type_keywords=["illegal distress", "irregular distress", "excessive distress"],
        facts_must_cover=[
            "Basis of Defendant's claimed right to distrain (or absence thereof)",
            "Description of goods distrained — nature, quantity, value",
            "Ground of illegality, irregularity, or excess — which category and why",
            "Damage suffered by Plaintiff as a result of the distress",
        ],
        prayer_template=[
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for illegal / irregular / excessive distress",
            "Direct the Defendant to return the distrained goods to the Plaintiff",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Limitation ONLY ONE YEAR (Art 79).",
            "Illegal distress = no right to distrain at all. Irregular = right exists but exercise defective. Excessive = distrained more than owed.",
        ],
        complexity_weight=2,
    ),

    # ── tortious_interference_contract ───────────────────────────────

    "tortious_interference_contract": _entry(
        registry_kind="cause",
        code="tortious_interference_contract",
        display_name="Suit for inducing breach of contract with plaintiff",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Inducing breach of contract"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "113",
            "period": "Three years",
            "from": "When the right to sue accrues (date of inducement causing breach)",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "contract_with_third_party", "defendant_inducement",
            "breach_resulting", "damage",
        ],
        required_reliefs=["damages_decree", "injunction_against_further_inducement", "costs"],
        doc_type_keywords=["inducing breach", "tortious interference", "poaching employee", "interference with contract"],
        facts_must_cover=[
            "Existence of a valid contract between Plaintiff and a third party — date, parties, subject matter",
            "Defendant's knowledge of the contract",
            "Specific acts of inducement by Defendant that caused the third party to breach the contract",
            "The breach that resulted from Defendant's inducement",
            "Damage suffered by Plaintiff as a consequence of the breach",
        ],
        prayer_template=[
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for loss caused by the Defendant's tortious interference",
            "Pass a decree of permanent injunction restraining the Defendant from further inducing breach of Plaintiff's contracts",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Residuary limitation Art 113 — three years.",
            "Must prove: (1) valid contract existed, (2) defendant KNEW of the contract, (3) defendant INDUCED the breach, (4) plaintiff suffered damage.",
            "Distinct from breach of contract itself — this is a tort against the INDUCER, not the contract-breaker.",
        ],
        complexity_weight=3,
    ),

    # ── compensation_act_under_enactment ─────────────────────────────

    "compensation_act_under_enactment": _entry(
        registry_kind="cause",
        code="compensation_act_under_enactment",
        display_name="Compensation for act done under enactment",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Statutory tort"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19", "Section 20"]},
        ],
        limitation={
            "article": "72",
            "period": "One year",
            "from": "When the act or omission takes place",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "enactment_under_which_act_done", "act_or_omission_details",
            "unauthorized_or_excessive_character", "damage",
        ],
        required_reliefs=["damages_decree", "costs"],
        doc_type_keywords=["compensation enactment", "statutory act", "municipal demolition damages", "government action damages"],
        facts_must_cover=[
            "The enactment under which the act was purportedly done — specific Act and Section",
            "Description of the act or omission complained of",
            "The unauthorized or excessive character of the act — how it exceeded or lacked statutory authority",
            "Damage suffered by Plaintiff as a result",
        ],
        prayer_template=[
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- as compensation for the wrongful act done under colour of {{ENACTMENT_NAME}}",
            "Award costs of the suit",
        ],
        procedural_prerequisites=["section_80_cpc_notice_if_government_defendant"],
        drafting_red_flags=[
            "Limitation ONLY ONE YEAR (Art 72).",
            "Applies where act is alleged to be in pursuance of any enactment — if act was wholly unauthorized (no statutory basis), general tort articles apply instead.",
            "S.80 CPC notice mandatory if defendant is Government/public officer.",
        ],
        complexity_weight=2,
    ),
}
