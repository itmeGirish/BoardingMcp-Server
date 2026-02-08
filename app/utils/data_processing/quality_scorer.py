"""Data quality scoring for broadcast contacts.

Scoring weights (per WhatsApp Broadcasting Agent Documentation):
    Phone Validity  : 40%  - Valid format: 40, Invalid: 0
    Completeness    : 25%  - All fields: 25, Name missing: 15, Minimal: 5
    Recency         : 20%  - Last 30d: 20, 31-90d: 15, 91-180d: 10, Older: 5
    Engagement      : 15%  - Active: 15, Passive: 10, New: 8, Unresponsive: 0
"""
from datetime import datetime, timedelta
from typing import Optional
from app.config import logger


# ============================================
# WEIGHT CONSTANTS
# ============================================
WEIGHT_PHONE_VALIDITY = 40
WEIGHT_COMPLETENESS = 25
WEIGHT_RECENCY = 20
WEIGHT_ENGAGEMENT = 15


def score_contact(contact: dict, engagement_history: Optional[dict] = None) -> int:
    """
    Assign a quality score (0-100) to a single contact.

    Args:
        contact: Contact dict with keys: phone, name, email, is_valid (bool),
                 last_seen (ISO datetime string, optional), custom_fields (dict)
        engagement_history: Optional dict with keys:
            - status: "active" | "passive" | "new" | "unresponsive"

    Returns:
        int: Quality score 0-100
    """
    score = 0

    # 1. Phone Validity (40%)
    is_valid = contact.get("is_valid", True)
    if is_valid:
        score += WEIGHT_PHONE_VALIDITY

    # 2. Completeness (25%)
    has_phone = bool(contact.get("phone"))
    has_name = bool(contact.get("name"))
    has_email = bool(contact.get("email"))

    if has_phone and has_name and has_email:
        score += 25
    elif has_phone and has_name:
        score += 15
    elif has_phone:
        score += 5

    # 3. Recency (20%)
    last_seen_str = contact.get("last_seen")
    if last_seen_str:
        try:
            last_seen = datetime.fromisoformat(last_seen_str)
            days_ago = (datetime.utcnow() - last_seen).days

            if days_ago <= 30:
                score += 20
            elif days_ago <= 90:
                score += 15
            elif days_ago <= 180:
                score += 10
            else:
                score += 5
        except (ValueError, TypeError):
            score += 15  # Default if parse fails
    else:
        score += 15  # Default when no last_seen data

    # 4. Engagement History (15%)
    if engagement_history:
        status = engagement_history.get("status", "new")
        engagement_scores = {
            "active": 15,
            "passive": 10,
            "new": 8,
            "unresponsive": 0,
        }
        score += engagement_scores.get(status, 8)
    else:
        score += 8  # Default: treat as "new"

    return min(score, 100)


def score_contacts(contacts: list) -> list:
    """
    Add quality_score field to each contact in the list.

    Args:
        contacts: List of contact dicts

    Returns:
        list: Same contacts with quality_score field added
    """
    logger.info(f"Scoring {len(contacts)} contacts for quality")

    for contact in contacts:
        contact["quality_score"] = score_contact(contact)

    # Log quality distribution
    if contacts:
        scores = [c["quality_score"] for c in contacts]
        avg = sum(scores) / len(scores)
        high = sum(1 for s in scores if s >= 70)
        medium = sum(1 for s in scores if 40 <= s < 70)
        low = sum(1 for s in scores if s < 40)

        logger.info(
            f"Quality distribution: avg={avg:.1f}, "
            f"high(>=70)={high}, medium(40-69)={medium}, low(<40)={low}"
        )

    return contacts
