"""Shared helpers for cause group sub-modules.

Extracted from civil.py — all cause group files import from here.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

COMMERCIAL_THRESHOLD = 300000

COMMON_REQUIRED_AVERMENTS = [
    "jurisdiction_basis", "cause_of_action_dates", "valuation_statement",
    "court_fee_basis", "verification_clause",
]

COMMON_CIVIL_PLAINT_SECTIONS = [
    "court_heading", "title", "parties", "jurisdiction", "facts",
    "legal_basis", "cause_of_action", "limitation", "valuation_court_fee",
    "prayer", "document_list", "verification",
]


def _civil_court_rules():
    return {
        "default": {
            "court": "Civil Judge (Senior Division)",
            "format": "O.S. No.",
            "heading": "IN THE COURT OF THE {court_type}",
        }
    }


def _civil_and_commercial_rules(*, nature_keywords=None, extra_procedural=None):
    procedural = [
        "Screen commercial dispute under Commercial Courts Act, 2015",
        "If commercial and specified value >= Rs.3 lakh, use Commercial Court format",
        "Section 12A pre-institution mediation mandatory unless urgent interim relief",
        "Statement of truth as per Order VI Rule 15A / Appendix-I for commercial disputes",
    ]
    if extra_procedural:
        procedural.extend(extra_procedural)
    return {
        "default": _civil_court_rules()["default"],
        "commercial": {
            "threshold": COMMERCIAL_THRESHOLD,
            "court": "Commercial Court",
            "format": "C.S. No.",
            "heading": "IN THE COURT OF THE {court_type} (COMMERCIAL DIVISION)",
            "act": "Commercial Courts Act, 2015",
            "procedural": procedural,
            "nature_keywords": nature_keywords or [],
        },
    }


def _entry(
    *,
    registry_kind,
    code,
    display_name,
    document_type="plaint",
    stage=None,
    primary_acts=None,
    alternative_acts=None,
    limitation=None,
    court_rules=None,
    required_sections=None,
    required_reliefs=None,
    required_averments=None,
    optional_reliefs=None,
    procedural_prerequisites=None,
    doc_type_keywords=None,
    classification_hints=None,
    permitted_doctrines=None,
    excluded_doctrines=None,
    defensive_points=None,
    terminology=None,
    damages_categories=None,
    interest_basis="not_applicable",
    interest_guidance="",
    coa_type=None,
    coa_guidance="",
    facts_must_cover=None,
    evidence_checklist=None,
    mandatory_averments=None,
    mandatory_inline_sections=None,
    drafting_red_flags=None,
    prayer_template=None,
    court_fee_statute=None,
    detected_court=None,
    complexity_weight=2,
    notes=None,
    draft_config=None,
    # ── v10.0: 5-Layer Data Model ──
    section_plan=None,
    gap_definitions=None,
    accuracy_rules=None,
    pre_institution=None,
    section_overrides=None,
    # ── v11.0: Layer 2 — Document Components ──
    available_reliefs=None,
    jurisdiction_basis=None,
    valuation_basis=None,
    legal_basis_text=None,
    suit_title_prefix=None,
):
    return {
        "registry_kind": registry_kind,
        "code": code,
        "display_name": display_name,
        "document_type": document_type,
        "stage": stage,
        "primary_acts": primary_acts or [],
        "alternative_acts": alternative_acts or [],
        "limitation": limitation or {},
        "court_rules": deepcopy(court_rules or _civil_court_rules()),
        "required_sections": required_sections or [],
        "required_reliefs": required_reliefs or [],
        "required_averments": required_averments or [],
        "optional_reliefs": optional_reliefs or [],
        "procedural_prerequisites": procedural_prerequisites or [],
        "doc_type_keywords": doc_type_keywords or [],
        "classification_hints": classification_hints or [],
        "permitted_doctrines": permitted_doctrines or [],
        "excluded_doctrines": excluded_doctrines or [],
        "defensive_points": defensive_points or [],
        "terminology": terminology or {},
        "damages_categories": damages_categories or [],
        "interest_basis": interest_basis,
        "interest_guidance": interest_guidance,
        "coa_type": coa_type,
        "coa_guidance": coa_guidance,
        "facts_must_cover": facts_must_cover or [],
        "evidence_checklist": evidence_checklist or [],
        "mandatory_averments": mandatory_averments or [],
        "mandatory_inline_sections": mandatory_inline_sections or [],
        "drafting_red_flags": drafting_red_flags or [],
        "prayer_template": prayer_template or [],
        "court_fee_statute": court_fee_statute or {},
        "detected_court": deepcopy(detected_court or {}),
        "complexity_weight": complexity_weight,
        "notes": notes or [],
        "draft_config": draft_config or {},
        # v10.0 layers — None = use family defaults / legacy path
        "section_plan": section_plan,
        "gap_definitions": gap_definitions,
        "accuracy_rules": accuracy_rules,
        "pre_institution": pre_institution,
        "section_overrides": section_overrides,
        # v11.0 Layer 2 — Document Components (None = not yet enriched)
        "available_reliefs": available_reliefs,
        "jurisdiction_basis": jurisdiction_basis,
        "valuation_basis": valuation_basis,
        "legal_basis_text": legal_basis_text,
        "suit_title_prefix": suit_title_prefix,
    }
