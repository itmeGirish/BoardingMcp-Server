"""
Reusable Qdrant ingestion/search helpers for legal books.

This module supports:
1) Ingesting all books under ``books/`` into Qdrant
2) Auto-routing each book into a separate domain collection
3) Querying one collection or all managed collections
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Iterable

from app.config import logger, settings

BOOK_FILE_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}
DEFAULT_COLLECTION_PREFIX = "legal_books_"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"

# Ordered: first match wins.
BOOK_COLLECTION_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("bns_ipc_comparison", ("comparison", "bns to ipc", "ipc")),
    ("bnss", ("bnss", "crpc")),
    ("bsa", ("bsa", "evidence")),
    ("bns", ("bns", "nyaya")),
    ("cpc", ("cpc", "civil procedure", "mulla")),
    ("pleading", ("pleading",)),
]


def _unwrap_secret(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "get_secret_value"):
        try:
            secret = value.get_secret_value()
            return str(secret).strip() if secret else None
        except Exception:
            return None
    text = str(value).strip()
    return text or None


def _get_setting(*names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(settings, name):
            value = getattr(settings, name)
            normalized = _unwrap_secret(value)
            if normalized is not None:
                return normalized
        lower = name.lower()
        if hasattr(settings, lower):
            value = getattr(settings, lower)
            normalized = _unwrap_secret(value)
            if normalized is not None:
                return normalized
    return default


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "misc"


def _clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if not text:
        return []

    if chunk_size <= 0:
        chunk_size = 1200
    if overlap < 0:
        overlap = 0
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 5)

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks


def resolve_collection_name(
    book_name: str,
    collection_prefix: str = DEFAULT_COLLECTION_PREFIX,
) -> str:
    lowered = book_name.lower()
    for bucket, keywords in BOOK_COLLECTION_RULES:
        if any(keyword in lowered for keyword in keywords):
            return f"{collection_prefix}{bucket}"
    return f"{collection_prefix}{_slugify(Path(book_name).stem)}"


def _discover_book_files(books_dir: Path) -> list[Path]:
    return sorted(
        file_path
        for file_path in books_dir.rglob("*")
        if file_path.is_file() and file_path.suffix.lower() in BOOK_FILE_EXTENSIONS
    )


def _extract_chunks_from_pdf(
    file_path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    global_index = 0

    def _append_page_chunks(page_text: str, page_number: int) -> None:
        nonlocal global_index
        text = _clean_text(page_text or "")
        if not text:
            return
        page_chunks = _chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        for local_index, chunk in enumerate(page_chunks):
            chunks.append(
                {
                    "text": chunk,
                    "page_number": page_number,
                    "page_chunk_index": local_index,
                    "chunk_index": global_index,
                }
            )
            global_index += 1

    # Preferred parser: pypdf
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        for page_number, page in enumerate(reader.pages, start=1):
            _append_page_chunks(page.extract_text() or "", page_number)
        return chunks
    except ImportError:
        pass

    # Fallback parser: pdfplumber (available in this repository environment)
    try:
        import pdfplumber

        with pdfplumber.open(str(file_path)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                _append_page_chunks(page.extract_text() or "", page_number)
        return chunks
    except ImportError as exc:
        raise RuntimeError(
            "No PDF parser found. Install `pypdf` or `pdfplumber`."
        ) from exc


def _extract_chunks_from_text_file(
    file_path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict[str, Any]]:
    text = _clean_text(file_path.read_text(encoding="utf-8", errors="ignore"))
    chunks = _chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
    return [
        {
            "text": chunk,
            "page_number": None,
            "page_chunk_index": idx,
            "chunk_index": idx,
        }
        for idx, chunk in enumerate(chunks)
    ]


def _extract_book_chunks(
    file_path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict[str, Any]]:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_chunks_from_pdf(file_path, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return _extract_chunks_from_text_file(file_path, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


_qdrant_client_cache: "Any | None" = None
_qdrant_client_error: "str | None" = None
_qdrant_client_built: bool = False


def _build_qdrant_client():
    global _qdrant_client_cache, _qdrant_client_error, _qdrant_client_built
    if _qdrant_client_built:
        return _qdrant_client_cache, _qdrant_client_error

    try:
        from qdrant_client import QdrantClient
    except ImportError:
        _qdrant_client_error = "qdrant_client not installed"
        _qdrant_client_built = True
        return None, _qdrant_client_error

    url = _get_setting("QDRANT_CLIENT_URL", "QUADRANT_CLIENT_URL")
    api_key = _get_setting("QDRANT_API_KEY", "QUADRANT_API_KEY")
    if not url:
        _qdrant_client_error = "Qdrant URL not configured (QDRANT_CLIENT_URL)"
        _qdrant_client_built = True
        return None, _qdrant_client_error

    timeout_value = _get_setting("QDRANT_TIMEOUT_SECONDS", default=120)
    try:
        timeout_seconds = float(timeout_value)
    except (TypeError, ValueError):
        timeout_seconds = 120.0

    # No health-check ping here — the first real query will reveal connectivity issues.
    _qdrant_client_cache = QdrantClient(url=url, api_key=api_key, timeout=timeout_seconds)
    _qdrant_client_built = True
    return _qdrant_client_cache, None


_embed_client_cache: "tuple[Any, str, Any] | None" = None
_embed_client_built: bool = False


def _build_embedding_client():
    global _embed_client_cache, _embed_client_built
    if _embed_client_built:
        return _embed_client_cache  # type: ignore[return-value]

    # Prefer OpenAI API key in this repository.
    openai_api_key = _get_setting("OPENAI_API_KEY")
    if openai_api_key:
        try:
            from openai import OpenAI
        except ImportError:
            return None, None, "openai package not installed"

        model_name = _get_setting("OPENAI_EMBEDDING_MODEL", default=DEFAULT_EMBED_MODEL)
        client = OpenAI(api_key=openai_api_key)
        _embed_client_cache = (client, str(model_name), None)
        _embed_client_built = True
        return client, str(model_name), None

    # Backward compatibility path for Azure envs.
    azure_api_key = _get_setting("AZURE_OPENAI_API_KEY", "azure_openai_api_key")
    azure_endpoint = _get_setting("AZURE_OPENAI_ENDPOINT", "azure_openai_endpoint")
    azure_deployment = _get_setting(
        "AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING",
        "azure_openai_deployment_name_embedding",
    )
    if azure_api_key and azure_endpoint and azure_deployment:
        try:
            from openai import AzureOpenAI
        except ImportError:
            return None, None, "openai package not installed"

        client = AzureOpenAI(
            api_key=azure_api_key,
            azure_endpoint=azure_endpoint,
            api_version="2024-02-01",
        )
        return client, str(azure_deployment), None

    return None, None, "Embedding provider not configured (OPENAI_API_KEY or Azure embedding settings)"


def _embed_texts(client: Any, model_name: str, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=model_name, input=texts)
    return [row.embedding for row in response.data]


def _ensure_collection(
    qdrant_client: Any,
    collection_name: str,
    vector_size: int,
    recreate: bool,
) -> None:
    from qdrant_client.models import Distance, VectorParams

    if recreate:
        qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        return

    try:
        qdrant_client.get_collection(collection_name=collection_name)
    except Exception:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def _iter_batches(items: list[Any], batch_size: int) -> Iterable[list[Any]]:
    if batch_size <= 0:
        batch_size = 64
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def ingest_books_to_qdrant(
    books_dir: str | Path = "books",
    recreate_collections: bool = False,
    collection_prefix: str = DEFAULT_COLLECTION_PREFIX,
    chunk_size: int = 2400,
    chunk_overlap: int = 240,
    embed_batch_size: int = 64,
    upsert_batch_size: int = 8,
) -> dict[str, Any]:
    """
    Ingest all supported books into Qdrant, grouped into collection buckets.
    """
    books_path = Path(books_dir).resolve()
    if not books_path.exists():
        return {
            "status": "failed",
            "message": f"Books directory not found: {books_path}",
            "books_processed": 0,
        }

    qdrant_client, qdrant_error = _build_qdrant_client()
    if qdrant_error:
        return {"status": "skipped", "message": qdrant_error, "books_processed": 0}

    embedding_client, embedding_model, embed_error = _build_embedding_client()
    if embed_error:
        return {"status": "skipped", "message": embed_error, "books_processed": 0}

    from qdrant_client.models import PointStruct

    files = _discover_book_files(books_path)
    if not files:
        return {
            "status": "skipped",
            "message": f"No book files found in {books_path}",
            "books_processed": 0,
        }

    summary: dict[str, Any] = {
        "status": "success",
        "books_dir": str(books_path),
        "books_discovered": len(files),
        "books_processed": 0,
        "books_failed": 0,
        "collections_touched": [],
        "collection_stats": {},
        "total_chunks_upserted": 0,
        "errors": [],
    }

    recreated_collections: set[str] = set()
    initialized_collections: set[str] = set()

    for file_path in files:
        try:
            collection_name = resolve_collection_name(
                book_name=file_path.name,
                collection_prefix=collection_prefix,
            )
            logger.info(
                "[QDRANT_INGEST] Processing file=%s -> collection=%s",
                file_path.name,
                collection_name,
            )
            chunks = _extract_book_chunks(
                file_path=file_path,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            if not chunks:
                logger.warning("[QDRANT_INGEST] Skipping empty file: %s", file_path)
                continue

            book_title = file_path.stem.replace("_", " ").strip()
            upserted_for_book = 0

            for chunk_batch in _iter_batches(chunks, batch_size=embed_batch_size):
                texts = [row["text"] for row in chunk_batch]
                vectors = _embed_texts(embedding_client, embedding_model, texts)

                if collection_name not in initialized_collections:
                    _ensure_collection(
                        qdrant_client=qdrant_client,
                        collection_name=collection_name,
                        vector_size=len(vectors[0]),
                        recreate=recreate_collections and collection_name not in recreated_collections,
                    )
                    initialized_collections.add(collection_name)
                    if recreate_collections:
                        recreated_collections.add(collection_name)

                paired = list(zip(chunk_batch, vectors))
                for upsert_group in _iter_batches(paired, batch_size=upsert_batch_size):
                    points: list[PointStruct] = []
                    for chunk_row, vector in upsert_group:
                        payload = {
                            "document": chunk_row["text"],
                            "source": file_path.name,
                            "source_path": str(file_path),
                            "book_title": book_title,
                            "topic": collection_name.removeprefix(collection_prefix),
                            "page_number": chunk_row.get("page_number"),
                            "page_chunk_index": chunk_row.get("page_chunk_index"),
                            "chunk_index": chunk_row.get("chunk_index"),
                            "collection": collection_name,
                        }
                        points.append(PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload))

                    qdrant_client.upsert(collection_name=collection_name, points=points, wait=False)
                    upserted_for_book += len(points)

            stats = summary["collection_stats"].setdefault(
                collection_name,
                {"books": 0, "chunks": 0},
            )
            stats["books"] += 1
            stats["chunks"] += upserted_for_book

            summary["books_processed"] += 1
            summary["total_chunks_upserted"] += upserted_for_book
            logger.info(
                "[QDRANT_INGEST] Completed file=%s chunks=%s",
                file_path.name,
                upserted_for_book,
            )

        except Exception as exc:
            summary["books_failed"] += 1
            summary["errors"].append({"file": str(file_path), "error": str(exc)})
            logger.error("[QDRANT_INGEST] Failed for %s: %s", file_path, exc, exc_info=True)

    summary["collections_touched"] = sorted(summary["collection_stats"].keys())
    if summary["books_processed"] == 0:
        summary["status"] = "failed" if summary["errors"] else "skipped"
    return summary


def list_qdrant_collections(collection_prefix: str | None = None) -> dict[str, Any]:
    qdrant_client, qdrant_error = _build_qdrant_client()
    if qdrant_error:
        return {"status": "skipped", "message": qdrant_error, "collections": []}

    try:
        collections = qdrant_client.get_collections().collections
        names = [row.name for row in collections]
        if collection_prefix:
            names = [name for name in names if name.startswith(collection_prefix)]
        return {"status": "success", "collections": sorted(names), "count": len(names)}
    except Exception as exc:
        return {"status": "failed", "message": str(exc), "collections": []}


def search_qdrant_books(
    query: str,
    collection_name: str = "all",
    top_k: int = 5,
    collection_prefix: str = DEFAULT_COLLECTION_PREFIX,
) -> dict[str, Any]:
    """
    Query Qdrant for legal text chunks. If collection_name='all', searches all prefixed collections.
    """
    if not query or not query.strip():
        return {"status": "failed", "message": "query is required", "results": []}

    qdrant_client, qdrant_error = _build_qdrant_client()
    if qdrant_error:
        return {"status": "skipped", "message": qdrant_error, "results": []}

    embedding_client, embedding_model, embed_error = _build_embedding_client()
    if embed_error:
        return {"status": "skipped", "message": embed_error, "results": []}

    try:
        query_vector = _embed_texts(embedding_client, embedding_model, [query])[0]
    except Exception as exc:
        return {"status": "failed", "message": f"Embedding error: {exc}", "results": []}

    requested = (collection_name or "").strip()
    if requested and requested.lower() not in {"*", "all"}:
        if "," in requested:
            target_collections = [name.strip() for name in requested.split(",") if name.strip()]
        else:
            target_collections = [requested]
    else:
        try:
            all_collections = qdrant_client.get_collections().collections
        except Exception as exc:
            return {
                "status": "failed",
                "message": f"Failed to list collections: {exc}",
                "results": [],
            }
        target_collections = [row.name for row in all_collections if row.name.startswith(collection_prefix)]

    if not target_collections:
        return {
            "status": "skipped",
            "message": f"No collections found for prefix '{collection_prefix}'",
            "results": [],
        }

    all_hits: list[dict[str, Any]] = []
    for target_collection in target_collections:
        try:
            points = qdrant_client.query_points(
                collection_name=target_collection,
                query=query_vector,
                limit=max(top_k, 1),
            ).points
        except Exception as exc:
            logger.warning("[QDRANT_SEARCH] collection=%s failed: %s", target_collection, exc)
            continue

        for point in points:
            payload = point.payload or {}
            all_hits.append(
                {
                    "collection": target_collection,
                    "score": float(point.score or 0.0),
                    "document": payload.get("document", ""),
                    "source": payload.get("source", ""),
                    "book_title": payload.get("book_title", ""),
                    "topic": payload.get("topic", ""),
                    "page_number": payload.get("page_number"),
                }
            )

    all_hits.sort(key=lambda row: row.get("score", 0.0), reverse=True)
    trimmed = all_hits[: max(top_k, 1)]
    return {
        "status": "success",
        "searched_collections": target_collections,
        "results": trimmed,
        "count": len(trimmed),
    }
