"""
Seed verified citations into drafting.verified_citations.

Supports input formats:
- CSV
- JSON array
- JSONL

Usage:
  python scripts/seed_verified_citations.py --input data/citations.csv
  python scripts/seed_verified_citations.py --input data/citations.jsonl --dry-run
  python scripts/seed_verified_citations.py --input data/citations.json --unverified

Expected fields (minimum):
- citation_text
- case_name

Optional fields:
- year
- court
- holding
- source_db
- source_url
- verified (true/false)

The script computes citation_hash from normalized citation_text
and performs upsert-like behavior:
- insert when hash does not exist
- update missing/empty fields when hash exists
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from sqlmodel import select

from app.database.postgresql.models.drafting import VerifiedCitation
from app.database.postgresql.postgresql_connection import get_session


REQUIRED_FIELDS = {"citation_text", "case_name"}
FIELD_ALIASES = {
    "citation": "citation_text",
    "citationtext": "citation_text",
    "case": "case_name",
    "casename": "case_name",
    "source": "source_db",
    "url": "source_url",
}


@dataclass
class Counters:
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


def normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_")


def normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    norm: dict[str, Any] = {}
    for k, v in raw.items():
        nk = normalize_key(str(k))
        nk = FIELD_ALIASES.get(nk, nk)
        norm[nk] = v
    return norm


def normalize_citation_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def compute_citation_hash(citation_text: str) -> str:
    norm = normalize_citation_text(citation_text).lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def parse_bool(v: Any, default: bool = True) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "y"}:
        return True
    if s in {"0", "false", "no", "n"}:
        return False
    return default


def parse_year(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        y = int(str(v).strip())
        if 1000 <= y <= 2999:
            return y
    except Exception:
        pass
    return None


def load_csv(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def load_json(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                yield row
    elif isinstance(data, dict):
        # Allow {"items":[...]} or single object.
        items = data.get("items")
        if isinstance(items, list):
            for row in items:
                if isinstance(row, dict):
                    yield row
        else:
            yield data


def load_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    yield obj
            except json.JSONDecodeError:
                continue


def load_rows(path: Path) -> Iterable[dict[str, Any]]:
    ext = path.suffix.lower()
    if ext == ".csv":
        return load_csv(path)
    if ext == ".json":
        return load_json(path)
    if ext == ".jsonl":
        return load_jsonl(path)
    raise ValueError(f"Unsupported input format: {ext}. Use .csv, .json, or .jsonl")


def build_record(row: dict[str, Any], default_verified: bool) -> dict[str, Any] | None:
    row = normalize_row(row)
    for req in REQUIRED_FIELDS:
        if not str(row.get(req, "")).strip():
            return None

    citation_text = normalize_citation_text(str(row["citation_text"]))
    case_name = str(row["case_name"]).strip()
    if not citation_text or not case_name:
        return None

    return {
        "citation_text": citation_text,
        "case_name": case_name,
        "year": parse_year(row.get("year")),
        "court": (str(row.get("court", "")).strip() or None),
        "holding": (str(row.get("holding", "")).strip() or None),
        "source_db": (str(row.get("source_db", "")).strip() or None),
        "source_url": (str(row.get("source_url", "")).strip() or None),
        "verified": parse_bool(row.get("verified"), default_verified),
        "citation_hash": compute_citation_hash(citation_text),
    }


def upsert_rows(path: Path, dry_run: bool, default_verified: bool) -> Counters:
    counters = Counters()
    rows = load_rows(path)

    with get_session() as session:
        for raw in rows:
            counters.total_rows += 1
            rec = build_record(raw, default_verified)
            if rec is None:
                counters.invalid_rows += 1
                continue
            counters.valid_rows += 1

            stmt = select(VerifiedCitation).where(
                VerifiedCitation.citation_hash == rec["citation_hash"]
            )
            existing = session.exec(stmt).first()

            if existing is None:
                counters.inserted += 1
                if dry_run:
                    continue
                obj = VerifiedCitation(
                    id=str(uuid.uuid4()),
                    citation_text=rec["citation_text"],
                    case_name=rec["case_name"],
                    year=rec["year"],
                    court=rec["court"],
                    holding=rec["holding"],
                    citation_hash=rec["citation_hash"],
                    source_db=rec["source_db"],
                    source_url=rec["source_url"],
                    verified_at=datetime.now() if rec["verified"] else None,
                )
                session.add(obj)
                continue

            changed = False
            # Update only missing/empty fields, keep existing curated data.
            for field in ("case_name", "year", "court", "holding", "source_db", "source_url"):
                new_val = rec.get(field)
                old_val = getattr(existing, field)
                if (old_val is None or str(old_val).strip() == "") and new_val not in (None, ""):
                    setattr(existing, field, new_val)
                    changed = True

            if existing.verified_at is None and rec["verified"]:
                existing.verified_at = datetime.now()
                changed = True

            if changed:
                counters.updated += 1
            else:
                counters.skipped += 1

        if not dry_run:
            session.commit()

    return counters


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed verified citations")
    parser.add_argument("--input", required=True, help="Path to CSV/JSON/JSONL file")
    parser.add_argument("--dry-run", action="store_true", help="Validate and count only; no DB writes")
    parser.add_argument(
        "--unverified",
        action="store_true",
        help="Default all rows to unverified unless row has verified=true",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    counters = upsert_rows(
        path=input_path,
        dry_run=args.dry_run,
        default_verified=not args.unverified,
    )

    print("Seeding summary")
    print(f"  input_file   : {input_path}")
    print(f"  dry_run      : {args.dry_run}")
    print(f"  total_rows   : {counters.total_rows}")
    print(f"  valid_rows   : {counters.valid_rows}")
    print(f"  invalid_rows : {counters.invalid_rows}")
    print(f"  inserted     : {counters.inserted}")
    print(f"  updated      : {counters.updated}")
    print(f"  skipped      : {counters.skipped}")


if __name__ == "__main__":
    main()

