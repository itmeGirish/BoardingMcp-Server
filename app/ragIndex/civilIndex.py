"""
Build and maintain a civil-law RAG index in Qdrant.

This module ingests all supported files from the Books/books folder and upserts
them into the `civil` collection using the shared Qdrant client and embeddings
model from app.database.vectordatabse.qudrant.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from qdrant_client import models
from qdrant_client.models import PointStruct

try:
    from ..config import logger
    from ..database.vectordatabse.qudrant import qdrant_db
except ImportError:  # pragma: no cover - enables direct script execution
    from app.config import logger
    from app.database.vectordatabse.qudrant import qdrant_db


DEFAULT_COLLECTION_NAME = "civil"
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}
DEFAULT_CHUNK_SIZE = 1400
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_EMBED_BATCH_SIZE = 64
DEFAULT_UPSERT_BATCH_SIZE = 64


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_books_dir(books_dir: str | Path | None = None) -> Path:
    if books_dir:
        return Path(books_dir).resolve()

    root = _project_root()
    candidates = [root / "Books", root / "books"]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return candidates[-1]


def _clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _source_type_for_file(file_name: str) -> str:
    name = file_name.lower()
    if "mulla" in name or "commentary" in name:
        return "commentary"
    if "principles" in name or "manual" in name or "practice" in name:
        return "practice_guide"
    return "bare_act"


def _act_name_for_file(file_name: str, book_title: str, chunk: str = "") -> str:
    # Include some content in classification because some source files are coded names
    # like A1963-36.pdf and do not contain the act title in the file name.
    text = f"{file_name} {book_title} {chunk[:500]}".lower()
    compact = re.sub(r"[^a-z0-9]", "", text)

    if "civil procedure" in text or "cpc" in text or "mulla" in text:
        return "CPC"
    if (
        "limitation act" in text
        or "article 113" in text
        or "a196336" in compact
    ):
        return "Limitation Act"
    if "evidence act" in text or "indian evidence act" in text or "section 65b" in text:
        return "Indian Evidence Act"
    if "court fees" in text or "court fee" in text or "suits valuation" in text or "karnataka court" in text:
        return "Karnataka Court Fees Act"
    if "specific relief" in text:
        return "Specific Relief Act"
    if "transfer of property" in text or "mortgagor" in text or "mortgagee" in text:
        return "Transfer of Property Act"
    if "stamp act" in text or "stamp duty" in text or "karnataka stamp" in text:
        return "Karnataka Stamp Act"
    if "registration act" in text or "registrar" in text and "registration" in text:
        return "Registration Act"
    if "civil rules of practice" in text or "karnataka civil rules" in text:
        return "Karnataka Civil Rules"
    if "contract act" in text or "indian contract act" in text or "a187209" in compact:
        return "Contract Act"
    return "Civil Law"


def _heading_for_chunk(chunk: str) -> Optional[str]:
    first_line = chunk.strip().split("\n", 1)[0].strip()
    if not first_line:
        return None
    if len(first_line) > 160:
        return first_line[:157].strip() + "..."
    return first_line


def _to_int_maybe(value: str) -> Optional[int]:
    if not value:
        return None
    upper = value.upper()
    roman_map = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
        "IX": 9,
        "X": 10,
        "XI": 11,
        "XII": 12,
        "XIII": 13,
        "XIV": 14,
        "XV": 15,
        "XVI": 16,
        "XVII": 17,
        "XVIII": 18,
        "XIX": 19,
        "XX": 20,
    }
    if upper in roman_map:
        return roman_map[upper]
    if value.isdigit():
        return int(value)
    return None


def _extract_section_order_rule(chunk: str) -> tuple[Optional[str], Optional[int], Optional[int]]:
    section = None
    order = None
    rule = None

    section_match = re.search(r"\bSECTION\s+(\d+[A-Za-z]?)\b", chunk, flags=re.IGNORECASE)
    if section_match:
        section = section_match.group(1).upper()

    order_rule_match = re.search(
        r"\bORDER\s+([IVXLCM]+|\d+)\s+RULE\s+(\d+)\b",
        chunk,
        flags=re.IGNORECASE,
    )
    if order_rule_match:
        order = _to_int_maybe(order_rule_match.group(1))
        rule = int(order_rule_match.group(2))
    else:
        order_match = re.search(r"\bORDER\s+([IVXLCM]+|\d+)\b", chunk, flags=re.IGNORECASE)
        rule_match = re.search(r"\bRULE\s+(\d+)\b", chunk, flags=re.IGNORECASE)
        if order_match:
            order = _to_int_maybe(order_match.group(1))
        if rule_match:
            rule = int(rule_match.group(1))

    return section, order, rule


def _topic_tags_for_chunk(chunk: str) -> list[str]:
    text = chunk.lower()
    keyword_map = {
        "pleading": "pleadings",
        "plaint": "plaint",
        "jurisdiction": "jurisdiction",
        "cause of action": "cause_of_action",
        "limitation": "limitation",
        "injunction": "injunction",
        "decree": "decree",
        "appeal": "appeal",
        "execution": "execution",
        "evidence": "evidence",
    }
    tags = [tag for key, tag in keyword_map.items() if key in text]
    return sorted(set(tags))


def _doc_type_tags_for_chunk(chunk: str) -> list[str]:
    text = chunk.lower()
    tags: list[str] = []
    if "money recovery" in text:
        tags.append("money_recovery_plaint")
    if "injunction plaint" in text or "suit for injunction" in text:
        tags.append("injunction_plaint")
    return sorted(set(tags))


def _make_anchor(
    act_name: str,
    source_path: str,
    page_number: Optional[int],
    chunk_index: int,
    section: Optional[str],
    order: Optional[int],
    rule: Optional[int],
) -> str:
    if order is not None and rule is not None:
        return f"{act_name}:Order{order}Rule{rule}"
    if section:
        return f"{act_name}:Section{section}"
    if page_number is not None:
        return f"{act_name}:{source_path}:P{page_number}:C{chunk_index}"
    return f"{act_name}:{source_path}:C{chunk_index}"


def _make_payload(
    *,
    chunk_id: str,
    chunk: str,
    file_name: str,
    source_path: str,
    book_title: str,
    file_size_bytes: int,
    indexed_at_utc: str,
    collection_name: str,
    page_number: Optional[int],
    page_chunk_index: int,
    chunk_index: int,
) -> dict[str, Any]:
    source_type = _source_type_for_file(file_name)
    act_name = _act_name_for_file(file_name, book_title, chunk)
    heading = _heading_for_chunk(chunk)
    section, order, rule = _extract_section_order_rule(chunk)
    anchor = _make_anchor(
        act_name=act_name,
        source_path=source_path,
        page_number=page_number,
        chunk_index=chunk_index,
        section=section,
        order=order,
        rule=rule,
    )
    topic_tags = _topic_tags_for_chunk(chunk)
    doc_type_tags = _doc_type_tags_for_chunk(chunk)

    payload = {
        # Example.py reference schema
        "source_type": source_type,
        "book": book_title,
        "act_name": act_name,
        "anchor": anchor,
        "heading": heading,
        "section": section,
        "order": order,
        "rule": rule,
        "topic_tags": topic_tags,
        "doc_type_tags": doc_type_tags,
        "page_start": page_number,
        "page_end": page_number,
        "lang": "en",
        # Existing schema compatibility
        "chunk_id": chunk_id,
        "document": chunk,
        "text": chunk,
        "source": file_name,
        "source_path": source_path,
        "book_title": book_title,
        "page_number": page_number,
        "page_chunk_index": page_chunk_index,
        "chunk_index": chunk_index,
        "collection": collection_name,
        "file_size_bytes": file_size_bytes,
        "indexed_at_utc": indexed_at_utc,
    }
    return {k: v for k, v in payload.items() if v is not None}


def _validate_payload(payload: dict[str, Any]) -> None:
    required = ("source_type", "book", "act_name", "anchor", "document", "chunk_id")
    for field in required:
        if field not in payload or payload[field] in ("", None):
            raise ValueError(f"Payload missing required field: {field}")


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if not text:
        return []

    if chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE
    if chunk_overlap < 0:
        chunk_overlap = 0
    if chunk_overlap >= chunk_size:
        chunk_overlap = max(0, chunk_size // 5)

    chunks: list[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            split = text.rfind(" ", start + int(chunk_size * 0.6), end)
            if split > start:
                end = split

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= n:
            break
        start = max(0, end - chunk_overlap)

    return chunks


def _iter_batches(items: list[Any], batch_size: int) -> Iterable[list[Any]]:
    size = max(1, int(batch_size))
    for index in range(0, len(items), size):
        yield items[index:index + size]


def _safe_relative_path(file_path: Path, base: Path) -> str:
    try:
        return file_path.resolve().relative_to(base.resolve()).as_posix()
    except Exception:
        return file_path.as_posix()


def _chunk_point_id(source_path: str, page_number: int | None, chunk_index: int, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
    raw = f"{source_path}|{page_number}|{chunk_index}|{digest}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, raw))


def _extract_pdf_payloads(
    file_path: Path,
    project_root: Path,
    chunk_size: int,
    chunk_overlap: int,
    collection_name: str,
    indexed_at_utc: str,
) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency expected
        raise RuntimeError("pypdf is required to index PDF books.") from exc

    reader = PdfReader(str(file_path))
    payloads: list[dict[str, Any]] = []
    source_path = _safe_relative_path(file_path, project_root)
    book_title = file_path.stem.replace("_", " ").strip()
    file_size_bytes = file_path.stat().st_size
    global_chunk_index = 0

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = _clean_text(page.extract_text() or "")
        if not page_text:
            continue

        page_chunks = _chunk_text(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for page_chunk_index, chunk in enumerate(page_chunks):
            point_id = _chunk_point_id(source_path, page_number, global_chunk_index, chunk)
            payload = _make_payload(
                chunk_id=point_id,
                chunk=chunk,
                file_name=file_path.name,
                source_path=source_path,
                book_title=book_title,
                file_size_bytes=file_size_bytes,
                indexed_at_utc=indexed_at_utc,
                collection_name=collection_name,
                page_number=page_number,
                page_chunk_index=page_chunk_index,
                chunk_index=global_chunk_index,
            )
            _validate_payload(payload)
            payloads.append(payload)
            global_chunk_index += 1

    return payloads


def _extract_text_payloads(
    file_path: Path,
    project_root: Path,
    chunk_size: int,
    chunk_overlap: int,
    collection_name: str,
    indexed_at_utc: str,
) -> list[dict[str, Any]]:
    source_text = file_path.read_text(encoding="utf-8", errors="ignore")
    source_text = _clean_text(source_text)
    chunks = _chunk_text(source_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    source_path = _safe_relative_path(file_path, project_root)
    book_title = file_path.stem.replace("_", " ").strip()
    file_size_bytes = file_path.stat().st_size
    payloads: list[dict[str, Any]] = []

    for chunk_index, chunk in enumerate(chunks):
        point_id = _chunk_point_id(source_path, None, chunk_index, chunk)
        payload = _make_payload(
            chunk_id=point_id,
            chunk=chunk,
            file_name=file_path.name,
            source_path=source_path,
            book_title=book_title,
            file_size_bytes=file_size_bytes,
            indexed_at_utc=indexed_at_utc,
            collection_name=collection_name,
            page_number=None,
            page_chunk_index=chunk_index,
            chunk_index=chunk_index,
        )
        _validate_payload(payload)
        payloads.append(payload)

    return payloads


def _extract_payloads_for_file(
    file_path: Path,
    project_root: Path,
    chunk_size: int,
    chunk_overlap: int,
    collection_name: str,
    indexed_at_utc: str,
) -> list[dict[str, Any]]:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_payloads(
            file_path=file_path,
            project_root=project_root,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            collection_name=collection_name,
            indexed_at_utc=indexed_at_utc,
        )
    return _extract_text_payloads(
        file_path=file_path,
        project_root=project_root,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        collection_name=collection_name,
        indexed_at_utc=indexed_at_utc,
    )


def _extract_existing_vector_size(collection_info: Any) -> int | None:
    config = getattr(collection_info, "config", None)
    params = getattr(config, "params", None)
    vectors = getattr(params, "vectors", None)
    if vectors is None:
        return None

    if isinstance(vectors, dict):
        first = next(iter(vectors.values()), None)
        size = getattr(first, "size", None) if first is not None else None
        return int(size) if size else None

    size = getattr(vectors, "size", None)
    return int(size) if size else None


def _ensure_collection(
    collection_name: str,
    embedding_size: int,
    recreate_on_mismatch: bool,
) -> str:
    client = qdrant_db.client

    exists = False
    if hasattr(client, "collection_exists"):
        exists = bool(client.collection_exists(collection_name=collection_name))
    else:
        try:
            client.get_collection(collection_name=collection_name)
            exists = True
        except Exception as exc:
            msg = str(exc).lower()
            if "not found" in msg or "404" in msg:
                exists = False
            else:
                raise

    state = "existing"
    if not exists:
        qdrant_db.create_collection(collection_name=collection_name, embedding_size=embedding_size)
        state = "created"
    else:
        info = client.get_collection(collection_name=collection_name)
        existing_size = _extract_existing_vector_size(info)
        if existing_size and existing_size != embedding_size:
            if not recreate_on_mismatch:
                raise ValueError(
                    f"Collection '{collection_name}' has vector size {existing_size}, "
                    f"but embeddings are size {embedding_size}. "
                    "Set recreate_on_mismatch=True to rebuild."
                )
            logger.warning(
                "Recreating collection '%s' due to vector size mismatch (%s != %s).",
                collection_name,
                existing_size,
                embedding_size,
            )
            qdrant_db.delete_collection(collection_name=collection_name)
            qdrant_db.create_collection(collection_name=collection_name, embedding_size=embedding_size)
            state = "recreated"

    keyword_fields = [
        "source_type",
        "book",
        "act_name",
        "anchor",
        "section",
        "source",
        "book_title",
        "source_path",
        "lang",
    ]
    integer_fields = [
        "order",
        "rule",
        "page_start",
        "page_end",
        "page_number",
    ]

    for field_name in keyword_fields:
        qdrant_db.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
    for field_name in integer_fields:
        qdrant_db.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=models.PayloadSchemaType.INTEGER,
        )
    return state


def _upsert_points_with_retry(
    collection_name: str,
    points: list[PointStruct],
    max_retries: int = 5,
) -> int:
    attempts = 0
    while True:
        try:
            qdrant_db.client.upsert(
                collection_name=collection_name,
                points=points,
                wait=False,
            )
            return len(points)
        except Exception as exc:
            attempts += 1
            if len(points) > 1 and attempts == 1:
                # If a larger batch fails, split once and retry in smaller chunks.
                midpoint = len(points) // 2
                left = points[:midpoint]
                right = points[midpoint:]
                written = 0
                if left:
                    written += _upsert_points_with_retry(collection_name, left, max_retries=max_retries)
                if right:
                    written += _upsert_points_with_retry(collection_name, right, max_retries=max_retries)
                return written
            if attempts > max_retries:
                raise
            delay = min(2 ** attempts, 8)
            logger.warning(
                "Upsert retry %s/%s for '%s' (%s points): %s",
                attempts,
                max_retries,
                collection_name,
                len(points),
                exc,
            )
            time.sleep(delay)


def build_civil_index(
    books_dir: str | Path | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    recreate_on_mismatch: bool = False,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    embed_batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
    upsert_batch_size: int = DEFAULT_UPSERT_BATCH_SIZE,
) -> dict[str, Any]:
    """
    Build/update the civil RAG index from all files in Books/books.

    Returns a summary dict with counts, errors, and final collection status.
    """
    project_root = _project_root()
    books_path = _resolve_books_dir(books_dir)

    summary: dict[str, Any] = {
        "status": "success",
        "collection_name": collection_name,
        "books_dir": str(books_path),
        "books_discovered": 0,
        "books_processed": 0,
        "books_failed": 0,
        "books_skipped_empty": 0,
        "chunks_discovered": 0,
        "chunks_upserted": 0,
        "collection_state": "unknown",
        "final_point_count": None,
        "errors": [],
    }

    if not books_path.exists() or not books_path.is_dir():
        summary["status"] = "failed"
        summary["errors"].append(f"Books directory not found: {books_path}")
        return summary

    book_files = sorted(
        path for path in books_path.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    summary["books_discovered"] = len(book_files)

    if not book_files:
        summary["status"] = "skipped"
        summary["errors"].append(f"No supported files found under: {books_path}")
        return summary

    try:
        qdrant_db.client.get_collections()
    except Exception as exc:
        summary["status"] = "failed"
        summary["errors"].append(f"Qdrant connectivity check failed: {exc}")
        logger.exception("Qdrant connectivity check failed before indexing.")
        return summary

    indexed_at_utc = datetime.now(timezone.utc).isoformat()
    collection_ready = False

    for file_path in book_files:
        try:
            payloads = _extract_payloads_for_file(
                file_path=file_path,
                project_root=project_root,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                collection_name=collection_name,
                indexed_at_utc=indexed_at_utc,
            )
        except Exception as exc:
            summary["books_failed"] += 1
            summary["errors"].append(f"Extraction failed for {file_path.name}: {exc}")
            logger.exception("Failed extracting chunks from %s", file_path)
            continue

        if not payloads:
            summary["books_skipped_empty"] += 1
            logger.warning("Skipping empty/unsupported content file: %s", file_path.name)
            continue

        summary["chunks_discovered"] += len(payloads)
        file_upserted = 0

        try:
            for payload_batch in _iter_batches(payloads, batch_size=embed_batch_size):
                documents = [item["document"] for item in payload_batch]
                embeddings = qdrant_db.get_embeddings_batch(documents)

                if len(embeddings) != len(payload_batch):
                    raise ValueError(
                        f"Embedding count mismatch for {file_path.name}: "
                        f"{len(embeddings)} != {len(payload_batch)}"
                    )

                if not collection_ready:
                    summary["collection_state"] = _ensure_collection(
                        collection_name=collection_name,
                        embedding_size=len(embeddings[0]),
                        recreate_on_mismatch=recreate_on_mismatch,
                    )
                    collection_ready = True

                paired = list(zip(payload_batch, embeddings))
                for pair_batch in _iter_batches(paired, batch_size=upsert_batch_size):
                    points = [
                        PointStruct(
                            id=payload["chunk_id"],
                            vector=vector,
                            payload=payload,
                        )
                        for payload, vector in pair_batch
                    ]
                    written = _upsert_points_with_retry(
                        collection_name=collection_name,
                        points=points,
                    )
                    file_upserted += written

            summary["books_processed"] += 1
            summary["chunks_upserted"] += file_upserted
            logger.info(
                "Indexed %s chunks from %s into '%s'.",
                file_upserted,
                file_path.name,
                collection_name,
            )

        except Exception as exc:
            summary["books_failed"] += 1
            summary["errors"].append(f"Upsert failed for {file_path.name}: {exc}")
            logger.exception("Failed indexing file %s", file_path.name)

    if summary["books_processed"] == 0:
        summary["status"] = "failed" if summary["errors"] else "skipped"

    try:
        count_result = qdrant_db.client.count(
            collection_name=collection_name,
            exact=True,
        )
        summary["final_point_count"] = int(getattr(count_result, "count", 0))
    except Exception as exc:
        summary["errors"].append(f"Could not fetch final point count: {exc}")

    return summary


def main() -> None:
    result = build_civil_index()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
