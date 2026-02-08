"""Multi-stage contact deduplication pipeline."""
from typing import Optional
from .phone_validator import normalize_phone
from app.config import logger


def deduplicate_contacts(
    contacts: list,
    default_country: str = "IN",
    cross_campaign_phones: Optional[set] = None,
) -> tuple:
    """
    Multi-stage deduplication pipeline for contacts.

    Stages:
        1. Exact match - identical phone strings
        2. Normalized match - compare after E.164 normalization
        3. Fuzzy match - Levenshtein distance <= 1 on E.164 numbers
        4. Cross-campaign - check against phones from previous campaigns (optional)

    Args:
        contacts: List of contact dicts (must have "phone" key)
        default_country: Country code for phone normalization
        cross_campaign_phones: Optional set of E.164 phone numbers from previous campaigns

    Returns:
        tuple: (unique_contacts, duplicates_removed)
            - unique_contacts: List of deduplicated contact dicts
            - duplicates_removed: List of duplicate contact dicts with "duplicate_of" field
    """
    if not contacts:
        return ([], [])

    logger.info(f"Deduplicating {len(contacts)} contacts (4-stage pipeline)")

    unique = []
    duplicates = []

    # Track seen phones at each stage
    seen_raw = set()           # Stage 1: exact raw strings
    seen_normalized = set()    # Stage 2: E.164 normalized
    seen_fuzzy = {}            # Stage 3: e164 -> contact for fuzzy matching

    for contact in contacts:
        phone = contact.get("phone", "").strip()
        if not phone:
            continue

        # Stage 1: Exact match
        if phone in seen_raw:
            dup = {**contact, "duplicate_of": phone, "dedup_stage": "exact"}
            duplicates.append(dup)
            continue

        # Stage 2: Normalized match
        normalized = normalize_phone(phone, default_country)
        if normalized in seen_normalized:
            dup = {**contact, "duplicate_of": normalized, "dedup_stage": "normalized"}
            duplicates.append(dup)
            continue

        # Stage 3: Fuzzy match (Levenshtein distance <= 1)
        fuzzy_match = _fuzzy_find(normalized, seen_fuzzy)
        if fuzzy_match:
            dup = {**contact, "duplicate_of": fuzzy_match, "dedup_stage": "fuzzy"}
            duplicates.append(dup)
            continue

        # Stage 4: Cross-campaign dedup
        if cross_campaign_phones and normalized in cross_campaign_phones:
            dup = {**contact, "duplicate_of": normalized, "dedup_stage": "cross_campaign"}
            duplicates.append(dup)
            continue

        # Not a duplicate - add to unique
        seen_raw.add(phone)
        seen_normalized.add(normalized)
        seen_fuzzy[normalized] = phone
        contact["phone_normalized"] = normalized
        unique.append(contact)

    logger.info(
        f"Deduplication complete: {len(unique)} unique, {len(duplicates)} duplicates removed"
    )

    # Log stage breakdown
    stage_counts = {}
    for d in duplicates:
        stage = d.get("dedup_stage", "unknown")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    if stage_counts:
        logger.info(f"Duplicate breakdown by stage: {stage_counts}")

    return (unique, duplicates)


def _fuzzy_find(phone: str, seen: dict) -> Optional[str]:
    """
    Check if phone is within Levenshtein distance 1 of any seen number.

    Only compares numbers of similar length (within 1 char difference).

    Args:
        phone: E.164 formatted phone to check
        seen: Dict of {e164_phone: original_phone}

    Returns:
        str: The matching phone number, or None if no fuzzy match
    """
    if not seen or not phone:
        return None

    try:
        from Levenshtein import distance as lev_distance
    except ImportError:
        return None

    phone_len = len(phone)
    for existing in seen:
        # Skip if length difference > 1 (can't be distance <= 1)
        if abs(len(existing) - phone_len) > 1:
            continue
        if lev_distance(phone, existing) <= 1:
            return existing

    return None
