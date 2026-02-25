"""
Reusable Brave web search helper.

This module is shared by research workflows and should not contain
hardcoded credentials.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import requests


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fed: list[str] = []

    def handle_data(self, d: str) -> None:
        self.fed.append(d)

    def get_data(self) -> str:
        return "".join(self.fed)


def _strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html or "")
    return s.get_data()


_HIGH_AUTHORITY_DOMAINS = {
    "indiankanoon.org",
    "sci.gov.in",
    "main.sci.gov.in",
    "ecourts.gov.in",
    "legislative.gov.in",
    "egazette.nic.in",
    "indiacode.nic.in",
}

_LEGAL_DB_DOMAINS = {
    "scconline.com",
    "manupatra.com",
    "casemine.com",
}

_LOW_AUTHORITY_HINTS = {
    "blog",
    "medium.com",
    "wordpress.com",
    "blogspot.com",
}


def _extract_domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().replace("www.", "")
    except Exception:
        return ""


def _extract_path(url: str) -> str:
    try:
        return (urlparse(url).path or "").lower()
    except Exception:
        return ""


def _classify_source(domain: str) -> tuple[str, int]:
    if (
        domain in _HIGH_AUTHORITY_DOMAINS
        or domain.endswith(".gov.in")
        or domain.endswith("indiacode.nic.in")
        or domain.endswith("ecourts.gov.in")
    ):
        return "official_legal_source", 100
    if domain in _LEGAL_DB_DOMAINS:
        return "legal_database", 90
    if any(h in domain for h in _LOW_AUTHORITY_HINTS):
        return "blog_or_low_authority", 25
    return "general_web", 50


def _looks_legal_text(title: str, snippet: str) -> bool:
    text = f"{title} {snippet}".lower()
    legal_markers = [
        "section",
        "act",
        "judgment",
        "supreme court",
        "high court",
        "limitation",
        "legal notice",
        "petition",
        "plaint",
        "affidavit",
        "tribunal",
    ]
    return any(m in text for m in legal_markers)


def _looks_blog_like(url: str, title: str) -> bool:
    path = _extract_path(url)
    text = f"{title} {path}".lower()
    blog_markers = [
        "/blog",
        " blog ",
        "medium.com",
        "blogspot.com",
        "wordpress.com",
    ]
    return any(m in text for m in blog_markers)


def web_search_tool(
    query: str,
    brave_api_key: str,
    count: int = 5,
    strict_legal: bool = True,
    authoritative_only: bool = True,
) -> dict[str, Any]:
    """
    Query Brave web search API and return normalized result payload.

    Returns:
      {
        "status": "success|failed",
        "results": [
          {
            "title",
            "url",
            "snippet",
            "published_at",
            "domain",
            "source_type",
            "authority_score"
          }, ...
        ],
        "count": int,
        "error": str (on failed)
      }
    """
    if not brave_api_key:
        return {"status": "failed", "error": "Brave API key not configured", "results": []}

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "x-subscription-token": brave_api_key,
    }
    params = {"q": query, "count": count}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        raw_results = response.json().get("web", {}).get("results", [])
    except Exception as e:
        return {"status": "failed", "error": str(e), "results": []}

    def _collect() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in raw_results:
            title = item.get("title", "") or ""
            url = item.get("url", "") or ""
            snippet = _strip_html(item.get("description", ""))
            published_at = item.get("published", "")
            domain = _extract_domain(url)
            source_type, authority_score = _classify_source(domain)

            if strict_legal:
                if source_type == "blog_or_low_authority":
                    continue
                if _looks_blog_like(url, title) and authority_score < 90:
                    continue
                if source_type == "general_web" and not _looks_legal_text(title, snippet):
                    continue
                if authoritative_only and source_type not in {"official_legal_source", "legal_database"}:
                    continue

            rows.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "published_at": published_at,
                    "domain": domain,
                    "source_type": source_type,
                    "authority_score": authority_score,
                }
            )
        return rows

    formatted = _collect()

    # Rank by authority first; then keep top `count`.
    formatted.sort(key=lambda r: r.get("authority_score", 0), reverse=True)
    formatted = formatted[:count]

    return {"status": "success", "results": formatted, "count": len(formatted)}
