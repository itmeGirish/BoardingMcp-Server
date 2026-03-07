"""v8.0 Template Engine — builds 15 of 18 plaint sections deterministically.

LLM generates only 3 sections: FACTS, BREACH PARTICULARS, DAMAGES NARRATIVE.
Everything else is correct by construction.

Usage:
    from app.agents.drafting_agents.templates.engine import TemplateEngine
    engine = TemplateEngine()
    skeleton = engine.assemble(state)
    # skeleton contains {{GENERATE:FACTS}}, {{GENERATE:BREACH}}, {{GENERATE:DAMAGES}}
    # for LLM to fill in
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..lkb import lookup


# ---------------------------------------------------------------------------
# Verbatim legal templates (never LLM-generated)
# ---------------------------------------------------------------------------

_VERIFICATION_TEMPLATE = """VERIFICATION

Verified at {{{{CITY}}}} on this the ____ day of __________ 20____.

I, {{{{PLAINTIFF_NAME}}}}, the Plaintiff above-named, do hereby verify that the contents of paragraphs 1 to {last_para} of this plaint are true and correct to my knowledge, and no material facts have been concealed therefrom, and that I have not filed any other suit, petition, or proceeding in any court or before any authority in respect of the same subject matter and cause of action.

DEPONENT

{{{{PLAINTIFF_NAME}}}}
PLAINTIFF"""

_SOT_TEMPLATE = """STATEMENT OF TRUTH

I, {{{{PLAINTIFF_NAME}}}}, the Plaintiff / authorised representative of the Plaintiff herein, do hereby state on solemn affirmation that the contents of the above plaint and the facts stated in paragraphs 1 to {last_para} are true to my knowledge and belief and nothing material has been concealed therefrom.

I understand that I shall be liable to proceedings under law for making a false statement.

Verified at {{{{CITY}}}} on this the ____ day of __________ 20____.

                                    {{{{PLAINTIFF_NAME}}}}
                                    PLAINTIFF"""

_ADVOCATE_BLOCK = """
                                    THROUGH:
                                    {{ADVOCATE_NAME}}
                                    Advocate for the Plaintiff
                                    Enrollment No. {{ENROLLMENT_NO}}
                                    {{ADVOCATE_ADDRESS}}
                                    Mobile: {{ADVOCATE_PHONE}}
                                    Email: {{ADVOCATE_EMAIL}}"""


# ---------------------------------------------------------------------------
# Damage category display names
# ---------------------------------------------------------------------------

_DAMAGE_DISPLAY = {
    "principal_amount": "Principal amount",
    "interest_on_principal": "Interest on principal",
    "loss_of_profit_unexpired_term": "Loss of profit for the unexpired term",
    "loss_of_goodwill": "Loss of goodwill",
    "wasted_capital_investment": "Wasted capital investment",
    "loss_on_unsold_stock": "Loss on unsold stock",
    "future_business_opportunities": "Loss of future business opportunities",
    "loss_of_profit": "Loss of profit",
    "wasted_investment": "Wasted investment",
    "consequential_loss": "Consequential loss / damages",
    "price_of_goods": "Price of goods sold and delivered",
    "interest_on_price": "Interest on price",
    "loss_of_salary": "Loss of salary and emoluments",
    "loss_of_benefits": "Loss of benefits",
    "reputational_damage": "Reputational damage",
    "special_damages": "Special damages",
    "general_damages": "General damages",
    "cost_of_repair": "Cost of repair / rectification",
    "diminution_in_value": "Diminution in value",
    "mental_agony": "Compensation for mental agony and harassment",
}


# ---------------------------------------------------------------------------
# Doctrine templates (for Legal Basis section)
# ---------------------------------------------------------------------------

_DOCTRINE_TEMPLATES = {
    "breach_of_contract": (
        "The Defendant is liable for breach of the agreement. The Defendant has "
        "failed to perform its obligations under the agreement, thereby committing "
        "a breach of contract entitling the Plaintiff to claim damages."
    ),
    "damages_s73": (
        "The Plaintiff is entitled to compensation under Section 73 of the Indian "
        "Contract Act, 1872, which provides that when a contract has been broken, "
        "the party who suffers by such breach is entitled to receive compensation "
        "for any loss or damage caused thereby, which naturally arose in the usual "
        "course of things from such breach, or which the parties knew, when they "
        "made the contract, to be likely to result from the breach of it."
    ),
    "damages_s74": (
        "Without prejudice to the above and in the alternative, if the agreement "
        "contains a stipulation for liquidated damages or penalty for breach, the "
        "Defendant is liable under Section 74 of the Indian Contract Act, 1872, to "
        "pay reasonable compensation not exceeding the amount so named in the contract."
    ),
    "repudiatory_breach_s39": (
        "The Defendant has committed a repudiatory breach within the meaning of "
        "Section 39 of the Indian Contract Act, 1872, by refusing to perform and "
        "disabling itself from performing its obligations under the agreement. The "
        "Plaintiff is entitled to treat the contract as rescinded and claim damages."
    ),
    "mitigation": (
        "The Plaintiff has taken all reasonable steps to mitigate the loss and "
        "damage caused by the Defendant's breach, including but not limited to "
        "seeking alternative business opportunities and minimizing ongoing expenses."
    ),
}


class TemplateEngine:
    """Builds a document skeleton with deterministic sections + LLM gaps."""

    def __init__(self):
        self._para = 0  # paragraph counter
        self._annexure = 0  # annexure counter (A=0, B=1, ...)

    def _next_para(self) -> int:
        self._para += 1
        return self._para

    def _next_annexure(self) -> str:
        label = chr(65 + self._annexure)  # A, B, C, ...
        self._annexure += 1
        return label

    def assemble(
        self,
        intake: Dict[str, Any],
        classify: Dict[str, Any],
        lkb_brief: Dict[str, Any],
        mandatory_provisions: Dict[str, Any],
        court_fee: Optional[Dict[str, Any]] = None,
        user_request: str = "",
    ) -> str:
        """Build complete document skeleton with 3 LLM gaps.

        Returns plain text with markers:
          {{GENERATE:FACTS}}
          {{GENERATE:BREACH}}
          {{GENERATE:DAMAGES}}
        """
        self._para = 0
        self._annexure = 0

        # Extract data from state
        cause_type = classify.get("cause_type", "")
        doc_type = classify.get("doc_type", "")
        law_domain = classify.get("law_domain", "Civil")

        # LKB entry (from lkb_brief or fresh lookup)
        lkb = lkb_brief if lkb_brief else {}
        if not lkb and cause_type:
            lkb = lookup(law_domain, cause_type) or {}

        detected_court = lkb.get("detected_court", lkb.get("court_rules", {}).get("default", {}))
        is_commercial = "commercial" in detected_court.get("court", "").lower()

        # Intake data
        jurisdiction = self._get_jurisdiction(intake)
        parties = self._get_parties(intake)
        facts_obj = self._get_facts(intake)
        evidence = self._get_evidence(intake)
        limitation = mandatory_provisions.get("limitation", {}) if mandatory_provisions else {}
        state = jurisdiction.get("state", "")

        sections: List[str] = []

        # 1. Court Heading
        sections.append(self._court_heading(detected_court, jurisdiction))

        # 2. Parties
        sections.append(self._parties_block(parties))

        # 3. Title
        sections.append(self._suit_title(lkb, detected_court))

        sections.append("MOST RESPECTFULLY SHOWETH:")

        # 4. Commercial Maintainability (if commercial)
        if is_commercial:
            sections.append(self._commercial_maintainability(facts_obj, lkb))

        # 5. Jurisdiction
        sections.append(self._jurisdiction_section(jurisdiction, detected_court, is_commercial))

        # 6. Limitation
        sections.append(self._limitation_section(limitation, lkb))

        # 7. Section 12A (if commercial)
        if is_commercial:
            sections.append(self._section_12a(intake, user_request))

        # 8. Arbitration Disclosure (if commercial and prerequisite)
        prereqs = lkb.get("procedural_prerequisites", [])
        if "arbitration_clause" in prereqs:
            sections.append(self._arbitration_disclosure(intake, user_request))

        # ---- LLM GAPS ----

        # 9. Facts (LLM generates)
        # Tell LLM what paragraph number to start from
        sections.append(f"{{{{GENERATE:FACTS|start_para={self._para + 1}}}}}")

        # 10. Breach Particulars (LLM generates)
        sections.append("{{GENERATE:BREACH}}")

        # 11. Damages Narrative (LLM generates)
        sections.append("{{GENERATE:DAMAGES}}")

        # ---- END LLM GAPS ----

        # 12. Legal Basis (from LKB permitted_doctrines)
        sections.append(self._legal_basis(lkb))

        # 13. Cause of Action (template + intake dates)
        sections.append(self._cause_of_action(lkb, facts_obj))

        # 14. Valuation & Court Fee (deterministic)
        sections.append(self._valuation_court_fee(lkb, facts_obj, state, court_fee))

        # 15. Interest
        sections.append(self._interest_section(lkb))

        # 16. Prayer (from LKB damages_categories)
        sections.append(self._prayer(lkb))

        # 17. Damages Schedule (if commercial)
        if is_commercial:
            sections.append(self._damages_schedule(lkb))

        # 18. Documents List (from evidence)
        sections.append(self._documents_list(evidence))

        # 19. Verification
        sections.append(_VERIFICATION_TEMPLATE.format(last_para=self._para))

        # 20. Statement of Truth (if commercial)
        if is_commercial:
            sections.append(_SOT_TEMPLATE.format(last_para=self._para))

        # 21. Advocate Block
        sections.append(_ADVOCATE_BLOCK)

        return "\n\n".join(sections)

    # -----------------------------------------------------------------------
    # Helper extractors (handle Pydantic or dict)
    # -----------------------------------------------------------------------

    def _get_jurisdiction(self, intake: Dict[str, Any]) -> Dict[str, Any]:
        j = intake.get("jurisdiction", {})
        if hasattr(j, "model_dump"):
            return j.model_dump()
        return j if isinstance(j, dict) else {}

    def _get_parties(self, intake: Dict[str, Any]) -> Dict[str, Any]:
        p = intake.get("parties", {})
        if hasattr(p, "model_dump"):
            return p.model_dump()
        return p if isinstance(p, dict) else {}

    def _get_facts(self, intake: Dict[str, Any]) -> Dict[str, Any]:
        f = intake.get("facts", {})
        if hasattr(f, "model_dump"):
            return f.model_dump()
        return f if isinstance(f, dict) else {}

    def _get_evidence(self, intake: Dict[str, Any]) -> List[Dict[str, Any]]:
        ev = intake.get("evidence", [])
        if isinstance(ev, list):
            return [e.model_dump() if hasattr(e, "model_dump") else e for e in ev]
        return []

    # -----------------------------------------------------------------------
    # Section builders
    # -----------------------------------------------------------------------

    def _court_heading(self, court: Dict, jurisdiction: Dict) -> str:
        heading = court.get("heading", "IN THE COURT OF THE {court_type}")
        court_type = court.get("court", "District Court")
        heading = heading.replace("{court_type}", court_type)
        city = jurisdiction.get("city") or jurisdiction.get("place") or "{{COURT_CITY}}"
        fmt = court.get("format", "O.S. No.")
        return f"{heading}\nAT {city}\n\n{fmt} __________ / 20____"

    def _parties_block(self, parties: Dict) -> str:
        primary = parties.get("primary", {})
        if hasattr(primary, "model_dump"):
            primary = primary.model_dump()
        p_name = primary.get("name") or "{{PLAINTIFF_NAME}}"
        p_age = primary.get("age") or "{{PLAINTIFF_AGE}}"
        p_occ = primary.get("occupation") or "{{PLAINTIFF_OCCUPATION}}"
        p_addr = primary.get("address") or "{{PLAINTIFF_ADDRESS}}"

        opposite = parties.get("opposite", [])
        if opposite:
            d = opposite[0]
            if hasattr(d, "model_dump"):
                d = d.model_dump()
        else:
            d = {}
        d_name = d.get("name") or "{{DEFENDANT_NAME}}"
        d_age = d.get("age") or "{{DEFENDANT_AGE}}"
        d_occ = d.get("occupation") or "{{DEFENDANT_OCCUPATION}}"
        d_addr = d.get("address") or "{{DEFENDANT_ADDRESS}}"

        return (
            f"{p_name},\n"
            f"Aged about {p_age} years,\n"
            f"Occupation: {p_occ},\n"
            f"Residing at: {p_addr}.\n\n"
            f"                                                        ... PLAINTIFF\n\n"
            f"                    VERSUS\n\n"
            f"{d_name},\n"
            f"Aged about {d_age} years,\n"
            f"Occupation: {d_occ},\n"
            f"Residing at: {d_addr}.\n\n"
            f"                                                        ... DEFENDANT"
        )

    def _suit_title(self, lkb: Dict, court: Dict) -> str:
        display = lkb.get("display_name", "Damages for breach of agreement")
        return (
            f"SUIT FOR {display.upper()} "
            f"WITH INTEREST AND COSTS"
        )

    def _commercial_maintainability(self, facts: Dict, lkb: Dict) -> str:
        p = self._next_para()
        threshold = lkb.get("court_rules", {}).get("commercial", {}).get("threshold", 300000)
        act = lkb.get("court_rules", {}).get("commercial", {}).get("act", "Commercial Courts Act, 2015")
        return (
            f"COMMERCIAL COURT MAINTAINABILITY\n\n"
            f"{p}. The subject matter of the present suit arises out of a commercial "
            f"dispute within the meaning of Section 2(1)(c) of the {act}. "
            f"The suit is valued above the specified value of Rs. {threshold:,}/- "
            f"as prescribed under Section 12 of the {act}, "
            f"and is therefore maintainable before this Hon'ble Commercial Court."
        )

    def _jurisdiction_section(self, jurisdiction: Dict, court: Dict, is_commercial: bool) -> str:
        lines = ["JURISDICTION"]
        p = self._next_para()
        lines.append(
            f"\n{p}. The Plaintiff is a person sui juris and competent to institute "
            f"the present suit. The Defendant is also a person sui juris and can be sued."
        )

        p = self._next_para()
        city = jurisdiction.get("city") or "{{CITY}}"
        lines.append(
            f"\n{p}. This Hon'ble Court has territorial jurisdiction to try and "
            f"entertain the present suit inasmuch as the cause of action arose "
            f"within the local limits of the jurisdiction of this Hon'ble Court at {city}, "
            f"and the Defendant carries on business / resides within such territorial limits."
        )

        p = self._next_para()
        lines.append(
            f"\n{p}. This Hon'ble Court has pecuniary jurisdiction to try the present suit, "
            f"the suit being valued at Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
            f"- (Rupees {{{{TOTAL_SUIT_VALUE_WORDS}}}} Only), which is within the "
            f"pecuniary limits prescribed for this Hon'ble Court."
        )

        if is_commercial:
            lines[-1] += (
                f" This Hon'ble Court has subject matter jurisdiction to entertain "
                f"commercial disputes under the Commercial Courts Act, 2015."
            )

        return "\n".join(lines)

    def _limitation_section(self, limitation: Dict, lkb: Dict) -> str:
        article = limitation.get("article", "UNKNOWN")
        p = self._next_para()

        if article == "NONE":
            desc = limitation.get("description", "No specific limitation applies.")
            return (
                f"LIMITATION\n\n"
                f"{p}. {desc} The present suit is filed within a reasonable time "
                f"from the date of accrual of the cause of action."
            )

        if article == "UNKNOWN":
            return (
                f"LIMITATION\n\n"
                f"{p}. The present suit is within the period of limitation prescribed "
                f"under {{{{LIMITATION_ARTICLE}}}} of the Schedule to the Limitation "
                f"Act, 1963."
            )

        period = limitation.get("period", "Three years")
        description = limitation.get("description", "")
        from_date = limitation.get("from", limitation.get("accrual", ""))
        coa_type = lkb.get("coa_type", "single_event")

        text = (
            f"LIMITATION\n\n"
            f"{p}. The present suit is within the period of limitation prescribed "
            f"under Article {article} of the Schedule to the Limitation Act, 1963, "
            f"which provides a period of {period.lower()} "
        )
        if from_date:
            text += f"from {from_date.lower()}. "
        else:
            text += f"from the date of accrual of the cause of action. "

        text += "The suit is filed well within the prescribed limitation period."
        return text

    def _section_12a(self, intake: Dict, user_request: str) -> str:
        p = self._next_para()
        # Check if user mentions mediation or urgent relief
        combined = (user_request + " " + str(intake)).lower()
        mediation_done = any(kw in combined for kw in ["mediation done", "mediation was conducted", "mediation certificate", "mediation completed"])
        urgent = any(kw in combined for kw in ["urgent", "interim relief", "immediate", "irreparable"])

        if mediation_done:
            return (
                f"SECTION 12A COMPLIANCE\n\n"
                f"{p}. The Plaintiff states that in compliance with Section 12A of the "
                f"Commercial Courts Act, 2015, pre-institution mediation was conducted "
                f"through {{{{MEDIATION_AUTHORITY}}}} vide reference dated "
                f"{{{{MEDIATION_DATE}}}}. The mediation was unsuccessful and a certificate "
                f"of non-settlement was issued. A true copy is annexed as "
                f"Annexure {self._next_annexure()}."
            )
        elif urgent:
            return (
                f"SECTION 12A COMPLIANCE\n\n"
                f"{p}. The Plaintiff seeks urgent interim relief to prevent irreparable "
                f"harm. In view of the urgency, the requirement of pre-institution "
                f"mediation under Section 12A of the Commercial Courts Act, 2015, is "
                f"not a bar to institution of this suit. The Plaintiff undertakes to "
                f"comply with mediation requirements as directed by this Hon'ble Court."
            )
        else:
            return (
                f"SECTION 12A COMPLIANCE\n\n"
                f"{p}. {{{{MEDIATION_STATUS -- CONFIRM: (a) Was pre-institution mediation "
                f"conducted? If yes, provide mediation authority, date, and outcome "
                f"certificate. (b) If not, is urgent interim relief being sought? "
                f"Section 12A compliance is mandatory for commercial suits unless "
                f"urgent interim relief is sought.}}}}"
            )

    def _arbitration_disclosure(self, intake: Dict, user_request: str) -> str:
        p = self._next_para()
        combined = (user_request + " " + str(intake)).lower()
        has_arb = any(kw in combined for kw in ["arbitration", "arbitral", "tribunal"])

        if has_arb:
            return (
                f"ARBITRATION DISCLOSURE\n\n"
                f"{p}. The Plaintiff discloses that the agreement between the parties "
                f"contains an arbitration clause. However, the Plaintiff submits that "
                f"this Hon'ble Court has jurisdiction to try the present suit as the "
                f"arbitration clause is void / inoperative / incapable of being "
                f"performed within the meaning of Section 8 of the Arbitration and "
                f"Conciliation Act, 1996."
            )
        else:
            return (
                f"ARBITRATION DISCLOSURE\n\n"
                f"{p}. {{{{ARBITRATION_STATUS -- CONFIRM: Does the agreement contain "
                f"an arbitration clause? If yes, state grounds why court jurisdiction "
                f"is proper despite the clause (e.g., clause is void, inoperative, "
                f"or fraud vitiates arbitration agreement).}}}}"
            )

    def _legal_basis(self, lkb: Dict) -> str:
        lines = ["LEGAL BASIS"]
        permitted = lkb.get("permitted_doctrines", ["breach_of_contract", "damages_s73"])

        for doctrine in permitted:
            template = _DOCTRINE_TEMPLATES.get(doctrine)
            if template:
                p = self._next_para()
                lines.append(f"\n{p}. {template}")

        # Defensive points
        defensive = lkb.get("defensive_points", [])
        if defensive:
            p = self._next_para()
            defenses = []
            for dp in defensive:
                readable = dp.replace("_", " ").replace("without prejudice alternative pleading",
                    "without prejudice to the above, the Plaintiff reserves the right to urge alternative pleas")
                defenses.append(readable)
            lines.append(
                f"\n{p}. The Plaintiff further submits that {'; '.join(defenses)}."
            )

        return "\n".join(lines)

    def _cause_of_action(self, lkb: Dict, facts: Dict) -> str:
        lines = ["CAUSE OF ACTION"]
        coa_type = lkb.get("coa_type", "single_event")
        coa_date = facts.get("cause_of_action_date") or "{{COA_DATE}}"

        p = self._next_para()
        lines.append(
            f"\n{p}. The cause of action for the present suit first arose on "
            f"{coa_date} when the Defendant committed the breach / wrongful act "
            f"giving rise to the Plaintiff's right to institute the present suit."
        )

        p = self._next_para()
        lines.append(
            f"\n{p}. The cause of action further arose when the Defendant, despite "
            f"receipt of the legal notice dated {{{{NOTICE_DATE}}}}, failed and "
            f"refused to comply with the Plaintiff's demand."
        )

        if coa_type == "continuing":
            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action is a continuing one and continues to "
                f"accrue from day to day as the Defendant continues to wrongfully "
                f"retain the Plaintiff's money / property."
            )
        else:
            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action is not a continuing cause of action. "
                f"The breach consisted of a single event. However, the Plaintiff's "
                f"right to damages subsists."
            )

        return "\n".join(lines)

    def _valuation_court_fee(self, lkb: Dict, facts: Dict, state: str, court_fee: Optional[Dict]) -> str:
        p = self._next_para()
        # Get court fee statute from LKB v2.0
        cfs = lkb.get("court_fee_statute", {})
        if isinstance(cfs, dict):
            court_fee_act = cfs.get(state, cfs.get("_default", "Court Fees Act, 1870"))
        else:
            court_fee_act = "Court Fees Act, 1870"

        return (
            f"VALUATION AND COURT FEE\n\n"
            f"{p}. The suit is valued at Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
            f"- (Rupees {{{{TOTAL_SUIT_VALUE_WORDS}}}} Only) for the purposes of "
            f"jurisdiction and court fee. Appropriate court fee has been paid on "
            f"this plaint under the provisions of the {court_fee_act} as "
            f"applicable in the State of {state or '{{STATE}}'}. "
            f"The plaint is properly stamped."
        )

    def _interest_section(self, lkb: Dict) -> str:
        lines = ["INTEREST"]
        basis = lkb.get("interest_guidance", "")

        p = self._next_para()
        lines.append(
            f"\n{p}. The Plaintiff claims interest on the suit amount as follows:"
        )

        lines.append(
            f"\n    (a) Pendente lite interest at such rate as this Hon'ble Court "
            f"deems fit and just from the date of filing of this suit till the "
            f"date of judgment / decree, under Section 34 of the Code of Civil "
            f"Procedure, 1908;"
        )
        lines.append(
            f"\n    (b) Future interest at such rate as this Hon'ble Court deems "
            f"fit and just from the date of judgment / decree till the date of "
            f"realisation of the entire decretal amount."
        )

        if basis:
            lines.append(f"\n    The interest is justified because {basis}")

        return "\n".join(lines)

    def _prayer(self, lkb: Dict) -> str:
        lines = ["PRAYER"]
        lines.append(
            "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
            "that this Hon'ble Court be pleased to:"
        )

        damages = lkb.get("damages_categories", [])
        letter = ord('a')

        # Main decree
        lines.append(
            f"\n    ({chr(letter)}) Pass a decree in favour of the Plaintiff and "
            f"against the Defendant for a sum of Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
            f"- (Rupees {{{{TOTAL_SUIT_VALUE_WORDS}}}} Only) towards damages;"
        )
        letter += 1

        # Individual damage heads
        for category in damages:
            display = _DAMAGE_DISPLAY.get(category, category.replace("_", " ").title())
            lines.append(
                f"\n    ({chr(letter)}) Award Rs. {{{{{category.upper()}_AMOUNT}}}}/"
                f"- towards {display};"
            )
            letter += 1

        # Interest
        lines.append(
            f"\n    ({chr(letter)}) Award pendente lite and future interest at "
            f"such rate as this Hon'ble Court deems just under Section 34 of the "
            f"Code of Civil Procedure, 1908;"
        )
        letter += 1

        # Costs
        lines.append(
            f"\n    ({chr(letter)}) Award costs of the suit including costs of the legal notice;"
        )
        letter += 1

        # General
        lines.append(
            f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
            f"Hon'ble Court may deem fit and proper in the facts and circumstances "
            f"of the case."
        )

        return "\n".join(lines)

    def _damages_schedule(self, lkb: Dict) -> str:
        lines = ["SCHEDULE OF DAMAGES / PARTICULARS OF DAMAGES"]
        damages = lkb.get("damages_categories", [])

        lines.append(
            "\nThe Plaintiff claims the following heads of damages with "
            "computation methodology:"
        )

        for i, category in enumerate(damages, 1):
            display = _DAMAGE_DISPLAY.get(category, category.replace("_", " ").title())
            amount_key = f"{{{{{category.upper()}_AMOUNT}}}}"
            lines.append(
                f"\n{i}. {display}\n"
                f"   Amount claimed: Rs. {amount_key}/-\n"
                f"   Basis / methodology: {{{{{category.upper()}_BASIS}}}}\n"
                f"   Documentary proof: {{{{{category.upper()}_PROOF}}}}"
            )

        lines.append(
            f"\nTOTAL DAMAGES CLAIMED: Rs. {{{{TOTAL_SUIT_VALUE}}}}/-"
        )
        return "\n".join(lines)

    def _documents_list(self, evidence: List[Dict]) -> str:
        lines = ["LIST OF DOCUMENTS"]
        if not evidence:
            lines.append(
                "\nAnnexure A — {{DOCUMENT_1}}\n"
                "Annexure B — {{DOCUMENT_2}}\n"
                "Annexure C — {{DOCUMENT_3}}"
            )
            return "\n".join(lines)

        for i, ev in enumerate(evidence):
            label = chr(65 + i)  # A, B, C, ...
            desc = ev.get("description", ev.get("type", f"Document {i+1}"))
            lines.append(f"\nAnnexure {label} — {desc}")

        return "\n".join(lines)
