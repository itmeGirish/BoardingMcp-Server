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
from ..lkb.causes._family_defaults import (
    get_family,
    resolve_gap_definitions,
    resolve_section_plan,
)
from ..lkb.limitation import get_limitation_reference_details, normalize_coa_type
from ..schema_contracts import evaluate_section_condition


# ---------------------------------------------------------------------------
# Verbatim legal templates (never LLM-generated)
# ---------------------------------------------------------------------------

_VERIFICATION_TEMPLATE = """VERIFICATION

Verified at {{CITY}} on this the ____ day of __________ 20____.

I, {{PLAINTIFF_NAME}}, the Plaintiff above-named, do hereby verify that the contents of paragraphs 1 to {{LAST_PARA}} of this plaint are true and correct to my knowledge, and no material facts have been concealed therefrom, and that I have not filed any other suit, petition, or proceeding in any court or before any authority in respect of the same subject matter and cause of action.

DEPONENT

{{PLAINTIFF_NAME}}
PLAINTIFF"""

_SOT_TEMPLATE = """STATEMENT OF TRUTH

I, {{PLAINTIFF_NAME}}, the Plaintiff / authorised representative of the Plaintiff herein, do hereby state on solemn affirmation that the contents of the above plaint and the facts stated in paragraphs 1 to {{LAST_PARA}} are true to my knowledge and belief and nothing material has been concealed therefrom.

I understand that I shall be liable to proceedings under law for making a false statement.

Verified at {{CITY}} on this the ____ day of __________ 20____.

                                    {{PLAINTIFF_NAME}}
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
    "actual_loss": "Actual and direct financial loss",
    "principal_amount": "Principal amount",
    "interest_on_principal": "Interest on principal",
    "loss_of_profit_unexpired_term": "Loss of profit for the unexpired term",
    "loss_of_goodwill": "Loss of goodwill",
    "wasted_capital_investment": "Wasted capital investment",
    "loss_on_unsold_stock": "Loss on unsold stock",
    "future_business_opportunities": "Loss of future business opportunities",
    "loss_of_profit": "Loss of profit",
    "wasted_investment": "Wasted investment",
    "consequential_loss": "Consequential loss (within the contemplation of the parties at the time of contract, per Section 73 second limb / Hadley v. Baxendale)",
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
    "remoteness_hadley_v_baxendale": (
        "The Plaintiff claims only such loss as arose naturally in the usual course "
        "of things from the breach, or such loss as was within the contemplation of "
        "the parties at the time of entering into the agreement, and does not claim "
        "any remote or indirect loss."
    ),
    "damages_s74": (
        "Without prejudice to the above and in the alternative, if the agreement "
        "contains a stipulation for liquidated damages or penalty for breach, the "
        "Defendant is liable under Section 74 of the Indian Contract Act, 1872, to "
        "pay reasonable compensation not exceeding the amount so named in the contract."
    ),
    "duty_to_mitigate": (
        "The Plaintiff has taken reasonable steps to mitigate the loss caused by "
        "the Defendant's breach and claims only such damages as could not reasonably "
        "be avoided."
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
    "repudiatory_breach": (
        "The Defendant has committed a repudiatory breach by refusing to perform "
        "its obligations, entitling the Plaintiff to treat the contract as at an "
        "end and seek appropriate relief."
    ),
    "anticipatory_breach": (
        "The Defendant's conduct amounts to anticipatory breach, as the Defendant "
        "made it clear before the due date of performance that the contractual "
        "obligations would not be performed."
    ),
    "fundamental_breach": (
        "The Defendant's breach goes to the root of the contract and defeats the "
        "commercial purpose for which the parties entered into the agreement."
    ),
    "mitigation_of_damages": (
        "The Plaintiff has taken reasonable steps to mitigate the loss caused by "
        "the Defendant's breach and claims only such damages as remain after such mitigation."
    ),
}

# Legacy frozensets DELETED — replaced by get_family() from _family_defaults.py


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
        decision_ir: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build complete document skeleton with 3 LLM gaps.

        Returns plain text with markers:
          {{GENERATE:FACTS}}
          {{GENERATE:BREACH}}
          {{GENERATE:DAMAGES}}

        If decision_ir is provided, damages_categories are filtered through
        forbidden_damages from the applicability compiler.
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

        # Filter damages_categories and permitted_doctrines through decision_ir.
        # If applicability compiled allow-lists exist, treat them as authoritative.
        _decision = decision_ir or {}
        _allowed_damages = set(_decision.get("allowed_damages") or [])
        _forbidden_damages = set(_decision.get("forbidden_damages") or [])
        _allowed_doctrines = set(_decision.get("allowed_doctrines") or [])
        _forbidden_doctrines = set(_decision.get("forbidden_doctrines") or [])
        _needs_lkb_copy = bool(
            ((_allowed_damages or _forbidden_damages) and lkb.get("damages_categories"))
            or ((_allowed_doctrines or _forbidden_doctrines) and lkb.get("permitted_doctrines"))
        )
        if _needs_lkb_copy:
            lkb = dict(lkb)  # shallow copy to avoid mutating state
            if lkb.get("damages_categories"):
                damages = list(lkb["damages_categories"])
                if _allowed_damages:
                    damages = [d for d in damages if d in _allowed_damages]
                if _forbidden_damages:
                    damages = [d for d in damages if d not in _forbidden_damages]
                lkb["damages_categories"] = damages
            if lkb.get("permitted_doctrines"):
                doctrines = list(lkb["permitted_doctrines"])
                if _allowed_doctrines:
                    doctrines = [d for d in doctrines if d in _allowed_doctrines]
                if _forbidden_doctrines:
                    doctrines = [d for d in doctrines if d not in _forbidden_doctrines]
                lkb["permitted_doctrines"] = doctrines

        # v10.0: If section_plan exists (from LKB or family defaults), use data-driven path
        section_plan = resolve_section_plan(lkb, cause_type)
        if section_plan:
            gap_definitions = resolve_gap_definitions(lkb, cause_type) or []
            return self._assemble_from_plan(
                section_plan=section_plan,
                gap_definitions=gap_definitions,
                lkb=lkb,
                intake=intake,
                classify=classify,
                mandatory_provisions=mandatory_provisions,
                court_fee=court_fee,
                user_request=user_request,
                decision_ir=decision_ir,
            )

        # Legacy path removed — all cause types now routed through v10.0 data-driven path.
        # If we reach here, it means the cause type has no family mapping.
        # Fall back to a minimal skeleton with 3 generic LLM gaps.
        raise ValueError(
            f"No section_plan found for cause_type={cause_type!r}. "
            f"Add it to _FAMILY_MAP in _family_defaults.py."
        )

    # -----------------------------------------------------------------------
    # v10.0 — Data-driven assembly from section_plan
    # -----------------------------------------------------------------------

    def _assemble_from_plan(
        self,
        section_plan: List[Dict],
        gap_definitions: List[Dict],
        lkb: Dict[str, Any],
        intake: Dict[str, Any],
        classify: Dict[str, Any],
        mandatory_provisions: Dict[str, Any],
        court_fee: Optional[Dict[str, Any]],
        user_request: str,
        decision_ir: Optional[Dict[str, Any]],
    ) -> str:
        """Generic loop — reads section_plan from LKB. Zero if/elif per cause type."""
        self._para = 0
        self._annexure = 0

        cause_type = classify.get("cause_type", "")
        detected_court = lkb.get(
            "detected_court",
            lkb.get("court_rules", {}).get("default", {}),
        )
        is_commercial = "commercial" in detected_court.get("court", "").lower()

        jurisdiction = self._get_jurisdiction(intake)
        parties = self._get_parties(intake)
        facts_obj = self._get_facts(intake)
        evidence = self._get_evidence(intake)
        limitation = (mandatory_provisions or {}).get("limitation", {})
        if get_limitation_reference_details(limitation).get("kind") in {
            "unknown", "not_applicable",
        }:
            limitation = lkb.get("limitation", {}) or limitation
        state = jurisdiction.get("state", "")

        # Context dict available to all builders
        ctx = {
            "lkb": lkb,
            "intake": intake,
            "classify": classify,
            "cause_type": cause_type,
            "detected_court": detected_court,
            "is_commercial": is_commercial,
            "jurisdiction": jurisdiction,
            "parties": parties,
            "facts_obj": facts_obj,
            "evidence": evidence,
            "limitation": limitation,
            "state": state,
            "decision_ir": decision_ir or {},
            "court_fee": court_fee,
            "user_request": user_request,
            "mandatory_provisions": mandatory_provisions or {},
        }

        # Builder registry — maps builder names to existing methods
        builders = {
            "court_heading": lambda c: self._court_heading(c["detected_court"], c["jurisdiction"]),
            "parties": lambda c: self._parties_block(c["parties"]),
            "suit_title": lambda c: self._suit_title(c["lkb"], c["detected_court"], c["cause_type"]),
            "showeth": lambda c: "MOST RESPECTFULLY SHOWETH:",
            "commercial_maintainability": lambda c: self._commercial_maintainability(c["facts_obj"], c["lkb"]),
            "jurisdiction": lambda c: self._jurisdiction_section(
                c["jurisdiction"], c["detected_court"], c["is_commercial"], c["cause_type"], c["facts_obj"]),
            "limitation": lambda c: self._limitation_section(c["limitation"], c["lkb"]),
            "section_12a": lambda c: self._section_12a(c["intake"], c["user_request"]),
            "legal_basis": lambda c: self._legal_basis(
                c["lkb"], c["cause_type"], c["facts_obj"], c["decision_ir"]),
            "cause_of_action": lambda c: self._cause_of_action(
                c["lkb"], c["facts_obj"], c["cause_type"], c["decision_ir"]),
            "valuation": lambda c: self._valuation_court_fee(
                c["lkb"], c["facts_obj"], c["state"], c["court_fee"], c["cause_type"]),
            "interest": lambda c: self._interest_section(c["lkb"], c["cause_type"]),
            "prayer": lambda c: self._prayer(c["lkb"], c["cause_type"]),
            "damages_schedule": lambda c: self._damages_schedule(c["lkb"], c["cause_type"]),
            "schedule_of_property": lambda c: self._schedule_of_property(c["facts_obj"]),
            "schedule_of_easement": lambda c: self._schedule_of_easement(c["facts_obj"]),
            "documents_list": lambda c: self._documents_list(c["evidence"], cause_type=c["cause_type"]),
            "verification": lambda c: _VERIFICATION_TEMPLATE,
            "statement_of_truth": lambda c: _SOT_TEMPLATE,
            "advocate_block": lambda c: _ADVOCATE_BLOCK,
        }

        parts: List[str] = []
        for section in section_plan:
            # Check condition (if any)
            if "condition" in section:
                if not self._evaluate_condition(section["condition"], ctx):
                    continue

            source = section.get("source", "")

            if source == "engine":
                builder_name = section.get("builder", "")
                builder = builders.get(builder_name)
                if builder:
                    text = builder(ctx)
                    if text:  # skip empty sections (e.g. interest returns "")
                        parts.append(text)

            elif source == "llm_gap":
                gap_id = section.get("gap_id", "UNKNOWN")
                parts.append(f"{{{{GENERATE:{gap_id}|start_para={self._para + 1}}}}}")

        return "\n\n".join(parts)

    def _evaluate_condition(self, condition: str, ctx: Dict[str, Any]) -> bool:
        """Evaluate a section condition against the current context."""
        doc_type = str(ctx.get("classify", {}).get("doc_type", ""))
        return evaluate_section_condition(condition, doc_type=doc_type, context=ctx)

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

    def _is_possession_cause(self, cause_type: str) -> bool:
        return get_family(cause_type) == "possession"

    def _is_injunction_cause(self, cause_type: str) -> bool:
        return get_family(cause_type) == "injunction"

    def _is_contract_cause(self, cause_type: str) -> bool:
        return get_family(cause_type) == "contract"

    def _is_money_cause(self, cause_type: str) -> bool:
        return get_family(cause_type) == "money"

    def _is_accounts_cause(self, cause_type: str) -> bool:
        return get_family(cause_type) == "accounts"

    def _is_partition_cause(self, cause_type: str) -> bool:
        return get_family(cause_type) == "partition"

    def _is_easement_cause(self, cause_type: str) -> bool:
        return (cause_type or "").strip() == "easement"

    def _is_tenancy_cause(self, cause_type: str) -> bool:
        return get_family(cause_type) == "tenancy"

    def _is_tort_cause(self, cause_type: str) -> bool:
        return get_family(cause_type) == "tort"

    def _is_immovable_injunction(self, cause_type: str, facts: Dict[str, Any]) -> bool:
        if not self._is_injunction_cause(cause_type):
            return False

        property_keys = (
            "property_address",
            "suit_property_address",
            "property_description",
            "schedule_property",
            "property_location",
            "land_survey_number",
            "survey_number",
            "survey_no",
            "land_area",
            "extent",
            "land_village",
            "village",
        )
        for key in property_keys:
            value = facts.get(key)
            if isinstance(value, str) and value.strip():
                return True

        summary_blob = " ".join(
            str(value)
            for value in (
                facts.get("summary", ""),
                facts.get("property_description", ""),
                facts.get("property_location", ""),
            )
            if value
        ).lower()
        return any(
            token in summary_blob
            for token in (
                "agricultural land",
                "survey no",
                "survey number",
                "suit property",
                "immovable property",
                "revenue record",
                "mutation",
                "pahani",
                "rtc",
                "adangal",
            )
        )

    def _fact_value(self, facts: Dict[str, Any], keys: List[str], default: str) -> str:
        for key in keys:
            value = facts.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return default

    def _property_reference(self, facts: Dict[str, Any], jurisdiction: Dict[str, Any]) -> str:
        return self._fact_value(
            facts,
            [
                "property_address",
                "suit_property_address",
                "property_description",
                "schedule_property",
                "property_location",
            ],
            jurisdiction.get("city") or "{{SUIT_PROPERTY_ADDRESS}}",
        )

    def _first_sections_for_act(self, acts: List[Dict[str, Any]], act_name: str) -> str:
        for act_info in acts:
            if act_info.get("act", "").strip() == act_name:
                sections = [section for section in act_info.get("sections", []) if section][:5]
                return ", ".join(sections)
        return ""

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

    def _suit_title(self, lkb: Dict, court: Dict, cause_type: str = "") -> str:
        display = lkb.get("display_name", "Damages for breach of agreement")
        display = re.sub(r"^\s*suit\s+for\s+", "", display, flags=re.IGNORECASE).strip()
        if self._is_possession_cause(cause_type):
            reliefs = set(lkb.get("required_reliefs") or [])
            if {
                "mesne_profits_inquiry_order_xx_r12",
                "mesne_profits_decree",
                "inquiry_under_order_xx_rule_12",
            } & reliefs:
                suffix = " WITH MESNE PROFITS AND COSTS"
            else:
                suffix = " WITH COSTS"
            return f"SUIT FOR {display.upper()}{suffix}"
        if self._is_injunction_cause(cause_type):
            return f"SUIT FOR {display.upper()} WITH COSTS"
        if self._is_easement_cause(cause_type):
            return "SUIT FOR DECLARATION OF EASEMENTARY RIGHT AND INJUNCTION WITH COSTS"
        if self._is_partition_cause(cause_type):
            if cause_type == "partition":
                return "SUIT FOR PARTITION AND SEPARATE POSSESSION WITH COSTS"
            if cause_type == "declaration_title":
                return "SUIT FOR DECLARATION OF TITLE WITH CONSEQUENTIAL RELIEF AND COSTS"
            if cause_type in ("mortgage_redemption", "mortgage_foreclosure", "mortgage_sale"):
                return f"SUIT FOR {display.upper()} WITH COSTS"
            return f"SUIT FOR {display.upper()} WITH COSTS"
        if self._is_tenancy_cause(cause_type):
            if cause_type == "eviction":
                return "SUIT FOR EVICTION AND RECOVERY OF POSSESSION WITH ARREARS OF RENT AND COSTS"
            if cause_type == "arrears_of_rent":
                return "SUIT FOR RECOVERY OF ARREARS OF RENT WITH INTEREST AND COSTS"
            if cause_type == "mesne_profits_post_tenancy":
                return "SUIT FOR MESNE PROFITS WITH INTEREST AND COSTS"
            return f"SUIT FOR {display.upper()} WITH COSTS"
        if self._is_tort_cause(cause_type):
            if cause_type == "defamation":
                return "SUIT FOR DAMAGES FOR DEFAMATION WITH PERMANENT INJUNCTION AND COSTS"
            if cause_type in ("negligence_personal_injury", "negligence_property_damage"):
                return "SUIT FOR DAMAGES FOR NEGLIGENCE WITH INTEREST AND COSTS"
            if cause_type == "nuisance":
                return "SUIT FOR PERMANENT INJUNCTION AND DAMAGES FOR NUISANCE WITH COSTS"
            return f"SUIT FOR {display.upper()} WITH INTEREST AND COSTS"
        if self._is_contract_cause(cause_type):
            if cause_type == "specific_performance":
                return "SUIT FOR SPECIFIC PERFORMANCE OF CONTRACT WITH COSTS"
            if cause_type == "rescission_contract":
                return "SUIT FOR RESCISSION OF CONTRACT AND REFUND WITH INTEREST AND COSTS"
            if cause_type == "breach_of_contract":
                return (
                    "SUIT FOR RECOVERY OF DAMAGES FOR BREACH OF CONTRACT "
                    "UNDER SECTION 73 OF THE INDIAN CONTRACT ACT, 1872"
                )
            if cause_type in ("breach_dealership_franchise",
                              "breach_employment", "breach_construction",
                              "supply_service_contract"):
                return "SUIT FOR DAMAGES FOR BREACH OF CONTRACT"
            return f"SUIT FOR {display.upper()}"
        if self._is_accounts_cause(cause_type):
            if cause_type == "accounts_stated":
                return "SUIT ON ACCOUNTS STATED IN WRITING WITH INTEREST AND COSTS"
            return "SUIT FOR RENDITION OF ACCOUNTS AND FOR PAYMENT OF AMOUNT FOUND DUE"
        if self._is_money_cause(cause_type):
            if cause_type == "recovery_specific_movable":
                return "SUIT FOR RECOVERY OF SPECIFIC MOVABLE PROPERTY WITH COSTS"
            return f"SUIT FOR {display.upper()} WITH INTEREST AND COSTS"
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

    def _jurisdiction_section(
        self,
        jurisdiction: Dict,
        court: Dict,
        is_commercial: bool,
        cause_type: str = "",
        facts: Optional[Dict[str, Any]] = None,
    ) -> str:
        lines = ["JURISDICTION"]
        if not self._is_contract_cause(cause_type):
            p = self._next_para()
            lines.append(
                f"\n{p}. The Plaintiff is a person sui juris and competent to institute "
                f"the present suit. The Defendant is also a person sui juris and can be sued."
            )

        p = self._next_para()
        city = jurisdiction.get("city") or "{{CITY}}"
        _needs_situs = (
            self._is_possession_cause(cause_type)
            or self._is_immovable_injunction(cause_type, facts or {})
            or self._is_partition_cause(cause_type)
            or self._is_tenancy_cause(cause_type)
        )
        if _needs_situs:
            property_ref = self._property_reference(facts or {}, jurisdiction)
            lines.append(
                f"\n{p}. This Hon'ble Court has territorial jurisdiction to try and "
                f"entertain the present suit under Section 16 of the Code of Civil "
                f"Procedure, 1908, inasmuch as the suit immovable property at {property_ref} "
                f"is situated within the local limits of this Hon'ble Court at {city}."
            )
        elif self._is_contract_cause(cause_type):
            contract_place = self._fact_value(
                facts or {},
                ["contract_place", "place_of_contract", "agreement_place", "place_of_agreement"],
                "{{PLACE_OF_CONTRACT}}",
            )
            performance_place = self._fact_value(
                facts or {},
                ["place_of_performance", "performance_place", "performance_location"],
                "{{PLACE_OF_PERFORMANCE}}",
            )
            breach_place = self._fact_value(
                facts or {},
                ["place_of_breach", "breach_place", "breach_location"],
                "{{PLACE_OF_BREACH}}",
            )
            lines.append(
                f"\n{p}. This Court has territorial jurisdiction under Section 20 CPC, "
                f"as the agreement was entered into "
                f"at {contract_place}, was to be performed at {performance_place}, and the "
                f"breach occurred at {breach_place}; in any event, the Defendant resides or "
                f"carries on business within the local limits of this Court at {city}."
            )
        else:
            lines.append(
                f"\n{p}. This Hon'ble Court has territorial jurisdiction to try and "
                f"entertain the present suit inasmuch as the cause of action arose "
                f"within the local limits of the jurisdiction of this Hon'ble Court at {city}, "
                f"and the Defendant carries on business / resides within such territorial limits."
            )

        p = self._next_para()
        lines.append(
            f"\n{p}. This Court has pecuniary jurisdiction to try the present suit, "
            f"the suit being valued at Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
            f"- (Rupees {{{{TOTAL_SUIT_VALUE_WORDS}}}} Only), which is within the "
            f"pecuniary limits prescribed for this Court."
        )

        if is_commercial:
            lines[-1] += (
                f" This Hon'ble Court has subject matter jurisdiction to entertain "
                f"commercial disputes under the Commercial Courts Act, 2015."
            )

        return "\n".join(lines)

    def _documents_list(self, evidence: List[Dict], cause_type: str = "") -> str:
        lines = ["LIST OF DOCUMENTS"]
        if not evidence:
            if self._is_contract_cause(cause_type):
                # Keep contract annexures — gap-fill prompt references P-1/P-2 labels
                lines.append(
                    "\nAnnexure P-1 - Contract / Agreement dated {{DATE_OF_CONTRACT}}\n"
                    "Annexure P-2 - Legal notice dated {{NOTICE_DATE}} and proof of service\n"
                    "Annexure P-3 - Statement / computation of damages with supporting documents"
                )
            else:
                # Single placeholder — do NOT fabricate annexure labels
                lines.append("\n{{DOCUMENTS_TO_BE_ANNEXED}}")
            return "\n".join(lines)

        for i, ev in enumerate(evidence):
            label = chr(65 + i)  # A, B, C, ...
            desc = ev.get("description", ev.get("type", f"Document {i+1}"))
            lines.append(f"\nAnnexure {label} — {desc}")

        return "\n".join(lines)

    def _limitation_section(self, limitation: Dict, lkb: Dict) -> str:
        details = get_limitation_reference_details(limitation)
        article = limitation.get("article", "UNKNOWN")
        p = self._next_para()
        cause_type = lkb.get("code") or ""

        if details["kind"] == "none":
            desc = limitation.get("description", "No specific limitation applies.")
            return (
                f"LIMITATION\n\n"
                f"{p}. {desc} The present suit is filed within a reasonable time "
                f"from the date of accrual of the cause of action."
            )

        if details["kind"] == "not_applicable":
            desc = limitation.get("description", "The proceeding is governed by a special statutory limitation rule.")
            return (
                f"LIMITATION\n\n"
                f"{p}. {desc} The proceeding is filed within the period prescribed by the governing statute / forum rule."
            )

        if article in ("UNKNOWN", "RELATIONSHIP_DEPENDENT") and not details["citation"]:
            desc = limitation.get("description", "")
            if article == "RELATIONSHIP_DEPENDENT" or desc:
                # Hedge cleanly with the LKB description
                hedge = desc if desc else (
                    "The applicable limitation article depends on the underlying "
                    "relationship and must be verified before filing."
                )
                return (
                    f"LIMITATION\n\n"
                    f"{p}. {hedge} The present suit is filed within the period "
                    f"of limitation prescribed under the applicable article of "
                    f"the Schedule to the Limitation Act, 1963."
                )
            return (
                f"LIMITATION\n\n"
                f"{p}. The present suit is within the period of limitation prescribed "
                f"under {{{{LIMITATION_ARTICLE}}}} of the Schedule to the Limitation "
                f"Act, 1963."
            )

        period = limitation.get("period", "Three years")
        description = limitation.get("description", "")
        from_date = limitation.get("from", limitation.get("accrual", ""))
        coa_type = lkb.get("coa_type") or None

        if self._is_contract_cause(cause_type) and normalize_coa_type(coa_type) != "continuing":
            return (
                f"LIMITATION\n\n"
                f"{p}. The suit is within limitation under {details['citation'] or '{{LIMITATION_REFERENCE}}'}, "
                f"the period prescribed being {period.lower()} from the date on which the contract "
                f"was broken. The suit is filed well within the prescribed period."
            )

        text = (
            f"LIMITATION\n\n"
            f"{p}. The present suit is within the period of limitation prescribed "
            f"under {details['citation'] or '{{LIMITATION_REFERENCE}}'}, "
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
        combined = (user_request + " " + str(intake)).lower()
        has_arb = any(kw in combined for kw in ["arbitration", "arbitral", "tribunal"])

        if has_arb:
            # User/intake mentions arbitration — must address it
            p = self._next_para()
            return (
                f"ARBITRATION DISCLOSURE\n\n"
                f"{p}. {{{{ARBITRATION_STATUS -- The agreement mentions an arbitration "
                f"clause. State whether the clause is (a) void, (b) inoperative, or "
                f"(c) incapable of being performed under Section 8 of the Arbitration "
                f"and Conciliation Act, 1996, and why this Hon'ble Court has "
                f"jurisdiction despite the clause.}}}}"
            )
        else:
            # No arbitration mentioned — skip the section entirely.
            # Do NOT assert arbitration clause exists or doesn't exist
            # without factual basis (INVENTED_FACT risk).
            return ""

    def _legal_basis(self, lkb: Dict, cause_type: str = "", facts: Optional[Dict[str, Any]] = None, decision_ir: Optional[Dict[str, Any]] = None) -> str:
        if self._is_possession_cause(cause_type):
            lines = ["LEGAL BASIS"]

            p = self._next_para()
            lines.append(
                f"\n{p}. The Plaintiff is entitled to recover possession of the suit "
                f"immovable property under Section 5 of the Specific Relief Act, 1963, "
                f"being a person entitled to immediate possession whose right is being "
                f"wrongfully withheld by the Defendant."
            )

            p = self._next_para()
            lines.append(
                f"\n{p}. The present suit is maintainable before this Hon'ble Court "
                f"under Section 9 read with Section 16 of the Code of Civil Procedure, "
                f"1908, and the Plaintiff is entitled to consequential relief for mesne "
                f"profits and inquiry under Order XX Rule 12 of the Code of Civil Procedure, 1908."
            )

            alt_acts = lkb.get("alternative_acts", []) or []
            if cause_type == "recovery_of_possession_tenant":
                sections_text = self._first_sections_for_act(alt_acts, "Transfer of Property Act, 1882") or "Section 106, Section 111(a)"
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant's occupation was that of a tenant / lessee, "
                    f"and the tenancy stood determined in accordance with {sections_text} "
                    f"of the Transfer of Property Act, 1882. Upon such determination, "
                    f"the Defendant became liable to hand over vacant possession."
                )
            elif cause_type == "recovery_of_possession_licensee":
                sections_text = self._first_sections_for_act(alt_acts, "Indian Easements Act, 1882") or "Section 52, Section 60, Section 61, Section 62, Section 63"
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant's occupation was only by way of licence / "
                    f"permissive use within the meaning of {sections_text} of the Indian "
                    f"Easements Act, 1882. The licence having been revoked / come to an end, "
                    f"the Defendant has no right to continue in possession of the suit property."
                )
            elif cause_type == "recovery_of_possession_co_owner":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff claims possession on the basis of title and "
                    f"co-ownership, coupled with ouster / exclusion by the Defendant, and "
                    f"is therefore entitled to seek recovery of possession together with "
                    f"consequential mesne profits according to law."
                )
            else:
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant is in unauthorized occupation without any "
                    f"subsisting right, title, or interest, and is liable to restore "
                    f"possession of the suit property to the Plaintiff."
                )

            return "\n".join(lines)

        if self._is_injunction_cause(cause_type):
            lines = ["LEGAL BASIS"]
            property_based = self._is_immovable_injunction(cause_type, facts or {})

            if cause_type == "mandatory_injunction":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to seek a mandatory injunction under "
                    f"Sections 37 and 39 of the Specific Relief Act, 1963, to compel "
                    f"restoration / removal of the wrongful state of affairs created or "
                    f"continued by the Defendant."
                )
            else:
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to seek a decree of perpetual / "
                    f"permanent injunction under Sections 36 and 37 read with Section 38 of the Specific "
                    f"Relief Act, 1963, as the Defendant threatens to invade the Plaintiff's "
                    f"peaceful possession, enjoyment, and lawful rights in respect of the "
                    f"suit property / subject matter of the suit."
                )

            p = self._next_para()
            if property_based:
                lines.append(
                    f"\n{p}. The present suit is maintainable under Section 9 read with "
                    f"Section 16 of the Code of Civil Procedure, 1908, the suit being in "
                    f"respect of rights relating to immovable property situated within the "
                    f"territorial jurisdiction of this Hon'ble Court."
                )
            else:
                lines.append(
                    f"\n{p}. The present suit is maintainable under Section 9 of the Code "
                    f"of Civil Procedure, 1908, and this Hon'ble Court has jurisdiction on "
                    f"the pleaded territorial and pecuniary facts."
                )

            p = self._next_para()
            lines.append(
                f"\n{p}. Monetary compensation is not an equally efficacious remedy in the "
                f"facts pleaded, and the relief of injunction is necessary to prevent "
                f"continued interference, irreparable injury, and multiplicity of proceedings."
            )
            return "\n".join(lines)

        # ── Contract / Commercial ──────────────────────────────────────
        if self._is_contract_cause(cause_type):
            lines = ["LEGAL BASIS"]
            permitted = lkb.get("permitted_doctrines") or []

            if cause_type == "specific_performance":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to a decree of specific performance "
                    f"of the agreement under Sections 10 and 14 of the Specific Relief Act, 1963, "
                    f"the subject matter being such that the grant of compensation in money "
                    f"would not afford adequate relief."
                )
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff has been ready and willing to perform his/her part "
                    f"of the agreement at all material times within the meaning of Section 16(c) "
                    f"of the Specific Relief Act, 1963."
                )
            elif cause_type == "rescission_contract":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to have the agreement rescinded under "
                    f"Section 27 of the Specific Relief Act, 1963, the Defendant "
                    f"having committed breach of the essential terms thereof."
                )
            else:
                if "damages_s73" not in permitted:
                    p = self._next_para()
                    lines.append(
                        f"\n{p}. The Defendant has committed breach of the agreement by remaining "
                        f"in default of the obligations undertaken therein, thereby entitling the "
                        f"Plaintiff to claim damages under Section 73 of the Indian Contract Act, 1872."
                    )

            # Doctrine-based paragraphs from LKB
            for doctrine in permitted:
                template = _DOCTRINE_TEMPLATES.get(doctrine)
                if template:
                    p = self._next_para()
                    lines.append(f"\n{p}. {template}")
            return "\n".join(lines)

        # ── Accounts / Relationship ──────────────────────────────────
        if self._is_accounts_cause(cause_type):
            lines = ["LEGAL BASIS"]

            p = self._next_para()
            lines.append(
                f"\n{p}. The Defendant, being in a fiduciary position / agent / "
                f"partner / manager of the joint business, was entrusted with "
                f"the management of funds, property, and/or business affairs on "
                f"behalf of the Plaintiff and is bound to render true and faithful "
                f"accounts to the Plaintiff."
            )

            p = self._next_para()
            lines.append(
                f"\n{p}. The Defendant has failed and neglected to render accounts "
                f"despite repeated demands. The Plaintiff is entitled to a "
                f"preliminary decree directing the Defendant to render true and "
                f"faithful accounts of all transactions and dealings under Order XX "
                f"Rule 16 of the Code of Civil Procedure, 1908, and thereafter to a "
                f"final decree for payment of such sum as may be found due to the "
                f"Plaintiff upon rendition of accounts."
            )

            p = self._next_para()
            lines.append(
                f"\n{p}. The Plaintiff is further entitled to pendente lite interest "
                f"under Order XX Rule 11 of the Code of Civil Procedure, 1908, and "
                f"post-decree interest under Section 34 CPC, on the amount found due."
            )

            return "\n".join(lines)

        # ── Money / Debt ───────────────────────────────────────────────
        if self._is_money_cause(cause_type):
            lines = ["LEGAL BASIS"]

            if cause_type in ("money_recovery_loan", "suit_on_bond"):
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant borrowed / received a sum of "
                    f"Rs. {{{{PRINCIPAL_AMOUNT}}}}/"
                    f"- from the Plaintiff and is liable to repay the same with interest "
                    f"under Section 69 read with Section 73 of the Indian Contract Act, 1872."
                )
            elif cause_type == "money_recovery_goods":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant is liable to pay the price of the goods sold and "
                    f"delivered under the Sale of Goods Act, 1930, read with Section 73 of the "
                    f"Indian Contract Act, 1872."
                )
            elif cause_type == "summary_suit_instrument":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to summary judgment under Order XXXVII "
                    f"of the Code of Civil Procedure, 1908, the suit being founded on a "
                    f"bill of exchange / promissory note / written contract for a liquidated amount."
                )
            elif cause_type == "quantum_meruit":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff performed work / rendered services at the request "
                    f"of the Defendant without a fixed price. The Plaintiff is entitled to "
                    f"reasonable remuneration on quantum meruit under Section 70 of the "
                    f"Indian Contract Act, 1872."
                )
            elif cause_type == "guarantee_recovery":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant, being the surety / guarantor under the guarantee "
                    f"agreement, is liable to pay the guaranteed sum upon default by the "
                    f"principal debtor, under Sections 126-147 of the Indian Contract Act, 1872."
                )
            elif cause_type == "indemnity_recovery":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to be indemnified by the Defendant "
                    f"under the contract of indemnity as provided by Sections 124-125 of the "
                    f"Indian Contract Act, 1872."
                )
            elif cause_type == "recovery_specific_movable":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to recovery of the specific movable "
                    f"property wrongfully detained by the Defendant, under Sections 7 and 8 "
                    f"of the Specific Relief Act, 1963."
                )
            else:
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant is liable to pay the claimed amount to the Plaintiff "
                    f"under the Indian Contract Act, 1872, and the relevant statutory provisions."
                )

            p = self._next_para()
            lines.append(
                f"\n{p}. The present suit is maintainable under Section 9 of the Code of "
                f"Civil Procedure, 1908."
            )
            return "\n".join(lines)

        # ── Partition / Immovable Property ─────────────────────────────
        if self._is_partition_cause(cause_type):
            lines = ["LEGAL BASIS"]

            if cause_type == "partition":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff, being a co-owner / coparcener of the suit property, "
                    f"is entitled to claim partition and separate possession of his/her share "
                    f"in the joint / coparcenary property under Section 4 of the Partition Act, 1893, "
                    f"read with Section 3 of the Hindu Succession Act, 1956 (as amended in 2005), "
                    f"where applicable."
                )
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to a preliminary decree declaring the "
                    f"rights and shares of the parties and a final decree for partition by metes "
                    f"and bounds under Order XX Rule 18 of the Code of Civil Procedure, 1908."
                )
            elif cause_type == "declaration_title":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to a declaration of title under "
                    f"Section 34 of the Specific Relief Act, 1963, the Plaintiff being the "
                    f"lawful owner and having valid title to the suit property."
                )
            elif cause_type == "easement":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff has acquired an easementary right under "
                    f"Section 15 of the Indian Easements Act, 1882 by peaceable, open, "
                    f"continuous, and uninterrupted enjoyment of the pathway as of right "
                    f"for a period exceeding twenty years."
                )
                p = self._next_para()
                lines.append(
                    f"\n{p}. Upon disturbance / obstruction of the said easement, the "
                    f"Plaintiff is entitled to sue for declaration and protection of the "
                    f"right under Sections 33 and 35 of the Indian Easements Act, 1882."
                )
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to a declaration of the easementary "
                    f"right under Section 34 of the Specific Relief Act, 1963, and to "
                    f"permanent and mandatory injunction under Sections 38 and 39 of the "
                    f"Specific Relief Act, 1963, to remove and restrain the obstruction."
                )
            elif cause_type in ("mortgage_redemption", "mortgage_foreclosure", "mortgage_sale"):
                p = self._next_para()
                lines.append(
                    f"\n{p}. The present suit is governed by the Transfer of Property Act, 1882, "
                    f"and the Plaintiff is entitled to the relief of {cause_type.replace('_', ' ')} "
                    f"under the provisions thereof."
                )
            elif cause_type == "adverse_possession_claim":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff has been in open, continuous, hostile, and uninterrupted "
                    f"possession of the suit property for a period exceeding 12 years, with "
                    f"animus possidendi, and has thereby perfected title by adverse possession "
                    f"under Article 65 of the Limitation Act, 1963."
                )
            elif cause_type == "mesne_profits":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to claim mesne profits for the period "
                    f"of the Defendant's wrongful occupation under Section 2(12) read with "
                    f"Order XX Rule 12 of the Code of Civil Procedure, 1908."
                )
            else:
                primary_acts = lkb.get("primary_acts", []) or []
                for act_info in primary_acts[:2]:
                    act_name = act_info.get("act", "").strip()
                    if not act_name:
                        continue
                    sections = [s for s in act_info.get("sections", []) if s][:4]
                    sections_text = ", ".join(sections)
                    sentence = f"The present cause is governed by {act_name}"
                    if sections_text:
                        sentence += f", including {sections_text}"
                    sentence += "."
                    p = self._next_para()
                    lines.append(f"\n{p}. {sentence}")

            p = self._next_para()
            lines.append(
                f"\n{p}. The present suit is maintainable under Section 9 read with Section 16 "
                f"of the Code of Civil Procedure, 1908, the suit property being situated "
                f"within the territorial jurisdiction of this Hon'ble Court."
            )
            return "\n".join(lines)

        # ── Tenancy / Rent ─────────────────────────────────────────────
        if self._is_tenancy_cause(cause_type):
            lines = ["LEGAL BASIS"]

            if cause_type == "eviction":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant was inducted as tenant / lessee of the suit premises "
                    f"and the tenancy / lease stood lawfully determined by service of a valid "
                    f"notice under Section 106 of the Transfer of Property Act, 1882."
                )
                p = self._next_para()
                lines.append(
                    f"\n{p}. Upon determination of the tenancy, the Defendant has no right "
                    f"to continue in occupation and is liable to be evicted and to deliver "
                    f"vacant and peaceful possession of the suit premises to the Plaintiff."
                )
                p = self._next_para()
                lines.append(
                    f"\n{p}. {{{{RENT_ACT_STATUS -- CONFIRM: Are the suit premises exempt from "
                    f"the applicable State Rent Control Act? If yes, state basis of exemption "
                    f"(e.g., premises built after cut-off date, commercial premises above "
                    f"threshold rent, vacancy after specified date). If no, file before Rent "
                    f"Controller instead.}}}}"
                )
            elif cause_type == "arrears_of_rent":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant, as tenant of the suit premises, is liable to pay "
                    f"rent at the agreed rate but has committed default in payment of rent "
                    f"for the period from {{{{ARREARS_FROM_DATE}}}} to {{{{ARREARS_TO_DATE}}}}."
                )
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Plaintiff is entitled to recover the arrears of rent together "
                    f"with interest thereon under the Transfer of Property Act, 1882."
                )
            elif cause_type == "mesne_profits_post_tenancy":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The tenancy of the Defendant having been lawfully determined, "
                    f"the Defendant's continued occupation is wrongful, and the Plaintiff "
                    f"is entitled to mesne profits under Section 2(12) read with Order XX "
                    f"Rule 12 of the Code of Civil Procedure, 1908."
                )

            p = self._next_para()
            lines.append(
                f"\n{p}. The present suit is maintainable under Section 9 read with Section 16 "
                f"of the Code of Civil Procedure, 1908."
            )
            return "\n".join(lines)

        # ── Tort / Civil Wrong ─────────────────────────────────────────
        if self._is_tort_cause(cause_type):
            lines = ["LEGAL BASIS"]

            if cause_type == "defamation":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant has published / uttered defamatory matter concerning "
                    f"the Plaintiff, thereby causing injury to the Plaintiff's reputation, "
                    f"standing, and goodwill. The Plaintiff is entitled to damages for defamation "
                    f"and a permanent injunction restraining further publication."
                )
            elif cause_type in ("negligence_personal_injury", "negligence_property_damage"):
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant owed a duty of care to the Plaintiff and breached "
                    f"that duty by negligent acts / omissions, thereby directly causing "
                    f"{'personal injury' if 'personal' in cause_type else 'property damage'} "
                    f"and loss to the Plaintiff. The Plaintiff is entitled to damages for "
                    f"such negligence."
                )
            elif cause_type == "nuisance":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant's acts constitute nuisance, causing unreasonable "
                    f"interference with the Plaintiff's use and enjoyment of the property / "
                    f"rights. The Plaintiff is entitled to a permanent injunction to abate the "
                    f"nuisance and damages for the loss suffered."
                )
            elif cause_type == "malicious_prosecution_civil":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant maliciously and without reasonable or probable cause "
                    f"initiated criminal / civil proceedings against the Plaintiff, which "
                    f"terminated in the Plaintiff's favour. The Plaintiff is entitled to "
                    f"damages for malicious prosecution."
                )
            elif cause_type == "false_imprisonment_civil":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant wrongfully and without lawful authority confined / "
                    f"restrained the Plaintiff's liberty, constituting false imprisonment. "
                    f"The Plaintiff is entitled to damages."
                )
            elif cause_type == "conversion":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant wrongfully converted the Plaintiff's goods / movable "
                    f"property to his own use, thereby depriving the Plaintiff of the same. "
                    f"The Plaintiff is entitled to the value of the converted goods and "
                    f"consequential damages."
                )
            elif cause_type == "fraud_misrepresentation_standalone":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The Defendant, by fraudulent misrepresentation / active concealment "
                    f"of material facts, induced the Plaintiff to act to his/her detriment, "
                    f"entitling the Plaintiff to damages under Section 19 of the Indian Contract "
                    f"Act, 1872 and the general law of torts."
                )
            else:
                # Generic tort
                primary_acts = lkb.get("primary_acts", []) or []
                if primary_acts:
                    for act_info in primary_acts[:2]:
                        act_name = act_info.get("act", "").strip()
                        if not act_name:
                            continue
                        sections = [s for s in act_info.get("sections", []) if s][:4]
                        sections_text = ", ".join(sections)
                        if act_name == "Law of Torts (Common Law)":
                            sentence = "The present cause is governed by the general law of torts recognised by Indian courts"
                        else:
                            sentence = f"The present cause is governed by {act_name}"
                        if sections_text:
                            sentence += f", including {sections_text}"
                        sentence += "."
                        p = self._next_para()
                        lines.append(f"\n{p}. {sentence}")
                else:
                    p = self._next_para()
                    lines.append(
                        f"\n{p}. The Defendant's wrongful act constitutes a tort under the "
                        f"general law of torts recognised by Indian courts, entitling the "
                        f"Plaintiff to damages."
                    )

            p = self._next_para()
            lines.append(
                f"\n{p}. The present suit is maintainable under Section 9 of the Code of "
                f"Civil Procedure, 1908."
            )
            return "\n".join(lines)

        # ── Generic fallback ───────────────────────────────────────────
        lines = ["LEGAL BASIS"]
        permitted = lkb.get("permitted_doctrines") or []

        for doctrine in permitted:
            template = _DOCTRINE_TEMPLATES.get(doctrine)
            if template:
                p = self._next_para()
                lines.append(f"\n{p}. {template}")

        if len(lines) == 1:
            primary_acts = lkb.get("primary_acts", []) or []
            for act_info in primary_acts[:2]:
                act_name = act_info.get("act", "").strip()
                if not act_name:
                    continue
                sections = [s for s in act_info.get("sections", []) if s][:4]
                sections_text = ", ".join(sections)
                if act_name == "Law of Torts (Common Law)":
                    sentence = "The present cause is governed by the general law of torts recognised by Indian courts"
                else:
                    sentence = f"The present cause is governed by {act_name}"
                if sections_text:
                    sentence += f", including {sections_text}"
                sentence += "."
                p = self._next_para()
                lines.append(f"\n{p}. {sentence}")

            alt_acts = lkb.get("alternative_acts", []) or []
            for act_info in alt_acts[:2]:
                act_name = act_info.get("act", "").strip()
                if not act_name:
                    continue
                sections = [s for s in act_info.get("sections", []) if s][:4]
                sections_text = ", ".join(sections)
                sentence = f"The Plaintiff also relies on {act_name}"
                if sections_text:
                    sentence += f", including {sections_text}"
                sentence += ", where the pleaded facts attract those provisions."
                p = self._next_para()
                lines.append(f"\n{p}. {sentence}")

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

    def _cause_of_action(self, lkb: Dict, facts: Dict, cause_type: str = "", decision_ir: Optional[Dict[str, Any]] = None) -> str:
        if self._is_possession_cause(cause_type):
            lines = ["CAUSE OF ACTION"]
            coa_date = self._fact_value(
                facts,
                [
                    "cause_of_action_date",
                    "termination_date",
                    "licence_expiry_date",
                    "lease_expiry_date",
                    "revocation_date",
                    "ouster_date",
                ],
                "{{CAUSE_OF_ACTION_DATE}}",
            )

            if cause_type == "recovery_of_possession_tenant":
                trigger = "the Defendant's tenancy stood determined / expired"
            elif cause_type == "recovery_of_possession_licensee":
                trigger = "the Defendant's licence / permissive occupation stood revoked / came to an end"
            elif cause_type == "recovery_of_possession_co_owner":
                trigger = "the Defendant denied the Plaintiff's co-ownership rights and excluded the Plaintiff from possession"
            else:
                trigger = "the Defendant's occupation became wrongful and unauthorized as against the Plaintiff"

            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action for the present suit first arose on "
                f"{coa_date} when {trigger} and the Defendant failed to hand over "
                f"vacant possession of the suit property to the Plaintiff."
            )

            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action further arose when the Plaintiff caused "
                f"a legal notice dated {{{{NOTICE_DATE}}}} to be served upon the Defendant "
                f"demanding vacant possession, and the Defendant failed and refused to comply."
            )

            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action is continuing in nature as the Defendant "
                f"continues in wrongful and unauthorized occupation of the suit property "
                f"and continues to withhold possession from the Plaintiff."
            )

            return "\n".join(lines)

        if self._is_injunction_cause(cause_type):
            lines = ["CAUSE OF ACTION"]
            coa_date = self._fact_value(
                facts,
                [
                    "cause_of_action_date",
                    "interference_date",
                    "threat_date",
                    "date_of_objection",
                ],
                "{{CAUSE_OF_ACTION_DATE}}",
            )

            if cause_type == "mandatory_injunction":
                trigger = (
                    "the Defendant committed / continued the wrongful obstruction, "
                    "encroachment, or alteration complained of by the Plaintiff"
                )
                continuing_text = (
                    "The cause of action continues so long as the wrongful obstruction / "
                    "state of affairs created by the Defendant remains unremoved."
                )
            else:
                trigger = (
                    "the Defendant first attempted to trespass upon, interfere with, or "
                    "dispossess the Plaintiff from the suit property"
                )
                continuing_text = (
                    "The cause of action is continuing in nature as the Defendant continues "
                    "to threaten trespass, interference, and unlawful dispossession."
                )

            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action for the present suit first arose on "
                f"{coa_date} when {trigger}."
            )

            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action further arose on each subsequent occasion "
                f"when the Defendant persisted in the unlawful interference despite the "
                f"Plaintiff's objection and protest."
            )

            p = self._next_para()
            lines.append(f"\n{p}. {continuing_text}")
            return "\n".join(lines)

        # ── Partition ──────────────────────────────────────────────────
        if self._is_partition_cause(cause_type):
            lines = ["CAUSE OF ACTION"]
            coa_date = self._fact_value(
                facts,
                ["cause_of_action_date", "exclusion_date", "ouster_date", "denial_date"],
                "{{CAUSE_OF_ACTION_DATE}}",
            )
            if cause_type == "partition":
                trigger = (
                    "the Defendant denied the Plaintiff's right to partition / "
                    "separate possession and refused to divide the joint property"
                )
                continuing_text = (
                    "The cause of action continues so long as the parties remain at odds "
                    "regarding partition and separate possession."
                )
            elif cause_type == "easement":
                trigger = (
                    "the Defendant obstructed / threatened to obstruct the Plaintiff's "
                    "established right of pathway and denied the Plaintiff's easementary right"
                )
                continuing_text = (
                    "The cause of action is continuing in nature so long as the obstruction "
                    "remains or the Defendant continues to interfere with the Plaintiff's "
                    "use of the pathway."
                )
            elif cause_type == "adverse_possession_claim":
                trigger = (
                    "the Plaintiff's title was denied / interfered with by the Defendant, "
                    "the Plaintiff having been in continuous adverse possession"
                )
                continuing_text = (
                    "The cause of action is continuing as the Defendant continues to deny "
                    "the Plaintiff's asserted title and possession."
                )
            else:
                trigger = (
                    "the Defendant committed the wrongful act / denial of right "
                    "with respect to the suit immovable property"
                )
                continuing_text = (
                    "The cause of action is continuing as the Defendant continues "
                    "to deny the Plaintiff's rights in the suit property."
                )

            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action for the present suit first arose on "
                f"{coa_date} when {trigger}."
            )
            p = self._next_para()
            lines.append(f"\n{p}. {continuing_text}")
            return "\n".join(lines)

        # ── Tenancy ────────────────────────────────────────────────────
        if self._is_tenancy_cause(cause_type):
            lines = ["CAUSE OF ACTION"]
            coa_date = self._fact_value(
                facts,
                ["cause_of_action_date", "notice_expiry_date", "lease_expiry_date", "default_date"],
                "{{CAUSE_OF_ACTION_DATE}}",
            )
            if cause_type == "eviction":
                trigger = (
                    "the Defendant's tenancy stood lawfully determined by notice / expiry "
                    "and the Defendant failed to deliver vacant possession"
                )
            elif cause_type == "arrears_of_rent":
                trigger = (
                    "the Defendant defaulted in payment of rent due under the lease / tenancy"
                )
            else:
                trigger = (
                    "the Defendant continued in wrongful occupation after determination "
                    "of the tenancy"
                )

            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action for the present suit first arose on "
                f"{coa_date} when {trigger}."
            )
            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action further arose when the Plaintiff served "
                f"a legal notice dated {{{{NOTICE_DATE}}}} upon the Defendant, and the "
                f"Defendant failed to comply."
            )
            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action is continuing in nature as the Defendant "
                f"continues to wrongfully occupy the suit premises / withhold rent."
            )
            return "\n".join(lines)

        # ── Tort ───────────────────────────────────────────────────────
        if self._is_tort_cause(cause_type):
            lines = ["CAUSE OF ACTION"]
            coa_date = self._fact_value(
                facts,
                ["cause_of_action_date", "date_of_incident", "date_of_publication",
                 "date_of_injury", "date_of_tort"],
                "{{CAUSE_OF_ACTION_DATE}}",
            )
            if cause_type == "defamation":
                trigger = (
                    "the Defendant published / uttered the defamatory matter "
                    "concerning the Plaintiff"
                )
            elif cause_type == "nuisance":
                trigger = (
                    "the Defendant's acts first constituted nuisance interfering "
                    "with the Plaintiff's use and enjoyment"
                )
            elif cause_type in ("negligence_personal_injury", "negligence_property_damage"):
                trigger = (
                    "the Defendant's negligent act / omission caused "
                    f"{'injury to the Plaintiff' if 'personal' in cause_type else 'damage to the Plaintiffs property'}"
                )
            else:
                trigger = "the Defendant committed the tortious act against the Plaintiff"

            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action for the present suit first arose on "
                f"{coa_date} when {trigger}."
            )

            if cause_type == "nuisance":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The cause of action is continuing in nature as the nuisance "
                    f"persists unabated."
                )
            else:
                p = self._next_para()
                lines.append(
                    f"\n{p}. The suit is filed within the prescribed period of limitation."
                )
            return "\n".join(lines)

        if self._is_contract_cause(cause_type):
            lines = ["CAUSE OF ACTION"]
            coa_type = normalize_coa_type(lkb.get("coa_type"))
            coa_date = self._fact_value(
                facts,
                ["date_of_breach", "breach_date", "default_date", "cause_of_action_date"],
                "{{DATE_OF_BREACH}}",
            )
            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action first arose on "
                f"{coa_date} when the Defendant committed default under the agreement and "
                f"thereby caused the Plaintiff's right to sue for damages to accrue."
            )

            if coa_type == "continuing":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The breach pleaded is continuing in nature and continues to "
                    f"accrue so long as the Defendant remains in continuing default under "
                    f"the agreement."
                )
            elif coa_type == "single_event":
                p = self._next_para()
                lines.append(
                    f"\n{p}. The breach was a single event. The Plaintiff's claim for "
                    f"damages subsists and remains enforceable in law."
                )

            return "\n".join(lines)

        lines = ["CAUSE OF ACTION"]
        coa_type = normalize_coa_type(lkb.get("coa_type"))
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
            f"receipt of the legal notice dated {{{{NOTICE_DATE}}}}, failed to "
            f"comply with the Plaintiff's demand."
        )

        if coa_type == "continuing":
            p = self._next_para()
            lines.append(
                f"\n{p}. The cause of action is a continuing one and continues to "
                f"accrue from day to day as the Defendant continues to wrongfully "
                f"retain the Plaintiff's money / property."
            )
        elif coa_type == "single_event":
            p = self._next_para()
            lines.append(
                f"\n{p}. The breach was a single event. The Plaintiff's loss and "
                f"right to claim damages continue until compensated in accordance "
                f"with law."
            )

        return "\n".join(lines)

    # State-specific court fee statutes (covers major states)
    _STATE_COURT_FEE_ACTS = {
        "Karnataka": "Karnataka Court Fees and Suits Valuation Act, 1958",
        "Maharashtra": "Maharashtra Court Fees Act, 1959",
        "Tamil Nadu": "Tamil Nadu Court Fees and Suits Valuation Act, 1955",
        "Andhra Pradesh": "Andhra Pradesh Court Fees and Suits Valuation Act, 1956",
        "Telangana": "Telangana Court Fees and Suits Valuation Act, 1956",
        "Kerala": "Kerala Court Fees and Suits Valuation Act, 1959",
        "Gujarat": "Gujarat Court Fees Act, 2004",
        "Rajasthan": "Rajasthan Court Fees Act, 1961",
        "Madhya Pradesh": "Madhya Pradesh Court Fees Act, 2012",
        "Uttar Pradesh": "Court Fees Act, 1870 (as applicable in Uttar Pradesh)",
        "West Bengal": "West Bengal Court Fees Act, 1970",
        "Bihar": "Bihar Court Fees Act, 2012",
        "Punjab": "Punjab Court Fees Act, 1914",
        "Haryana": "Haryana Court Fees Act, 1999",
        "Odisha": "Odisha Court Fees Act, 1958",
        "Jharkhand": "Jharkhand Court Fees Act, 2010",
        "Chhattisgarh": "Chhattisgarh Court Fees Act, 2008",
        "Assam": "Assam Court Fees Act, 1870 (as applicable in Assam)",
        "Delhi": "Court Fees Act, 1870 (as applicable in Delhi)",
        "Goa": "Goa Court Fees and Suits Valuation Act, 1965",
    }

    def _valuation_court_fee(self, lkb: Dict, facts: Dict, state: str, court_fee: Optional[Dict], cause_type: str = "") -> str:
        p = self._next_para()
        # State-specific court fee statute — LKB override, then known state map, then fallback
        cfs = lkb.get("court_fee_statute", {})
        if isinstance(cfs, dict) and cfs:
            court_fee_act = cfs.get(state, cfs.get("_default", ""))
        else:
            court_fee_act = ""
        if not court_fee_act:
            court_fee_act = self._STATE_COURT_FEE_ACTS.get(
                state, "{{COURT_FEE_ACT_NAME}}"
            )

        if self._is_possession_cause(cause_type):
            return (
                f"VALUATION AND COURT FEE\n\n"
                f"{p}. The suit is valued at Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
                f"- (Rupees {{{{TOTAL_SUIT_VALUE_WORDS}}}} Only) for the purposes of "
                f"jurisdiction, the said valuation representing the value placed on the "
                f"suit immovable property. Appropriate court fee has been paid under the "
                f"provisions of the {court_fee_act} as applicable in the State of "
                f"{state or '{{STATE}}'}. The claim for mesne profits is separately prayed "
                f"for and shall abide by inquiry / valuation as directed by this Hon'ble Court."
            )

        if self._is_injunction_cause(cause_type):
            return (
                f"VALUATION AND COURT FEE\n\n"
                f"{p}. The suit is valued at Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
                f"- (Rupees {{{{TOTAL_SUIT_VALUE_WORDS}}}} Only) for the purposes of "
                f"jurisdiction and court fee as a suit for injunction. Appropriate court "
                f"fee of Rs. {{{{COURT_FEE_AMOUNT}}}}/- has been paid on this plaint under the provisions of the {court_fee_act} "
                f"as applicable in the State of {state or '{{STATE}}'}. The plaint is properly stamped."
            )

        if self._is_partition_cause(cause_type) and cause_type == "partition":
            return (
                f"VALUATION AND COURT FEE\n\n"
                f"{p}. The suit is valued at Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
                f"- (Rupees {{{{TOTAL_SUIT_VALUE_WORDS}}}} Only), being the market value "
                f"of the Plaintiff's share in the suit property, for the purposes of "
                f"jurisdiction and court fee. Appropriate court fee of Rs. {{{{COURT_FEE_AMOUNT}}}}/- has been paid on "
                f"this plaint under the provisions of the {court_fee_act} as "
                f"applicable in the State of {state or '{{STATE}}'}. "
                f"The plaint is properly stamped."
            )

        if self._is_tenancy_cause(cause_type):
            return (
                f"VALUATION AND COURT FEE\n\n"
                f"{p}. The suit is valued at Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
                f"- (Rupees {{{{TOTAL_SUIT_VALUE_WORDS}}}} Only) for the purposes of "
                f"jurisdiction and court fee. Appropriate court fee of Rs. {{{{COURT_FEE_AMOUNT}}}}/- has been paid under "
                f"the provisions of the {court_fee_act} as applicable in the State of "
                f"{state or '{{STATE}}'}. The plaint is properly stamped."
            )

        return (
            f"VALUATION AND COURT FEE\n\n"
            f"{p}. The suit is valued at Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
            f"- (Rupees {{{{TOTAL_SUIT_VALUE_WORDS}}}} Only) for the purposes of "
            f"jurisdiction and court fee. Court fee on the plaint has been computed at "
            f"Rs. {{{{COURT_FEE_AMOUNT}}}}/- under the provisions of the {court_fee_act} as "
            f"applicable in the State of {state or '{{STATE}}'}, with reference to "
            f"{{{{COURT_FEE_COMPUTATION_BASIS}}}} and the applicable rate schedule. "
            f"The plaint is tendered with the requisite court fee."
        )

    def _interest_section(self, lkb: Dict, cause_type: str = "") -> str:
        # Property-based suits don't have interest section
        if (
            self._is_possession_cause(cause_type)
            or self._is_injunction_cause(cause_type)
            or (self._is_partition_cause(cause_type) and cause_type not in ("mesne_profits",))
        ):
            return ""

        lines = ["INTEREST"]
        basis = lkb.get("interest_guidance", "")

        p = self._next_para()
        lines.append(
            f"\n{p}. The Plaintiff claims interest on the suit amount as follows:"
        )

        # Pre-suit interest — only for money/contract causes where contractual
        # rate may apply (from date of default to date of filing)
        if self._is_money_cause(cause_type) or self._is_contract_cause(cause_type):
            lines.append(
                f"\n    (a) Pre-suit interest at the rate of "
                f"{{{{INTEREST_RATE}}}}% per annum from {{{{DATE_OF_DEFAULT}}}} "
                f"(date of default) until the date of institution of the suit;"
            )
            lines.append(
                f"\n    (b) Pendente lite interest at such rate as the Court "
                f"deems fit and just from the date of institution of the suit until "
                f"the date of decree, under Order XX Rule 11 CPC;"
            )
            lines.append(
                f"\n    (c) Post-decree interest at such rate as the Court deems "
                f"fit and just from the date of decree until realization of the "
                f"entire decretal amount, under Section 34 CPC."
            )
        else:
            lines.append(
                f"\n    (a) Pendente lite interest at such rate as the Court "
                f"deems fit and just from the date of institution of the suit until "
                f"the date of decree, under Order XX Rule 11 CPC;"
            )
            lines.append(
                f"\n    (b) Post-decree interest at such rate as the Court deems "
                f"fit and just from the date of decree until realization of the "
                f"entire decretal amount, under Section 34 CPC."
            )

        if basis:
            lines.append(f"\n    The interest is justified because {basis}")

        return "\n".join(lines)

    def _prayer_from_template(self, prayer_items: List[str]) -> str:
        """Build prayer section from LKB prayer_template items (data-driven)."""
        lines = ["PRAYER"]
        lines.append(
            "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
            "that this Hon'ble Court be pleased to:"
        )
        letter = ord("a")
        for item in prayer_items:
            lines.append(f"\n    ({chr(letter)}) {item};")
            letter += 1
        # Auto-append costs + general relief if not already present
        if not any("costs" in item.lower() for item in prayer_items):
            lines.append(f"\n    ({chr(letter)}) Award costs of the suit;")
            letter += 1
        if not any("further relief" in item.lower() for item in prayer_items):
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as "
                f"this Hon'ble Court may deem fit and proper in the facts and "
                f"circumstances of the case."
            )
        return "\n".join(lines)

    def _prayer(self, lkb: Dict, cause_type: str = "") -> str:
        # Try LKB prayer_template first (data-driven)
        prayer_items = lkb.get("prayer_template") or []
        if prayer_items:
            return self._prayer_from_template(prayer_items)

        # Fall through to existing hardcoded logic (backward compat)
        if self._is_possession_cause(cause_type):
            lines = ["PRAYER"]
            lines.append(
                "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
                "that this Hon'ble Court be pleased to:"
            )
            letter = ord("a")
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree for recovery of possession of the "
                f"suit immovable property in favour of the Plaintiff and direct the Defendant "
                f"to deliver vacant and peaceful possession thereof to the Plaintiff;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree for past mesne profits for the "
                f"period from {{{{MESNE_PROFITS_START_DATE}}}} till the date of institution "
                f"of the suit, in such sum as may be found due to the Plaintiff;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Direct an inquiry under Order XX Rule 12 of the "
                f"Code of Civil Procedure, 1908 into future mesne profits from the date of "
                f"institution of the suit till delivery of possession / relinquishment through "
                f"Court / three years from decree, whichever is earlier;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Award costs of the suit including costs of the legal notice;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
                f"Hon'ble Court may deem fit and proper in the facts and circumstances "
                f"of the case."
            )
            return "\n".join(lines)

        if self._is_injunction_cause(cause_type):
            lines = ["PRAYER"]
            lines.append(
                "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
                "that this Hon'ble Court be pleased to:"
            )
            letter = ord("a")

            if cause_type == "mandatory_injunction":
                lines.append(
                    f"\n    ({chr(letter)}) Pass a decree of mandatory injunction directing "
                    f"the Defendant to remove / undo the wrongful obstruction, encroachment, "
                    f"or alteration complained of by the Plaintiff and restore the position "
                    f"as it existed prior to the Defendant's unlawful acts;"
                )
            else:
                lines.append(
                    f"\n    ({chr(letter)}) Pass a decree of permanent injunction restraining "
                    f"the Defendant, his agents, servants, supporters, or anyone claiming "
                    f"through or under him from trespassing into, interfering with, or "
                    f"attempting to dispossess the Plaintiff from the suit property;"
                )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Award costs of the suit including costs of the legal notice;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
                f"Hon'ble Court may deem fit and proper in the facts and circumstances "
                f"of the case."
            )
            return "\n".join(lines)

        # ── Contract / Specific Performance ────────────────────────────
        if self._is_contract_cause(cause_type) and cause_type == "specific_performance":
            lines = ["PRAYER"]
            lines.append(
                "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
                "that this Hon'ble Court be pleased to:"
            )
            letter = ord("a")
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree of specific performance directing "
                f"the Defendant to perform and complete the agreement dated "
                f"{{{{AGREEMENT_DATE}}}} in favour of the Plaintiff;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Direct the Defendant to execute and register the "
                f"necessary conveyance / sale deed in favour of the Plaintiff upon "
                f"receipt of the balance consideration;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) In the alternative, award compensation / damages "
                f"in lieu of specific performance;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Award costs of the suit;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
                f"Hon'ble Court may deem fit and proper in the facts and circumstances "
                f"of the case."
            )
            return "\n".join(lines)

        # ── Partition ──────────────────────────────────────────────────
        if self._is_partition_cause(cause_type) and cause_type == "partition":
            lines = ["PRAYER"]
            lines.append(
                "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
                "that this Hon'ble Court be pleased to:"
            )
            letter = ord("a")
            lines.append(
                f"\n    ({chr(letter)}) Pass a preliminary decree declaring the rights "
                f"and shares of the parties in the suit property;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Pass a final decree for partition of the suit "
                f"property by metes and bounds and for delivery of separate possession "
                f"of the Plaintiff's share to the Plaintiff;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) In the event partition by metes and bounds is "
                f"not feasible, direct sale of the suit property and distribution of "
                f"the sale proceeds among the parties in accordance with their shares;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Direct the Defendant to render accounts of "
                f"income received from the joint property and pay the Plaintiff's "
                f"proportionate share thereof;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Award costs of the suit;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
                f"Hon'ble Court may deem fit and proper in the facts and circumstances "
                f"of the case."
            )
            return "\n".join(lines)

        # ── Tenancy / Eviction ─────────────────────────────────────────
        if self._is_tenancy_cause(cause_type):
            lines = ["PRAYER"]
            lines.append(
                "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
                "that this Hon'ble Court be pleased to:"
            )
            letter = ord("a")

            if cause_type == "eviction":
                lines.append(
                    f"\n    ({chr(letter)}) Pass a decree of eviction directing the Defendant "
                    f"to vacate the suit premises and deliver vacant and peaceful possession "
                    f"thereof to the Plaintiff;"
                )
                letter += 1
                lines.append(
                    f"\n    ({chr(letter)}) Pass a decree for arrears of rent from "
                    f"{{{{ARREARS_FROM_DATE}}}} to {{{{ARREARS_TO_DATE}}}} in such sum "
                    f"as may be found due;"
                )
                letter += 1
                lines.append(
                    f"\n    ({chr(letter)}) Pass a decree for mesne profits / damages for "
                    f"use and occupation from the date of determination of tenancy till "
                    f"delivery of possession;"
                )
                letter += 1
            elif cause_type == "arrears_of_rent":
                lines.append(
                    f"\n    ({chr(letter)}) Pass a decree for recovery of arrears of rent "
                    f"amounting to Rs. {{{{ARREARS_AMOUNT}}}}/"
                    f"- from {{{{ARREARS_FROM_DATE}}}} to {{{{ARREARS_TO_DATE}}}};"
                )
                letter += 1
                lines.append(
                    f"\n    ({chr(letter)}) Award pendente lite and future interest at "
                    f"such rate as this Hon'ble Court deems just;"
                )
                letter += 1
            elif cause_type == "mesne_profits_post_tenancy":
                lines.append(
                    f"\n    ({chr(letter)}) Pass a decree for mesne profits from the date "
                    f"of determination of tenancy till delivery of vacant possession;"
                )
                letter += 1
                lines.append(
                    f"\n    ({chr(letter)}) Direct an inquiry under Order XX Rule 12 of the "
                    f"Code of Civil Procedure, 1908 for computation of mesne profits;"
                )
                letter += 1

            lines.append(
                f"\n    ({chr(letter)}) Award costs of the suit;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
                f"Hon'ble Court may deem fit and proper in the facts and circumstances "
                f"of the case."
            )
            return "\n".join(lines)

        # ── Tort / Defamation ──────────────────────────────────────────
        if self._is_tort_cause(cause_type) and cause_type == "defamation":
            lines = ["PRAYER"]
            lines.append(
                "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
                "that this Hon'ble Court be pleased to:"
            )
            letter = ord("a")
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree for damages amounting to "
                f"Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
                f"- against the Defendant for injury to the Plaintiff's reputation;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree of permanent injunction restraining "
                f"the Defendant from further publishing / repeating the defamatory matter;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Award costs of the suit;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
                f"Hon'ble Court may deem fit and proper in the facts and circumstances "
                f"of the case."
            )
            return "\n".join(lines)

        # ── Tort / Nuisance ────────────────────────────────────────────
        if self._is_tort_cause(cause_type) and cause_type == "nuisance":
            lines = ["PRAYER"]
            lines.append(
                "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
                "that this Hon'ble Court be pleased to:"
            )
            letter = ord("a")
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree of permanent injunction directing "
                f"the Defendant to abate / cease the nuisance complained of;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree for damages amounting to "
                f"Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
                f"- for loss suffered by the Plaintiff on account of the nuisance;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Award costs of the suit;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
                f"Hon'ble Court may deem fit and proper in the facts and circumstances "
                f"of the case."
            )
            return "\n".join(lines)

        # ── Tort / Recovery of Specific Movable ────────────────────────
        if self._is_money_cause(cause_type) and cause_type == "recovery_specific_movable":
            lines = ["PRAYER"]
            lines.append(
                "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
                "that this Hon'ble Court be pleased to:"
            )
            letter = ord("a")
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree for delivery of the specific "
                f"movable property described in the plaint / schedule to the Plaintiff;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) In the alternative, award the value of the said "
                f"movable property assessed at Rs. {{{{TOTAL_SUIT_VALUE}}}}/-;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Award costs of the suit;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
                f"Hon'ble Court may deem fit and proper in the facts and circumstances "
                f"of the case."
            )
            return "\n".join(lines)

        # ── Accounts / Relationship ──────────────────────────────────
        if self._is_accounts_cause(cause_type):
            lines = ["PRAYER"]
            lines.append(
                "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
                "that this Hon'ble Court be pleased to:"
            )
            letter = ord("a")
            lines.append(
                f"\n    ({chr(letter)}) Pass a preliminary decree directing the Defendant "
                f"to render true and faithful accounts of all transactions and dealings "
                f"during the period {{{{ACCOUNTING_PERIOD}}}} under Order XX Rule 16 of "
                f"the Code of Civil Procedure, 1908;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Appoint a Commissioner for taking accounts, if "
                f"necessary;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Pass a final decree for payment of such sum as "
                f"may be found due to the Plaintiff upon rendition of accounts;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Award pendente lite interest under Order XX "
                f"Rule 11 CPC and post-decree interest under Section 34 CPC at such "
                f"rate as this Hon'ble Court deems just;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Award costs of the suit;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
                f"Hon'ble Court may deem fit and proper in the facts and circumstances "
                f"of the case."
            )
            return "\n".join(lines)

        # ── Generic fallback (contract / money / tort with damages) ────
        if self._is_easement_cause(cause_type):
            lines = ["PRAYER"]
            lines.append(
                "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
                "that this Hon'ble Court be pleased to:"
            )
            letter = ord("a")
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree declaring that the Plaintiff has "
                f"an easementary right of way over the pathway / passage described in "
                f"Schedule B for access to the dominant heritage described in Schedule A;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree of mandatory injunction directing "
                f"the Defendant to remove the obstruction / encroachment from the said "
                f"pathway and restore the Plaintiff's access thereto;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Pass a decree of permanent injunction "
                f"restraining the Defendant, his agents, servants, or anybody claiming "
                f"through him from obstructing or interfering with the Plaintiff's "
                f"peaceful use of the said pathway in future;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Award costs of the suit;"
            )
            letter += 1
            lines.append(
                f"\n    ({chr(letter)}) Grant such other and further relief(s) as this "
                f"Hon'ble Court may deem fit and proper in the facts and circumstances "
                f"of the case."
            )
            return "\n".join(lines)

        # Prayer lists ONLY the aggregate decree, interest, and costs.
        # Individual damage heads belong in SCHEDULE OF DAMAGES, not prayer.
        lines = ["PRAYER"]
        lines.append(
            "\nIn the premises aforesaid, the Plaintiff most respectfully prays "
            "that this Hon'ble Court be pleased to:"
        )

        letter = ord('a')

        # Main decree — single aggregate amount (no itemized breakdown)
        decree_tail = "towards damages as particularised in the Schedule of Damages annexed hereto;"
        if self._is_contract_cause(cause_type):
            decree_tail = (
                "towards damages for breach of contract as particularised in the "
                "Schedule of Damages annexed hereto;"
            )
        lines.append(
            f"\n    ({chr(letter)}) Pass a decree in favour of the Plaintiff and "
            f"against the Defendant for a sum of Rs. {{{{TOTAL_SUIT_VALUE}}}}/"
            f"- (Rupees {{{{TOTAL_SUIT_VALUE_WORDS}}}} Only) {decree_tail}"
        )
        letter += 1

        # Interest
        lines.append(
            f"\n    ({chr(letter)}) Award pendente lite interest at such rate as "
            f"the Court deems just from the date of suit till decree under "
            f"Order XX Rule 11 CPC, and future interest from the date of "
            f"decree till realisation under Section 34 CPC;"
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
            f"Court may deem fit and proper in the facts and circumstances "
            f"of the case."
        )

        return "\n".join(lines)

    # Interest-type categories excluded from Schedule — covered by S.34 prayer
    _INTEREST_CATEGORIES = frozenset({
        "interest_on_delayed_payment", "interest_on_principal", "interest_on_price",
    })

    def _damages_schedule(self, lkb: Dict, cause_type: str = "") -> str:
        lines = ["SCHEDULE OF DAMAGES / PARTICULARS OF DAMAGES"]
        damages = [
            d for d in lkb.get("damages_categories", [])
            if d not in self._INTEREST_CATEGORIES
        ]

        if not damages:
            return ""

        lines.append(
            "\nThe Plaintiff claims the following heads of damages with "
            "computation methodology:"
        )

        _ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
        for i, category in enumerate(damages):
            display = _DAMAGE_DISPLAY.get(category, category.replace("_", " ").title())
            amount_key = f"{{{{{category.upper()}_AMOUNT}}}}"
            if self._is_contract_cause(cause_type) and damages == ["actual_loss"]:
                amount_key = "{{TOTAL_SUIT_VALUE}}"
            numeral = _ROMAN[i] if i < len(_ROMAN) else str(i + 1)
            lines.append(
                f"\n({numeral}) {display}\n"
                f"     Amount claimed: Rs. {amount_key}/-\n"
                f"     Basis / methodology: {{{{{category.upper()}_BASIS}}}}\n"
                f"     Documentary proof: {{{{{category.upper()}_PROOF}}}}"
            )

        lines.append(
            f"\nTOTAL DAMAGES CLAIMED: Rs. {{{{TOTAL_SUIT_VALUE}}}}/-"
        )
        return "\n".join(lines)

    def _schedule_of_property(self, facts: Dict[str, Any]) -> str:
        """Schedule of suit property — required for all immovable property suits."""
        address = self._fact_value(
            facts,
            ["property_address", "suit_property_address", "property_description",
             "schedule_property", "property_location"],
            None,
        )
        survey = self._fact_value(
            facts,
            ["land_survey_number", "survey_number", "survey_no"],
            None,
        )
        extent = self._fact_value(
            facts,
            ["land_area", "extent", "property_area"],
            None,
        )
        boundaries = self._fact_value(
            facts,
            ["boundaries", "property_boundaries"],
            None,
        )

        # Consolidate: if ALL fields empty, single placeholder instead of 4
        if not any([address, survey, extent, boundaries]):
            return (
                "SCHEDULE OF SUIT PROPERTY\n\n"
                "{{SCHEDULE_OF_SUIT_PROPERTY -- Address, Survey/Plot No., "
                "Extent/Area, Boundaries (East/West/North/South)}}"
            )

        return (
            "SCHEDULE OF SUIT PROPERTY\n\n"
            f"All that piece and parcel of immovable property situated at:\n\n"
            f"Address: {address or '{{SUIT_PROPERTY_ADDRESS}}'}\n"
            f"Survey / Plot No.: {survey or '{{SURVEY_NUMBER}}'}\n"
            f"Extent / Area: {extent or '{{PROPERTY_AREA}}'}\n"
            f"Boundaries:\n{boundaries or '{{BOUNDARIES -- East: ___, West: ___, North: ___, South: ___}}'}"
        )

    def _schedule_of_easement(self, facts: Dict[str, Any]) -> str:
        dominant = self._fact_value(
            facts,
            ["dominant_heritage_description", "plaintiff_property_description", "property_description", "property_address"],
            None,
        )
        dominant_survey = self._fact_value(
            facts,
            ["dominant_heritage_survey_number", "land_survey_number", "survey_number", "survey_no"],
            None,
        )
        pathway = self._fact_value(
            facts,
            ["pathway_description", "servient_heritage_description", "easement_pathway_description", "right_of_way_description"],
            None,
        )
        pathway_measurements = self._fact_value(
            facts,
            ["pathway_measurements", "pathway_dimensions", "pathway_width_length"],
            None,
        )
        pathway_boundaries = self._fact_value(
            facts,
            ["pathway_boundaries", "servient_heritage_boundaries", "boundaries"],
            None,
        )

        # Consolidate: if ALL fields empty, single placeholder instead of 5
        if not any([dominant, dominant_survey, pathway, pathway_measurements, pathway_boundaries]):
            return (
                "SCHEDULE A - DOMINANT HERITAGE\n\n"
                "{{DOMINANT_HERITAGE -- Description, Survey No.}}\n\n"
                "SCHEDULE B - PATHWAY / SERVIENT HERITAGE\n\n"
                "{{EASEMENT_PATHWAY -- Description, Width/Length, Boundaries (E/W/N/S)}}"
            )

        return (
            "SCHEDULE A - DOMINANT HERITAGE\n\n"
            f"Property of the Plaintiff for the beneficial enjoyment of which the "
            f"claimed easement is exercised:\n"
            f"Description: {dominant or '{{DOMINANT_HERITAGE_DESCRIPTION}}'}\n"
            f"Survey / Plot No.: {dominant_survey or '{{DOMINANT_HERITAGE_SURVEY_NO}}'}\n\n"
            "SCHEDULE B - PATHWAY / SERVIENT HERITAGE\n\n"
            f"Description of the pathway / passage over which the easementary right "
            f"is claimed:\n"
            f"Pathway: {pathway or '{{PATHWAY_DESCRIPTION}}'}\n"
            f"Measurements: {pathway_measurements or '{{PATHWAY_MEASUREMENTS -- width / length / alignment}}'}\n"
            f"Boundaries / alignment:\n{pathway_boundaries or '{{PATHWAY_BOUNDARIES -- East: ___, West: ___, North: ___, South: ___}}'}"
        )

    def _documents_list_legacy(self, evidence: List[Dict]) -> str:
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
