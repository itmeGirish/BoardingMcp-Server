"""
Rule Classifier Gate  (CLAUD.md Step 4A) -- Rule-based, NO LLM calls.

Fast preliminary classification of legal domain, document type, and
court type using keyword / pattern matching against facts and the user
query.
"""

import re

# ---------------------------------------------------------------------------
# Keyword patterns  (domain -> list of trigger keywords / phrases)
# ---------------------------------------------------------------------------

KEYWORD_PATTERNS: dict[str, list[str]] = {
    "criminal": [
        "bail", "FIR", "arrest", "accused", "CrPC", "IPC",
        "chargesheet", "charge sheet", "remand", "anticipatory",
        "cognizable", "non-bailable", "bailable", "police station",
        "investigation", "crime number", "section 439",
        "section 437", "quashing", "abscond", "surrender",
        "custody", "criminal", "offence", "offense",
        "prosecution", "complainant accused", "BNSS", "BNS",
    ],
    "civil": [
        "suit", "plaint", "decree", "injunction",
        "specific relief", "CPC", "damages", "mesne profits",
        "declaratory", "permanent injunction", "temporary injunction",
        "order VII", "order XXXIX", "civil suit", "recovery suit",
        "money suit",
    ],
    "family": [
        "divorce", "maintenance", "custody", "marriage",
        "Hindu Marriage Act", "alimony", "restitution of conjugal rights",
        "judicial separation", "domestic violence", "DV Act",
        "protection order", "dowry", "child custody",
        "guardian", "guardianship", "adoption", "Muslim Women",
        "Special Marriage Act", "Hindu Succession",
    ],
    "commercial": [
        "company", "arbitration", "commercial court",
        "partnership", "insolvency", "IBC", "NCLT", "NCLAT",
        "winding up", "liquidation", "corporate",
        "shareholder", "director", "LLP", "commercial dispute",
        "cheque bounce", "section 138", "NI Act",
        "Negotiable Instruments Act",
    ],
    "property": [
        "land", "title", "possession", "easement",
        "partition", "eviction", "rent control",
        "landlord", "tenant", "lease", "trespass",
        "encroachment", "mutation", "revenue records",
        "specific performance", "sale deed", "gift deed",
        "property dispute", "immovable property",
    ],
    "constitutional": [
        "fundamental rights", "article 226", "writ",
        "habeas corpus", "mandamus", "certiorari",
        "prohibition", "quo warranto", "article 32",
        "constitutional", "PIL", "public interest litigation",
        "violation of rights", "right to life", "article 21",
        "article 14", "equality", "discrimination",
    ],
    "consumer": [
        "consumer", "deficiency of service", "unfair trade practice",
        "consumer protection", "NCDRC", "District Forum",
        "State Commission", "consumer complaint",
        "product liability", "service provider",
    ],
    "labour": [
        "employment", "termination of service", "reinstatement",
        "labour court", "industrial dispute", "workman",
        "employer", "retrenchment", "gratuity", "provident fund",
        "EPFO", "ESI", "labour", "labor",
        "unfair labour practice", "standing orders",
    ],
    "arbitration": [
        "arbitration", "arbitral tribunal", "arbitrator",
        "section 11", "section 9", "section 34",
        "Arbitration and Conciliation Act", "arbitral award",
        "interim measures", "enforcement of award",
    ],
}

# ---------------------------------------------------------------------------
# Document-type patterns  (doc_type -> trigger phrases)
# ---------------------------------------------------------------------------

DOC_TYPE_PATTERNS: dict[str, list[str]] = {
    "Bail Application": [
        "bail application", "regular bail", "anticipatory bail",
        "interim bail", "default bail", "section 439", "section 437",
        "section 438",
    ],
    "Writ Petition": [
        "writ petition", "article 226", "article 32",
        "writ of mandamus", "writ of certiorari",
        "writ of habeas corpus", "writ of prohibition",
        "quo warranto",
    ],
    "Complaint u/s 138 NI Act": [
        "section 138", "cheque bounce", "cheque dishonour",
        "NI Act", "Negotiable Instruments",
    ],
    "Divorce Petition": [
        "divorce petition", "dissolution of marriage",
        "Hindu Marriage Act", "section 13",
    ],
    "Civil Suit": [
        "civil suit", "plaint", "suit for",
        "money suit", "recovery suit",
    ],
    "Injunction Application": [
        "injunction", "temporary injunction", "permanent injunction",
        "order XXXIX", "restraining order",
    ],
    "Quashing Petition": [
        "quashing", "section 482", "quash FIR",
        "quash proceedings", "inherent powers",
    ],
    "Appeal": [
        "appeal", "first appeal", "second appeal",
        "criminal appeal", "civil appeal",
    ],
    "Revision Petition": [
        "revision", "revision petition", "section 397",
        "section 401",
    ],
    "Arbitration Petition": [
        "arbitration petition", "section 11",
        "appointment of arbitrator", "section 9 application",
        "section 34 application",
    ],
    "Legal Notice": [
        "legal notice", "demand notice", "cease and desist",
        "show cause",
    ],
    "Contract": [
        "contract", "agreement", "terms and conditions",
        "memorandum of understanding", "MOU",
    ],
    "NDA": [
        "non-disclosure", "NDA", "confidentiality agreement",
        "confidential information",
    ],
}

# ---------------------------------------------------------------------------
# Court-type patterns  (court_type -> trigger phrases)
# ---------------------------------------------------------------------------

COURT_TYPE_PATTERNS: dict[str, list[str]] = {
    "HighCourt": [
        "high court", "article 226", "writ petition",
        "criminal appeal", "civil revision",
        "section 482", "quashing",
    ],
    "Sessions": [
        "sessions court", "sessions judge",
        "section 439", "regular bail",
        "criminal miscellaneous",
    ],
    "Magistrate": [
        "magistrate", "JMFC", "CJM",
        "section 437", "section 138",
        "complaint case",
    ],
    "CivilCourt": [
        "civil court", "civil judge",
        "senior division", "junior division",
        "original suit", "civil suit",
    ],
    "Tribunal": [
        "tribunal", "NCLT", "NCLAT", "NCDRC",
        "consumer forum", "labour court",
        "DRT", "DRAT", "ITAT", "SAT",
    ],
    "SupremeCourt": [
        "supreme court", "article 32", "SLP",
        "special leave petition",
    ],
    "DistrictCourt": [
        "district court", "district judge",
        "principal district judge",
    ],
    "FamilyCourt": [
        "family court", "family judge",
        "matrimonial", "divorce court",
    ],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _match_keywords(
    text: str,
    patterns: dict[str, list[str]],
) -> tuple[str | None, float, list[str]]:
    """
    Match *text* against a keyword-pattern dict.

    Returns:
        (best_match_key, confidence, matched_keywords)
    """
    text_lower = text.lower()
    scores: dict[str, list[str]] = {}

    for key, keywords in patterns.items():
        matched: list[str] = []
        for kw in keywords:
            # Use word-boundary-aware search for short keywords,
            # plain substring for multi-word phrases
            if " " in kw:
                if kw.lower() in text_lower:
                    matched.append(kw)
            else:
                if re.search(rf"\b{re.escape(kw)}\b", text_lower, re.IGNORECASE):
                    matched.append(kw)
        if matched:
            scores[key] = matched

    if not scores:
        return None, 0.0, []

    # Pick the key with the most keyword hits
    best_key = max(scores, key=lambda k: len(scores[k]))
    best_matched = scores[best_key]

    # Confidence heuristic: min(hits / 3, 1.0) capped at 0.90
    # (rule classifier should never claim >0.90 -- leave room for LLM)
    confidence = min(len(best_matched) / 3.0, 0.90)
    confidence = round(confidence, 2)

    return best_key, confidence, best_matched


def _build_search_text(facts: list[dict], user_query: str) -> str:
    """Combine facts + user query into a single search string."""
    parts = [user_query]
    for fact in facts:
        parts.append(fact.get("text", ""))
        parts.append(fact.get("fact_value", ""))
        parts.append(fact.get("fact_key", ""))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_by_rules(
    facts: list[dict],
    user_query: str,
) -> dict:
    """
    Rule-based legal classifier (Step 4A).

    Pure keyword / pattern matching -- no LLM calls.

    Args:
        facts:      List of fact dicts (with ``text`` or ``fact_value``).
        user_query: The user's raw (or sanitised) query string.

    Returns:
        dict with keys:
            gate                - "rule_classifier"
            legal_domain_guess  - str | None
            court_type_guess    - str | None
            doc_type_guess      - str | None
            confidence          - float (0.0 - 0.90)
            matched_keywords    - list[str]
    """
    search_text = _build_search_text(facts, user_query)

    # --- domain ---
    domain_guess, domain_conf, domain_kws = _match_keywords(
        search_text, KEYWORD_PATTERNS,
    )

    # --- doc type ---
    doc_type_guess, doc_conf, doc_kws = _match_keywords(
        search_text, DOC_TYPE_PATTERNS,
    )

    # --- court type ---
    court_guess, court_conf, court_kws = _match_keywords(
        search_text, COURT_TYPE_PATTERNS,
    )

    # Aggregate all matched keywords (deduplicated, preserving order)
    seen: set[str] = set()
    all_matched: list[str] = []
    for kw in domain_kws + doc_kws + court_kws:
        if kw not in seen:
            seen.add(kw)
            all_matched.append(kw)

    # Overall confidence = weighted average of sub-confidences
    weights = []
    if domain_conf > 0:
        weights.append(domain_conf)
    if doc_conf > 0:
        weights.append(doc_conf)
    if court_conf > 0:
        weights.append(court_conf)

    overall_confidence = round(sum(weights) / max(len(weights), 1), 2)

    return {
        "gate": "rule_classifier",
        "legal_domain_guess": domain_guess,
        "court_type_guess": court_guess,
        "doc_type_guess": doc_type_guess,
        "confidence": overall_confidence,
        "matched_keywords": all_matched,
    }
