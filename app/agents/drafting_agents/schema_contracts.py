from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SUPPORTED_LAW_DOMAINS = ("Civil", "Criminal", "Family", "Corporate", "IP", "Other")
SUPPORTED_SECTION_TYPES = ("template", "template_with_fill", "llm_fill")
SUPPORTED_SECTION_CONDITIONS = (
    "monetary_claim",
    "immovable_property",
    "is_commercial",
    "has_damages_categories",
    "has_schedule_of_property",
    "has_interest",
)

_MONETARY_DOC_KEYWORDS = (
    "money",
    "recovery",
    "loan",
    "rent",
    "damages",
    "debt",
    "restitution",
    "refund",
    "price",
    "compensation",
    "cheque",
)

_IMMOVABLE_DOC_KEYWORDS = (
    "property",
    "possession",
    "partition",
    "eviction",
    "mortgage",
    "easement",
    "injunction",
    "declaration_title",
    "specific_performance",
)


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        if isinstance(dumped, dict):
            return dumped
    return value if isinstance(value, dict) else {}


def _nested_dict(source: Mapping[str, Any], key: str) -> dict[str, Any]:
    value: Any = source
    for part in key.split("."):
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        if not isinstance(value, Mapping):
            return {}
        value = value.get(part, {})
    return _as_dict(value)


def _normalized_doc_type(doc_type: str, context: Mapping[str, Any]) -> str:
    for candidate in (
        doc_type,
        _nested_dict(context, "classify").get("doc_type", ""),
        _nested_dict(context, "template").get("doc_type", ""),
    ):
        if candidate:
            return str(candidate).lower()
    return ""


def is_supported_condition(condition: str) -> bool:
    if not condition:
        return True
    if condition.startswith("doc_type_contains:"):
        suffix = condition.split(":", 1)[1]
        return any(token.strip() for token in suffix.split("|"))
    return condition in SUPPORTED_SECTION_CONDITIONS


def _looks_monetary(doc_type: str, context: Mapping[str, Any]) -> bool:
    if any(token in doc_type for token in _MONETARY_DOC_KEYWORDS):
        return True

    facts = _nested_dict(context, "facts")
    if not facts:
        facts = _nested_dict(context, "facts_obj")
    if not facts:
        facts = _nested_dict(context, "intake.facts")

    amounts = _as_dict(facts.get("amounts"))
    for key in ("principal", "damages", "interest_rate"):
        value = amounts.get(key)
        if value not in (None, "", 0, 0.0):
            return True

    required_reliefs = _nested_dict(context, "lkb").get("required_reliefs") or []
    return any("damages" in str(relief).lower() or "money" in str(relief).lower() for relief in required_reliefs)


def _looks_immovable(doc_type: str, context: Mapping[str, Any]) -> bool:
    if any(token in doc_type for token in _IMMOVABLE_DOC_KEYWORDS):
        return True

    classify = _nested_dict(context, "classify")
    cause_type = str(classify.get("cause_type", "") or context.get("cause_type", "")).lower()
    if any(token in cause_type for token in ("property", "possession", "partition", "eviction", "mortgage", "easement")):
        return True

    decision = _nested_dict(context, "decision_ir")
    family = str(decision.get("family", "")).lower()
    if family == "immovable_property":
        return True

    required_sections = _nested_dict(context, "lkb").get("required_sections") or []
    return "schedule_of_property" in required_sections


def evaluate_section_condition(
    condition: str,
    *,
    doc_type: str = "",
    context: Mapping[str, Any] | None = None,
) -> bool:
    if not condition:
        return True

    context = context or {}
    normalized_doc_type = _normalized_doc_type(doc_type, context)

    if condition.startswith("doc_type_contains:"):
        keywords = [token.strip().lower() for token in condition.split(":", 1)[1].split("|") if token.strip()]
        return any(keyword in normalized_doc_type for keyword in keywords)

    if condition == "monetary_claim":
        return _looks_monetary(normalized_doc_type, context)

    if condition == "immovable_property":
        return _looks_immovable(normalized_doc_type, context)

    if condition == "is_commercial":
        return bool(context.get("is_commercial"))

    if condition == "has_damages_categories":
        return bool(_nested_dict(context, "lkb").get("damages_categories"))

    if condition == "has_schedule_of_property":
        return "schedule_of_property" in (_nested_dict(context, "lkb").get("required_sections") or []) or _looks_immovable(
            normalized_doc_type, context
        )

    if condition == "has_interest":
        lkb = _nested_dict(context, "lkb")
        interest_basis = str(lkb.get("interest_basis", "not_applicable")).lower()
        if interest_basis and interest_basis != "not_applicable":
            return True
        return _looks_monetary(normalized_doc_type, context)

    return True


def validate_template_payload(template: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []

    for field in ("template_id", "template_version", "doc_type", "law_domain", "party_labels", "sections"):
        if field not in template:
            errors.append(f"missing required field '{field}'")

    law_domain = template.get("law_domain")
    if law_domain and law_domain not in SUPPORTED_LAW_DOMAINS:
        errors.append(f"invalid law_domain: {law_domain!r}")

    party_labels = _as_dict(template.get("party_labels"))
    if party_labels and not {"primary", "opposite"} <= set(party_labels):
        errors.append("party_labels must include 'primary' and 'opposite'")

    sections = template.get("sections", [])
    if not isinstance(sections, list) or not sections:
        errors.append("sections must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, section in enumerate(sections):
        if not isinstance(section, Mapping):
            errors.append(f"section {index} is not an object")
            continue

        sid = str(section.get("section_id", "") or "")
        stype = str(section.get("type", "") or "")
        heading = section.get("heading")

        if not sid:
            errors.append(f"section {index} missing section_id")
        elif sid in seen_ids:
            errors.append(f"duplicate section_id: {sid}")
        else:
            seen_ids.add(sid)

        if not isinstance(heading, str):
            errors.append(f"section {sid or index}: heading must be a string")

        if stype not in SUPPORTED_SECTION_TYPES:
            errors.append(f"section {sid or index}: invalid type {stype!r}")
            continue

        if stype == "template" and not isinstance(section.get("body"), str):
            errors.append(f"section {sid or index}: template type requires string 'body'")
        if stype in {"template_with_fill", "llm_fill"} and not isinstance(section.get("instruction"), str):
            errors.append(f"section {sid or index}: {stype} type requires string 'instruction'")

        condition = section.get("condition", "")
        if condition and (not isinstance(condition, str) or not is_supported_condition(condition)):
            errors.append(f"section {sid or index}: unsupported condition {condition!r}")

        examples = section.get("examples")
        if examples is not None:
            if not isinstance(examples, Mapping):
                errors.append(f"section {sid or index}: examples must be an object")
            else:
                for label in ("bad", "good"):
                    if label in examples and not isinstance(examples[label], str):
                        errors.append(f"section {sid or index}: examples.{label} must be a string")

        must_include = section.get("must_include", [])
        if must_include is None:
            must_include = []
        if not isinstance(must_include, list):
            errors.append(f"section {sid or index}: must_include must be a list")
            continue

        for item_index, item in enumerate(must_include):
            if not isinstance(item, Mapping):
                errors.append(f"section {sid or index}: must_include[{item_index}] is not an object")
                continue
            if item.get("type") not in {"keyword", "regex", "concept", "evidence_anchor"}:
                errors.append(f"section {sid or index}: must_include[{item_index}] invalid type")
            if not isinstance(item.get("match"), str):
                errors.append(f"section {sid or index}: must_include[{item_index}] missing string match")

    return errors
