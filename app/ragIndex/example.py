"""
QDRANT INGESTION (PUSHING DATA) — Civil Drafting RAG
====================================================
- Push chunks into Qdrant with strong metadata (act/section/order/rule/anchor/tags)
- Works for: bare acts, commentary (Mulla), general principles, contract act
- Uses a pluggable embedder (you can connect Kimi/OpenAI/local later)

Install:
  pip install qdrant-client pydantic

Run:
  python ingest_qdrant.py
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.models import PointStruct


# -----------------------------
# 1) Embedder (plug your model)
# -----------------------------

@dataclass
class Embedder:
    """
    Replace embed_texts() with your real embeddings call.
    - For production: use one embedding model consistently across all collections.
    - dim must match the vectors you store in Qdrant collection.
    """
    dim: int = 768

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        # ⚠️ Placeholder: deterministic fake vectors (DO NOT use in production)
        # Replace with real embedding vectors.
        vectors: List[List[float]] = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            # build dim floats from hash bytes (repeat)
            vals = []
            i = 0
            while len(vals) < self.dim:
                b = h[i % len(h)]
                vals.append((b / 255.0) * 2.0 - 1.0)  # [-1, 1]
                i += 1
            vectors.append(vals)
        return vectors


# -----------------------------
# 2) Chunk schema
# -----------------------------

def stable_id(*parts: str) -> str:
    """Stable UUID from content+metadata so re-ingest upserts consistently."""
    raw = "||".join(parts).encode("utf-8")
    return str(uuid.UUID(hashlib.md5(raw).hexdigest()))  # noqa: S324 (ok for stable IDs)


def make_payload(
    *,
    source_type: str,  # bare_act | commentary | principles
    book: str,
    act_name: str,
    anchor: Optional[str],
    heading: Optional[str] = None,
    section: Optional[str] = None,
    order: Optional[int] = None,
    rule: Optional[int] = None,
    topic_tags: Optional[List[str]] = None,
    doc_type_tags: Optional[List[str]] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    lang: str = "en",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "source_type": source_type,
        "book": book,
        "act_name": act_name,
        "anchor": anchor,
        "heading": heading,
        "section": section,
        "order": order,
        "rule": rule,
        "topic_tags": topic_tags or [],
        "doc_type_tags": doc_type_tags or [],
        "page_start": page_start,
        "page_end": page_end,
        "lang": lang,
    }
    if extra:
        payload.update(extra)
    # Remove None keys for cleaner payloads
    return {k: v for k, v in payload.items() if v is not None}


# -----------------------------
# 3) Qdrant helpers
# -----------------------------

def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    dim: int,
    distance: rest.Distance = rest.Distance.COSINE,
) -> None:
    exists = client.collection_exists(collection_name)
    if exists:
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=rest.VectorParams(size=dim, distance=distance),
        hnsw_config=rest.HnswConfigDiff(m=16, ef_construct=128),
        optimizers_config=rest.OptimizersConfigDiff(default_segment_number=2),
    )


def upsert_points_batched(
    client: QdrantClient,
    collection_name: str,
    points: List[PointStruct],
    batch_size: int = 64,
) -> None:
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)


# -----------------------------
# 4) Ingestion API
# -----------------------------

def ingest_chunks(
    client: QdrantClient,
    embedder: Embedder,
    *,
    collection_name: str,
    chunks: List[Dict[str, Any]],
    text_key: str = "text",
    batch_size: int = 32,
) -> None:
    """
    chunks: list of dicts. Each dict must include:
      - text: str
      - payload fields (we'll store as payload)
      - optional id (else generated stable id)
    """
    ensure_collection(client, collection_name, dim=embedder.dim)

    texts: List[str] = []
    payloads: List[Dict[str, Any]] = []
    ids: List[str] = []

    for c in chunks:
        text = c[text_key].strip()
        payload = c["payload"]
        chunk_id = c.get("id")

        # create stable id if missing
        if not chunk_id:
            chunk_id = stable_id(
                collection_name,
                payload.get("book", ""),
                payload.get("act_name", ""),
                payload.get("anchor", "") or "",
                payload.get("section", "") or "",
                str(payload.get("order", "")),
                str(payload.get("rule", "")),
                text[:200],
            )

        texts.append(text)
        payloads.append(payload)
        ids.append(chunk_id)

    vectors = embedder.embed_texts(texts)

    points: List[PointStruct] = []
    for pid, vec, text, payload in zip(ids, vectors, texts, payloads):
        payload2 = dict(payload)
        payload2["text"] = text  # store raw text in payload for easy debugging
        points.append(PointStruct(id=pid, vector=vec, payload=payload2))

    upsert_points_batched(client, collection_name, points, batch_size=batch_size)


# -----------------------------
# 5) Example: prepare chunks
# -----------------------------

def example_bare_act_chunks() -> List[Dict[str, Any]]:
    """
    Example chunking style for Bare Acts:
    One chunk per Section or Order/Rule.
    Replace 'text' with actual extracted section text.
    """
    return [
        {
            "payload": make_payload(
                source_type="bare_act",
                book="IndiaCode Bare Act",
                act_name="CPC",
                anchor="CPC:Order7Rule1",
                heading="Particulars to be contained in plaint",
                order=7,
                rule=1,
                topic_tags=["pleadings", "plaint"],
                doc_type_tags=["money_recovery_plaint", "injunction_plaint"],
            ),
            "text": "ORDER VII RULE 1 — Particulars to be contained in plaint: ... (paste exact text here)",
        },
        {
            "payload": make_payload(
                source_type="bare_act",
                book="IndiaCode Bare Act",
                act_name="Limitation Act",
                anchor="Limitation:Article113",
                heading="Article 113 — Any suit for which no period of limitation is provided elsewhere...",
                topic_tags=["limitation"],
                doc_type_tags=["money_recovery_plaint"],
            ),
            "text": "ARTICLE 113 — Description of suit: ... Period: ... Time from which period begins to run: ...",
        },
    ]


def example_commentary_chunks() -> List[Dict[str, Any]]:
    """
    Example chunking for commentary:
    350-900 tokens; must map to anchors.
    """
    return [
        {
            "payload": make_payload(
                source_type="commentary",
                book="Mulla CPC",
                act_name="CPC",
                anchor="CPC:Order7Rule1",
                heading="Order VII Rule 1 — Commentary",
                page_start=156,
                page_end=157,
                topic_tags=["pleadings", "jurisdiction", "cause_of_action"],
                doc_type_tags=["money_recovery_plaint"],
                extra={"citation": "Mulla CPC, O7 R1 (pp.156-157)"},
            ),
            "text": "Commentary: A plaint must contain ... jurisdiction facts ... cause of action ... valuation ... reliefs ...",
        }
    ]


# -----------------------------
# 6) Main
# -----------------------------

def main():
    # Change to your Qdrant endpoint
    client = QdrantClient(url="http://localhost:6333", timeout=60)

    embedder = Embedder(dim=768)  # MUST match your real embedding dim

    # Collections (recommended split)
    col_bare = "bare_acts_civil_chunks"
    col_cpc = "commentary_cpc_mulla_chunks"

    # Prepare chunks
    bare_chunks = example_bare_act_chunks()
    cpc_chunks = example_commentary_chunks()

    # Ingest
    ingest_chunks(client, embedder, collection_name=col_bare, chunks=bare_chunks, batch_size=32)
    ingest_chunks(client, embedder, collection_name=col_cpc, chunks=cpc_chunks, batch_size=32)

    print("✅ Ingestion complete.")
    print(f"- {col_bare}: {client.count(col_bare, exact=True).count} points")
    print(f"- {col_cpc}: {client.count(col_cpc, exact=True).count} points")


if __name__ == "__main__":
    main()