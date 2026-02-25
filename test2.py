"""
Shared retrieval tools used by drafting agents.

Current usage:
- Shared vector/RAG lookup across drafting agents.
"""
from __future__ import annotations
import concurrent.futures
import json
from langchain.tools import tool
from app.config import logger
from app.database.vectordatabse.qudrant import (
    search_qdrant_books,
)

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)


def _run_rag_search_sync(query: str, collection_name: str = "all", top_k: int = 5):
    """Search Qdrant vector DB for relevant legal documents."""
    try:
        return search_qdrant_books(
            query=query,
            collection_name="legal_books_cpc",
            top_k=top_k,
        )
    except Exception as e:
        return {"status": "failed", "error": str(e), "results": []}
        

x=_run_rag_search_sync("Civil suit", "all", 5)
print(x)