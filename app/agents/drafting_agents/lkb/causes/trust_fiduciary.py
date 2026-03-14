"""Group 9 — Trust & Fiduciary causes."""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    _civil_court_rules,
    _entry,
)

CAUSES: dict = {
    "trust_dispute_civil": _entry(
        registry_kind="cause",
        code="trust_dispute_civil",
        display_name="Civil suit relating to private trust",
        primary_acts=[
            {"act": "Indian Trusts Act, 1882", "sections": ["Section 13", "Section 23", "Section 35", "Section 46"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Do not assign one fixed article for every private-trust suit. Verify the relief sought, and screen Section 10 of the Limitation Act where trust property or its traceable proceeds remain vested in the trustee.",
            "period": "Relief-specific; may be unrestricted in the situations covered by Section 10 of the Limitation Act",
            "from": "From the governing relief-specific trigger, unless Section 10 of the Limitation Act applies",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "trust_instrument_details",
            "trustee_duty_and_breach",
            "beneficiary_standing",
        ],
        required_reliefs=["declaration_of_breach", "account_of_trust_property", "restoration_of_trust_property", "removal_of_trustee", "costs"],
        doc_type_keywords=["trust", "breach of trust", "trustee removal", "trust property"],
        facts_must_cover=[
            "Trust instrument — date, parties, nature of trust, trust property",
            "Trustee's specific duty breached — S.13 Indian Trusts Act (duties of trustee)",
            "Specific acts or omissions constituting breach of trust",
            "Loss or damage to trust property or beneficiary's interest",
        ],
        prayer_template=[
            "Pass a decree declaring that the Defendant-Trustee has committed breach of trust in respect of the trust property described in the Schedule",
            "Direct the Defendant to render a true and faithful account of the trust property and all dealings therewith",
            "Direct the Defendant to restore to the trust all property wrongfully alienated or applied in breach of trust",
            "Remove the Defendant from the office of Trustee and appoint a new Trustee in his place",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Distinguish private trust suits in the ordinary civil court from public/charitable trust proceedings under Section 92 CPC; Section 92 is not the procedural vehicle for a private trust dispute.",
            "Do NOT use Article 137 for a suit. Verify the relief-specific article, and screen Section 10 of the Limitation Act in express-trust/property-following cases.",
        ],
        complexity_weight=3,
    ),
    "benami_declaration": _entry(
        registry_kind="cause",
        code="benami_declaration",
        display_name="Declaration that property is benami / held in trust",
        primary_acts=[
            {"act": "Benami Transactions (Prohibition) Act, 1988 (as amended 2016)", "sections": ["Section 2(8) (benami property)", "Section 2(9) (benami transaction)", "Section 4 (prohibition)"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 34"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={"article": "58", "period": "Three years", "from": "When right to sue first accrues"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "benami_transaction_details",
            "real_owner_evidence",
            "benamidar_details",
            "schedule_of_property",
        ],
        required_reliefs=["declaration_benami", "reconveyance_direction", "permanent_injunction_against_alienation", "costs"],
        doc_type_keywords=["benami", "benami property", "benamidar", "real owner"],
        facts_must_cover=[
            "Property details — schedule with survey number, boundaries, area, market value",
            "Source of consideration — who paid and from what funds",
            "Circumstances of the benami transaction — why property was placed in Defendant's name",
            "Evidence establishing Plaintiff as the real owner — payment records, possession, improvements",
        ],
        prayer_template=[
            "Pass a decree declaring that the property described in the Schedule is the benami property of the Plaintiff and that the Defendant holds the same as benamidar / in trust for the Plaintiff",
            "Direct the Defendant to execute a deed of reconveyance / transfer in favour of the Plaintiff",
            "Pass a decree of permanent injunction restraining the Defendant from alienating, encumbering, or dealing with the suit property in any manner",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Post-2016 Amendment: Initiating Authority under the Act has primary jurisdiction for benami transactions. Civil suit maintainability must be screened.",
            "Section 4 generally bars suits to enforce benami rights. Do not rely on the old Section 4 'wife/child' exception; instead screen whether the facts fall outside Section 2(9) because they fit one of the current statutory exclusions.",
            "Distinguish 'benami' from 'trust' — fiduciary relationship vs prohibited transaction.",
        ],
        complexity_weight=3,
    ),
}
