"""File parsing utilities for extracting contacts from Excel and CSV files."""
import csv
import os
from typing import Optional
from app.config import logger


# Common column name patterns for auto-detection
PHONE_PATTERNS = {"phone", "mobile", "number", "contact", "whatsapp", "cell", "telephone", "tel"}
NAME_PATTERNS = {"name", "full_name", "fullname", "contact_name", "first_name", "firstname"}
EMAIL_PATTERNS = {"email", "e-mail", "mail", "email_address"}


def _find_column(headers: list, patterns: set, explicit: str = None) -> Optional[str]:
    """Find matching column header from patterns or explicit name."""
    if explicit:
        for h in headers:
            if h.strip().lower() == explicit.strip().lower():
                return h
    for h in headers:
        if h.strip().lower() in patterns:
            return h
    return None


def parse_excel(
    file_path: str,
    phone_column: str = None,
    name_column: str = None,
) -> list:
    """
    Parse contacts from an Excel (.xlsx) file.

    Auto-detects phone/name columns by header name if not specified.

    Args:
        file_path: Path to the Excel file
        phone_column: Explicit phone column name (auto-detected if None)
        name_column: Explicit name column name (auto-detected if None)

    Returns:
        list[dict]: List of contact dicts with keys:
            phone, name, email, source_row, custom_fields
    """
    import openpyxl

    logger.info(f"Parsing Excel file: {file_path}")

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        return []

    headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(rows[0])]

    phone_col = _find_column(headers, PHONE_PATTERNS, phone_column)
    name_col = _find_column(headers, NAME_PATTERNS, name_column)
    email_col = _find_column(headers, EMAIL_PATTERNS)

    if not phone_col:
        raise ValueError(
            f"Could not detect phone column. Headers found: {headers}. "
            f"Please specify phone_column parameter."
        )

    contacts = []
    for row_idx, row in enumerate(rows[1:], start=2):
        row_dict = dict(zip(headers, row))

        phone_val = row_dict.get(phone_col)
        if not phone_val:
            continue

        # Build custom fields (everything except phone/name/email)
        skip_cols = {phone_col, name_col, email_col} - {None}
        custom_fields = {
            k: str(v) for k, v in row_dict.items()
            if k not in skip_cols and v is not None
        }

        contacts.append({
            "phone": str(phone_val).strip(),
            "name": str(row_dict.get(name_col, "")).strip() if name_col and row_dict.get(name_col) else None,
            "email": str(row_dict.get(email_col, "")).strip() if email_col and row_dict.get(email_col) else None,
            "source_row": row_idx,
            "custom_fields": custom_fields if custom_fields else {},
        })

    logger.info(f"Parsed {len(contacts)} contacts from Excel file")
    return contacts


def parse_csv(
    file_path: str,
    phone_column: str = None,
    name_column: str = None,
) -> list:
    """
    Parse contacts from a CSV file with auto-delimiter detection.

    Handles encoding issues (utf-8 with latin-1 fallback).

    Args:
        file_path: Path to the CSV file
        phone_column: Explicit phone column name (auto-detected if None)
        name_column: Explicit name column name (auto-detected if None)

    Returns:
        list[dict]: List of contact dicts with keys:
            phone, name, email, source_row, custom_fields
    """
    import pandas as pd

    logger.info(f"Parsing CSV file: {file_path}")

    # Try utf-8 first, fall back to latin-1
    for encoding in ("utf-8", "latin-1"):
        try:
            # Detect delimiter
            with open(file_path, "r", encoding=encoding) as f:
                sample = f.read(8192)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                sep = dialect.delimiter
            except csv.Error:
                sep = ","

            df = pd.read_csv(file_path, sep=sep, encoding=encoding, dtype=str)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Could not read CSV file with supported encodings: {file_path}")

    df.columns = [str(c).strip() for c in df.columns]
    headers = list(df.columns)

    phone_col = _find_column(headers, PHONE_PATTERNS, phone_column)
    name_col = _find_column(headers, NAME_PATTERNS, name_column)
    email_col = _find_column(headers, EMAIL_PATTERNS)

    if not phone_col:
        raise ValueError(
            f"Could not detect phone column. Headers found: {headers}. "
            f"Please specify phone_column parameter."
        )

    contacts = []
    skip_cols = {phone_col, name_col, email_col} - {None}

    for row_idx, row in df.iterrows():
        phone_val = row.get(phone_col)
        if pd.isna(phone_val) or not str(phone_val).strip():
            continue

        custom_fields = {
            k: str(v) for k, v in row.items()
            if k not in skip_cols and not pd.isna(v)
        }

        name_val = row.get(name_col) if name_col else None
        email_val = row.get(email_col) if email_col else None

        contacts.append({
            "phone": str(phone_val).strip(),
            "name": str(name_val).strip() if name_val and not pd.isna(name_val) else None,
            "email": str(email_val).strip() if email_val and not pd.isna(email_val) else None,
            "source_row": row_idx + 2,  # +2 for 1-based + header row
            "custom_fields": custom_fields if custom_fields else {},
        })

    logger.info(f"Parsed {len(contacts)} contacts from CSV file")
    return contacts


def parse_file(file_path: str, **kwargs) -> list:
    """
    Auto-detect file format and parse contacts.

    Supported formats: .xlsx, .xls, .csv

    Args:
        file_path: Path to the file
        **kwargs: Passed to the appropriate parser (phone_column, name_column)

    Returns:
        list[dict]: List of contact dicts

    Raises:
        ValueError: If file format is not supported
        FileNotFoundError: If file does not exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".xlsx", ".xls"):
        return parse_excel(file_path, **kwargs)
    elif ext == ".csv":
        return parse_csv(file_path, **kwargs)
    else:
        raise ValueError(
            f"Unsupported file format: '{ext}'. "
            f"Supported formats: .xlsx, .xls, .csv"
        )
