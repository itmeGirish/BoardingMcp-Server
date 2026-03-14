"""Group 13 -- Family & Guardianship causes."""
from __future__ import annotations

from ._helpers import _entry

CAUSES: dict = {
    "divorce_nullity_judicial_separation": _entry(
        registry_kind="cause",
        code="divorce_nullity_judicial_separation",
        display_name="Petition for Divorce / Nullity / Judicial Separation",
        document_type="family_petition",
        primary_acts=[
            {"act": "Hindu Marriage Act, 1955", "sections": ["Section 11 (void marriages)", "Section 12 (nullity)", "Section 13 (divorce)", "Section 10 (judicial separation)"]},
            {"act": "Special Marriage Act, 1954", "sections": ["Section 27", "Section 28"]},
            {"act": "Family Courts Act, 1984", "sections": ["Section 7"]},
        ],
        limitation={"article": "N/A", "period": "Governed by specific matrimonial statute — no Limitation Act article", "from": "Varies by ground"},
        required_sections=[
            "family_court_heading", "petitioner_respondent_details",
            "marriage_details", "ground_for_relief", "children_details",
            "maintenance_claim_if_any", "prayer",
        ],
        doc_type_keywords=["divorce", "nullity", "judicial separation", "matrimonial", "HMA"],
        drafting_red_flags=[
            "Family Court has exclusive jurisdiction (Family Courts Act, 1984 S.7).",
            "S.13B HMA: mutual consent divorce requires 6-month cooling period (waivable per SC in Amardeep Singh).",
            "Family Courts Act, 1984 Section 9 requires the court to make efforts for settlement/conciliation where possible before proceeding with the merits.",
        ],
        complexity_weight=3,
    ),

    "maintenance_alimony": _entry(
        registry_kind="cause",
        code="maintenance_alimony",
        display_name="Petition for Maintenance / Alimony",
        document_type="family_petition",
        primary_acts=[
            {"act": "Hindu Adoptions and Maintenance Act, 1956", "sections": ["Section 18", "Section 22", "Section 23"]},
            {"act": "Hindu Marriage Act, 1955", "sections": ["Section 24 (pendente lite)", "Section 25 (permanent)"]},
            {"act": "Protection of Women from Domestic Violence Act, 2005", "sections": ["Section 20 (monetary reliefs)"]},
            {"act": "Bharatiya Nagarik Suraksha Sanhita, 2023", "sections": ["Section 144 (maintenance of wife, children, parents — formerly CrPC S.125)"]},
        ],
        limitation={"article": "N/A", "period": "Governed by specific statute", "from": "Varies"},
        required_sections=[
            "court_heading", "petitioner_respondent_details",
            "marriage_relationship", "income_and_means",
            "needs_and_expenses", "prayer_for_maintenance",
        ],
        doc_type_keywords=["maintenance", "alimony", "section 125", "section 24 HMA", "interim maintenance"],
        drafting_red_flags=[
            "S.144 BNSS (formerly S.125 CrPC) is available to wife of ALL religions — not limited by personal law.",
            "S.24 HMA applies only DURING pending matrimonial proceedings — cannot be filed standalone.",
            "BNSS S.144 replaced CrPC S.125 from 1 July 2024 — cite BNSS for new applications.",
            "Maintenance and Welfare of Parents and Senior Citizens Act, 2007 is a separate remedy for elderly parents.",
        ],
        complexity_weight=2,
    ),

    "custody_visitation": _entry(
        registry_kind="cause",
        code="custody_visitation",
        document_type="family_petition",
        display_name="Petition for Custody / Visitation / Guardianship of Minor",
        primary_acts=[
            {"act": "Guardians and Wards Act, 1890", "sections": ["Section 7", "Section 25"]},
            {"act": "Hindu Minority and Guardianship Act, 1956", "sections": ["Section 6", "Section 13"]},
        ],
        limitation={"article": "N/A", "period": "No limitation — welfare of child is paramount", "from": "N/A"},
        required_sections=[
            "court_heading", "petitioner_respondent_details",
            "child_details", "welfare_of_child_basis",
            "custody_arrangement_sought", "prayer",
        ],
        doc_type_keywords=["custody", "visitation", "guardian", "minor child", "welfare of child"],
        drafting_red_flags=[
            "Paramount consideration is WELFARE OF THE CHILD — not rights of parents.",
            "S.13 HMGA: welfare of minor is paramount in appointing guardian.",
            "Family Court jurisdiction under Family Courts Act, 1984.",
        ],
        complexity_weight=3,
    ),

    "guardianship_minor_property": _entry(
        registry_kind="cause",
        code="guardianship_minor_property",
        display_name="Application for Permission to Deal with Minor's Property",
        document_type="family_petition",
        primary_acts=[
            {"act": "Guardians and Wards Act, 1890", "sections": ["Section 7", "Section 29", "Section 30", "Section 31"]},
            {"act": "Hindu Minority and Guardianship Act, 1956", "sections": ["Section 8"]},
        ],
        limitation={"article": "N/A", "period": "No limitation — but must be filed before transaction", "from": "N/A"},
        required_sections=[
            "court_heading", "guardian_details", "minor_details",
            "property_details", "necessity_or_benefit_to_minor",
            "prayer_for_permission",
        ],
        doc_type_keywords=["guardian permission", "minor property", "section 29 GWA", "sell minor property"],
        drafting_red_flags=[
            "S.29 GWA: a guardian of property appointed or declared by the court cannot, without previous permission, mortgage, charge, transfer by sale/gift/exchange, or grant the prohibited leases of the minor's immovable property.",
            "For a Hindu natural guardian, Section 8 HMGA separately requires previous permission of the court for transfer of the minor's immovable property; an unauthorized transfer is voidable at the instance of the minor or a person claiming under the minor.",
            "Must demonstrate NECESSITY or clear BENEFIT to the minor.",
        ],
        complexity_weight=2,
    ),
}
