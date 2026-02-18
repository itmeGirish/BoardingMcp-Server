"""
Citation Confidence Gate — Rule-based, NO LLM calls.

Verifies that all citations meet the confidence threshold (>= 0.75)
or have a source_doc_id for verification.
"""

CONFIDENCE_THRESHOLD = 0.75


def check_citation_confidence(citations: list[dict]) -> dict:
    """
    Rule-based check: Do all citations meet confidence requirements?

    A citation passes if:
    - confidence >= 0.75, OR
    - source_doc_id is present (externally verified)

    Args:
        citations: List of citation dicts with 'confidence' and 'source_doc_id' fields

    Returns:
        dict with 'passed', 'low_confidence_citations', 'details'
    """
    if not citations:
        return {
            "gate": "citation_confidence",
            "passed": True,
            "low_confidence_citations": [],
            "details": {"total_citations": 0, "message": "No citations to validate"},
        }

    low_confidence = []
    for citation in citations:
        confidence = citation.get("confidence", 0.0)
        source_doc_id = citation.get("source_doc_id")

        if confidence < CONFIDENCE_THRESHOLD and not source_doc_id:
            low_confidence.append({
                "citation_text": citation.get("citation_text", "unknown"),
                "confidence": confidence,
                "source_doc_id": source_doc_id,
            })

    passed = len(low_confidence) == 0

    details = {
        "total_citations": len(citations),
        "passing_citations": len(citations) - len(low_confidence),
        "failing_citations": len(low_confidence),
        "threshold": CONFIDENCE_THRESHOLD,
        "low_confidence_citations": low_confidence,
    }

    return {
        "gate": "citation_confidence",
        "passed": passed,
        "low_confidence_citations": low_confidence,
        "details": details,
    }


def verify_citation_hashes(
    citations: list[dict],
    verified_hashes: set[str],
) -> dict:
    """
    Hash-based citation verification (CLAUDE.md Section 2.2).

    A citation is valid ONLY if:
    - It has a verification_hash (or citation_hash), AND
    - That hash exists in the verified_hashes set (from DB)

    Citations without a hash or with an unknown hash are DISCARDED.

    Args:
        citations:       List of citation dicts.
        verified_hashes: Set of hashes from verified_citations DB.

    Returns:
        dict with 'passed', 'verified_citations', 'discarded_citations', 'details'
    """
    if not citations:
        return {
            "gate": "citation_hash_verification",
            "passed": True,
            "verified_citations": [],
            "discarded_citations": [],
            "details": {"total": 0, "verified": 0, "discarded": 0},
        }

    verified = []
    discarded = []

    for c in citations:
        c_hash = c.get("verification_hash") or c.get("citation_hash")
        if c_hash and c_hash in verified_hashes:
            verified.append(c)
        else:
            discarded.append({
                "citation_text": c.get("citation_text", "unknown"),
                "reason": "no_hash" if not c_hash else "hash_not_in_verified_db",
            })

    return {
        "gate": "citation_hash_verification",
        "passed": len(discarded) == 0,
        "verified_citations": verified,
        "discarded_citations": discarded,
        "details": {
            "total": len(citations),
            "verified": len(verified),
            "discarded": len(discarded),
        },
    }
