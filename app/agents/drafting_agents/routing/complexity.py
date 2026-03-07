"""Complexity scoring — deterministic, no LLM.

Scores user prompts from 4-12 and assigns a tier: SIMPLE, MEDIUM, COMPLEX.
Used by Stage 0 Input Gate for model routing.
"""
from __future__ import annotations

import re
from typing import Literal, Tuple

Tier = Literal["SIMPLE", "MEDIUM", "COMPLEX"]

# Cause type complexity weights (from keyword scan)
CAUSE_WEIGHTS: dict[str, int] = {
    "money_recovery_loan": 1,
    "money_recovery_goods": 1,
    "failure_of_consideration": 1,
    "money_recovery_cheque": 1,
    "summary_suit_cheque": 1,
    "ni_138_complaint": 1,
    "breach_of_contract": 2,
    "injunction_suit": 2,
    "specific_performance": 2,
    "defamation_suit": 2,
    "eviction_suit": 2,
    "rent_recovery": 1,
    "breach_dealership_franchise": 3,
    "partition": 3,
    "motor_accident": 3,
    "partnership_dissolution": 3,
    "matrimonial_dispute": 2,
    "consumer_complaint": 2,
}

# Keywords that suggest specific cause types
_CAUSE_KEYWORDS: dict[str, list[str]] = {
    "money_recovery_loan": ["loan", "lent", "advance", "repay"],
    "money_recovery_goods": ["goods sold", "delivered", "supply"],
    "failure_of_consideration": ["failure of consideration", "section 65"],
    "ni_138_complaint": ["cheque bounce", "dishonour", "138", "negotiable"],
    "summary_suit_cheque": ["summary suit", "order 37"],
    "breach_of_contract": ["breach", "contract", "agreement"],
    "breach_dealership_franchise": ["dealership", "franchise", "agency agreement", "termination of dealer"],
    "partition": ["partition", "co-owner", "joint property", "ancestral"],
    "injunction_suit": ["injunction", "restrain", "prohibit"],
    "specific_performance": ["specific performance", "execute", "conveyance"],
    "defamation_suit": ["defamation", "defame", "libel", "slander"],
    "motor_accident": ["motor accident", "vehicle", "road accident"],
    "partnership_dissolution": ["partnership", "dissolution", "partner"],
    "eviction_suit": ["eviction", "tenant", "landlord", "vacate"],
    "rent_recovery": ["rent", "arrears", "lease"],
}

# Damage-related keywords
_DAMAGE_KEYWORDS = [
    "profit", "goodwill", "stock", "expenditure",
    "consequential", "interest", "penalty", "rent",
    "compensation", "loss", "damages",
]


def _keyword_scan(text: str) -> str | None:
    """Scan text for keywords to guess probable cause type."""
    text_lower = text.lower()
    best_match = None
    best_count = 0
    for cause_type, keywords in _CAUSE_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_match = cause_type
    return best_match


def compute_complexity(user_prompt: str) -> Tuple[int, Tier]:
    """Compute complexity score (4-12) and tier from user prompt.

    All factors are deterministic — no LLM call.

    Returns:
        (score, tier) where tier is SIMPLE (4-6), MEDIUM (7-9), COMPLEX (10-12)
    """
    score = 0
    text_lower = user_prompt.lower()

    # Factor 1: Cause type weight (from keyword scan)
    probable_cause = _keyword_scan(user_prompt)
    score += CAUSE_WEIGHTS.get(probable_cause or "", 2)

    # Factor 2: Party count
    party_indicators = len(re.findall(
        r'\b(?:plaintiff|defendant|respondent|petitioner|applicant)\b',
        text_lower,
    ))
    score += min(party_indicators, 3)

    # Factor 3: Damage heads mentioned
    damage_count = sum(1 for kw in _DAMAGE_KEYWORDS if kw in text_lower)
    score += min(damage_count, 3)

    # Factor 4: Prompt length (proxy for case complexity)
    word_count = len(user_prompt.split())
    if word_count < 100:
        score += 1
    elif word_count < 300:
        score += 2
    else:
        score += 3

    # Clamp to 4-12 range
    score = max(4, min(12, score))

    # Tier assignment
    if score <= 6:
        tier: Tier = "SIMPLE"
    elif score <= 9:
        tier = "MEDIUM"
    else:
        tier = "COMPLEX"

    return score, tier
