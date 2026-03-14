"""Cause group sub-modules with duplicate-safe registry assembly."""
from __future__ import annotations

from .accounts_relationship import CAUSES as ACCOUNTS_AND_RELATIONSHIP
from .arbitration_court import CAUSES as ARBITRATION_COURT
from .consumer_special import CAUSES as CONSUMER_AND_SPECIAL_FORA
from .contract_commercial import CAUSES as CONTRACT_AND_COMMERCIAL
from .execution_restitution import CAUSES as EXECUTION_AND_RESTITUTION
from .family_guardianship import CAUSES as FAMILY_AND_GUARDIANSHIP
from .immovable_property import CAUSES as IMMOVABLE_PROPERTY
from .injunction_declaratory import CAUSES as INJUNCTION_AND_DECLARATORY
from .ip_civil import CAUSES as IP_CIVIL
from .money_and_debt import CAUSES as MONEY_AND_DEBT
from .partnership_business import CAUSES as PARTNERSHIP_AND_BUSINESS
from .public_special import CAUSES as PUBLIC_AND_SPECIAL_PROCEEDINGS
from .special_misc import CAUSES as SPECIAL_AND_MISCELLANEOUS
from .succession_estate import CAUSES as SUCCESSION_AND_ESTATE
from .tenancy_rent import CAUSES as TENANCY_AND_RENT
from .tort_civil_wrong import CAUSES as TORT_AND_CIVIL_WRONG
from .trust_fiduciary import CAUSES as TRUST_AND_FIDUCIARY

GROUPS = (
    ("MONEY_AND_DEBT", "Recovery of money / debt / liquidated amount", MONEY_AND_DEBT),
    (
        "CONTRACT_AND_COMMERCIAL",
        "Breach/enforcement of contract - damages or specific performance",
        CONTRACT_AND_COMMERCIAL,
    ),
    (
        "IMMOVABLE_PROPERTY",
        "Ownership, possession, title, boundaries, mortgage of immovable property",
        IMMOVABLE_PROPERTY,
    ),
    ("INJUNCTION_AND_DECLARATORY", "Standalone injunction or declaration", INJUNCTION_AND_DECLARATORY),
    ("TORT_AND_CIVIL_WRONG", "Damages for tortious acts (not arising from contract)", TORT_AND_CIVIL_WRONG),
    ("TENANCY_AND_RENT", "Landlord-tenant / licensor-licensee disputes", TENANCY_AND_RENT),
    ("ACCOUNTS_AND_RELATIONSHIP", "Rendition of accounts, duty to account, accounts stated", ACCOUNTS_AND_RELATIONSHIP),
    ("PARTNERSHIP_AND_BUSINESS", "Partnership dissolution, accounts, restraint", PARTNERSHIP_AND_BUSINESS),
    ("IP_CIVIL", "Intellectual property enforcement - civil track", IP_CIVIL),
    ("TRUST_AND_FIDUCIARY", "Trust property, breach of trust, benami", TRUST_AND_FIDUCIARY),
    ("EXECUTION_AND_RESTITUTION", "Post-decree enforcement, restitution", EXECUTION_AND_RESTITUTION),
    ("SPECIAL_AND_MISCELLANEOUS", "Rare/specialized civil causes", SPECIAL_AND_MISCELLANEOUS),
    (
        "SUCCESSION_AND_ESTATE",
        "Probate, letters of administration, succession certificate",
        SUCCESSION_AND_ESTATE,
    ),
    ("FAMILY_AND_GUARDIANSHIP", "Divorce, maintenance, custody, guardianship", FAMILY_AND_GUARDIANSHIP),
    ("ARBITRATION_COURT", "Court applications under Arbitration Act 1996", ARBITRATION_COURT),
    ("CONSUMER_AND_SPECIAL_FORA", "Consumer complaints, SARFAESI, IBC", CONSUMER_AND_SPECIAL_FORA),
    (
        "PUBLIC_AND_SPECIAL_PROCEEDINGS",
        "Public trust suits, public premises eviction",
        PUBLIC_AND_SPECIAL_PROCEEDINGS,
    ),
)


def _build_substantive_causes() -> dict:
    substantive_causes: dict = {}
    for group_name, _description, group in GROUPS:
        for code, entry in group.items():
            if code in substantive_causes:
                raise ValueError(
                    f"Duplicate LKB cause_type '{code}' detected while merging group '{group_name}'"
                )
            substantive_causes[code] = entry
    return substantive_causes


SUBSTANTIVE_CAUSES: dict = _build_substantive_causes()

CAUSE_GROUPS = {
    group_name: {"description": description, "causes": list(group.keys())}
    for group_name, description, group in GROUPS
}

DOCUMENT_TYPE_GROUPS: dict = {}
for _code, _entry in SUBSTANTIVE_CAUSES.items():
    _dtype = _entry.get("document_type", "plaint")
    DOCUMENT_TYPE_GROUPS.setdefault(_dtype, []).append(_code)
