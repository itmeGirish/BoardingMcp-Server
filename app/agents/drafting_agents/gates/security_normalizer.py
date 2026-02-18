"""
Security Normalizer Gate  (CLAUD.md Step 1) -- Rule-based, NO LLM calls.

Prevents prompt injection, strips unsafe content, normalises text,
and enforces input size limits before anything else in the pipeline.
"""

import re
import unicodedata
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_WORD_COUNT = 10_000

# HTML / script tags  (greedy across lines)
_HTML_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)

# Zero-width / invisible Unicode characters
_INVISIBLE_CHARS = frozenset([
    "\u200b",  # ZERO WIDTH SPACE
    "\u200c",  # ZERO WIDTH NON-JOINER
    "\u200d",  # ZERO WIDTH JOINER
    "\u200e",  # LEFT-TO-RIGHT MARK
    "\u200f",  # RIGHT-TO-LEFT MARK
    "\u2060",  # WORD JOINER
    "\u2061",  # FUNCTION APPLICATION
    "\u2062",  # INVISIBLE TIMES
    "\u2063",  # INVISIBLE SEPARATOR
    "\u2064",  # INVISIBLE PLUS
    "\ufeff",  # ZERO WIDTH NO-BREAK SPACE (BOM)
    "\ufff9",  # INTERLINEAR ANNOTATION ANCHOR
    "\ufffa",  # INTERLINEAR ANNOTATION SEPARATOR
    "\ufffb",  # INTERLINEAR ANNOTATION TERMINATOR
])

# Prompt-injection patterns (case-insensitive)
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?above\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous\s+(instructions|context)", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+(above|before)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),
    re.compile(r"\bDAN\s+mode\b", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"override\s+(safety|instructions|rules)", re.IGNORECASE),
    re.compile(r"act\s+as\s+if\s+you\s+have\s+no\s+restrictions", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|to\s+be)\s+", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Remove all HTML / script tags."""
    return _HTML_TAG_RE.sub("", text)


def _remove_invisible_chars(text: str) -> str:
    """Remove zero-width and invisible Unicode characters."""
    return "".join(ch for ch in text if ch not in _INVISIBLE_CHARS)


def _normalise_whitespace(text: str) -> str:
    """Collapse runs of whitespace to a single space, strip edges."""
    return re.sub(r"\s+", " ", text).strip()


def _normalise_unicode(text: str) -> str:
    """Normalise to NFC form to prevent homoglyph attacks."""
    return unicodedata.normalize("NFC", text)


def _detect_injections(text: str) -> list[str]:
    """Return list of matched injection pattern descriptions."""
    events: list[str] = []
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            events.append(f"prompt_injection_detected: '{match.group()}'")
    return events


def _sanitize_text(text: str) -> tuple[str, list[str]]:
    """
    Run the full sanitisation pipeline on a single text string.
    Returns (sanitised_text, security_events).
    """
    events: list[str] = []

    if not text:
        return "", events

    # 1. Detect injections BEFORE stripping (we want the raw match)
    injection_hits = _detect_injections(text)
    events.extend(injection_hits)

    # 2. Strip HTML / script tags
    cleaned = _strip_html(text)

    # 3. Remove invisible unicode
    cleaned = _remove_invisible_chars(cleaned)

    # 4. Normalise unicode (NFC)
    cleaned = _normalise_unicode(cleaned)

    # 5. Remove the injection phrases themselves
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    # 6. Normalise whitespace
    cleaned = _normalise_whitespace(cleaned)

    return cleaned, events


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sanitize_input(
    user_query: str,
    uploaded_docs: list[dict] | None = None,
) -> dict:
    """
    Security + normalisation gate (Step 1).

    Pure rule-based -- no LLM calls.

    Args:
        user_query:    Raw user query string.
        uploaded_docs: Optional list of document dicts, each with at least
                       ``doc_id``, ``file_name``, ``doc_text``.

    Returns:
        dict with keys:
            gate               - "security_normalizer"
            passed             - bool (False if query exceeds word limit or
                                 injection was detected)
            sanitized_query    - cleaned query string
            sanitized_docs     - list of cleaned doc dicts
            security_events    - list of event descriptions
            metadata           - {word_count, doc_count}
    """
    all_events: list[str] = []

    # --- sanitise user query ---
    sanitized_query, query_events = _sanitize_text(user_query or "")
    all_events.extend(query_events)

    # --- enforce word limit on query ---
    word_count = len(sanitized_query.split()) if sanitized_query else 0
    if word_count > MAX_WORD_COUNT:
        all_events.append(
            f"word_limit_exceeded: {word_count} words (max {MAX_WORD_COUNT})"
        )
        # Truncate to MAX_WORD_COUNT words
        sanitized_query = " ".join(sanitized_query.split()[:MAX_WORD_COUNT])
        word_count = MAX_WORD_COUNT

    # --- sanitise uploaded documents ---
    sanitized_docs: list[dict] = []
    if uploaded_docs:
        for doc in uploaded_docs:
            doc_text = doc.get("doc_text", "")
            cleaned_text, doc_events = _sanitize_text(doc_text)
            if doc_events:
                for evt in doc_events:
                    all_events.append(f"doc[{doc.get('doc_id', '?')}]: {evt}")

            # enforce word limit per document
            doc_words = len(cleaned_text.split()) if cleaned_text else 0
            if doc_words > MAX_WORD_COUNT:
                all_events.append(
                    f"doc[{doc.get('doc_id', '?')}]: word_limit_exceeded: "
                    f"{doc_words} words (max {MAX_WORD_COUNT})"
                )
                cleaned_text = " ".join(cleaned_text.split()[:MAX_WORD_COUNT])

            sanitized_docs.append({
                "doc_id": doc.get("doc_id", ""),
                "file_name": doc.get("file_name", ""),
                "doc_text": cleaned_text,
            })

    # --- determine pass / fail ---
    # Fail if any injection was detected or word limit was exceeded
    has_injection = any("prompt_injection_detected" in e for e in all_events)
    has_word_limit = any("word_limit_exceeded" in e for e in all_events)
    passed = not has_injection and not has_word_limit

    return {
        "gate": "security_normalizer",
        "passed": passed,
        "sanitized_query": sanitized_query,
        "sanitized_docs": sanitized_docs,
        "security_events": all_events,
        "metadata": {
            "word_count": word_count,
            "doc_count": len(sanitized_docs),
            "sanitized_at": datetime.now(timezone.utc).isoformat(),
        },
    }
