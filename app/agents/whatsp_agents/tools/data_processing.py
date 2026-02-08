"""
Backend tools for Data Processing Agent.

Handles beginner verification, file parsing, phone validation,
deduplication, quality scoring, and contact storage.

Uses ThreadPoolExecutor to run DB/MCP calls in separate threads
(same pattern as onboarding and supervisor broadcasting agents).
"""

import asyncio
import json
import concurrent.futures
import nest_asyncio
from langchain.tools import tool

from ....config import logger

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Thread pool for running operations in separate threads
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)


# ============================================
# DIRECT API MCP HELPER
# ============================================

def _call_direct_api_mcp(tool_name: str, params: dict) -> dict:
    """Call a Direct API MCP tool (port 9002) synchronously."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.utils.whsp_onboarding_agent import parse_mcp_result_with_debug as parse_mcp_result

    async def _call():
        client = MultiServerMCPClient({
            "DirectApiMCP": {
                "url": "http://127.0.0.1:9002/mcp",
                "transport": "streamable-http"
            }
        })
        async with client.session("DirectApiMCP") as session:
            mcp_tools_list = await load_mcp_tools(session)
            mcp_tools = {t.name: t for t in mcp_tools_list}
            if tool_name not in mcp_tools:
                return {"status": "failed", "error": f"MCP tool '{tool_name}' not found"}
            result = await mcp_tools[tool_name].ainvoke(params)
            return parse_mcp_result(result)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_call())
    finally:
        loop.close()


# ============================================
# TOOL 1: CHECK BEGINNER STATUS
# ============================================

def _run_check_beginner_sync(user_id: str, project_id: str):
    """Check first_broadcasting flag and FB verification."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.memory_repo import MemoryRepository

    with get_session() as session:
        memory_repo = MemoryRepository(session=session)
        is_first = memory_repo.is_first_broadcasting(
            user_id=user_id,
            project_id=project_id
        )

    return {
        "status": "success",
        "is_beginner": is_first,
        "message": (
            "First-time broadcaster. Facebook Business verification required."
            if is_first else
            "Returning broadcaster. Ready to process contact data."
        )
    }


@tool
def check_beginner_status(user_id: str, project_id: str) -> str:
    """
    Check if the user is a first-time broadcaster.

    Reads the first_broadcasting flag from TempMemory.
    If True, the user needs FB verification before processing contacts.
    If False, the user can proceed directly with contact upload.

    Args:
        user_id: User's unique identifier
        project_id: Project ID

    Returns:
        JSON string with is_beginner flag and status message
    """
    logger.info("[DATA_PROCESSING] check_beginner_status for user: %s", user_id)
    try:
        future = _executor.submit(_run_check_beginner_sync, user_id, project_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DATA_PROCESSING] check_beginner_status error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 2: VERIFY FACEBOOK BUSINESS
# ============================================

def _run_verify_fb_sync(user_id: str, project_id: str):
    """Check FB verification via MCP and flip flag if verified."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.memory_repo import MemoryRepository

    # Call MCP to check FB verification status
    result = _call_direct_api_mcp("fb_verification_status", {"user_id": user_id})

    is_verified = False
    if isinstance(result, dict):
        data = result.get("data", result)
        if isinstance(data, dict):
            is_verified = data.get("verified", False) or data.get("is_verified", False)
        if result.get("status") == "success":
            is_verified = True

    if is_verified:
        # Flip first_broadcasting to False
        with get_session() as session:
            memory_repo = MemoryRepository(session=session)
            memory_repo.mark_not_first_broadcasting(user_id=user_id, project_id=project_id)

        return {
            "status": "success",
            "verified": True,
            "message": "Facebook Business verification confirmed. You can now upload contacts for broadcasting."
        }
    else:
        return {
            "status": "pending",
            "verified": False,
            "message": "Your Facebook Business account is not yet verified. Please complete verification before broadcasting."
        }


# @tool
# def verify_facebook_business(user_id: str, project_id: str) -> str:
#     """
#     Check Facebook Business verification status via MCP.

#     For first-time broadcasters, this checks if their FB Business account
#     is verified. If verified, flips first_broadcasting=False in TempMemory
#     so they can proceed with contact processing.

#     Args:
#         user_id: User's unique identifier
#         project_id: Project ID

#     Returns:
#         JSON string with verification status and next steps
#     """
#     logger.info("[DATA_PROCESSING] verify_facebook_business for user: %s", user_id)
#     try:
#         future = _executor.submit(_run_verify_fb_sync, user_id, project_id)
#         result = future.result(timeout=30)
#         return json.dumps(result, ensure_ascii=False)
#     except Exception as e:
#         logger.error("[DATA_PROCESSING] verify_facebook_business error: %s", e, exc_info=True)
#         return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 3: PROCESS PHONE LIST (Direct input)
# ============================================

def _run_process_phone_list_sync(
    user_id: str,
    broadcast_job_id: str,
    phone_numbers: list,
    default_country: str = "IN",
):
    """Validate, deduplicate, score, and store phone numbers."""
    from app.utils.data_processing.phone_validator import validate_phone
    from app.utils.data_processing.deduplicator import deduplicate_contacts
    from app.utils.data_processing.quality_scorer import score_contacts
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    # Step 1: Validate each phone number
    contacts = []
    invalid_phones = []

    for i, phone in enumerate(phone_numbers):
        phone = str(phone).strip()
        if not phone:
            continue

        is_valid, e164, country = validate_phone(phone, default_country)

        if is_valid:
            contacts.append({
                "phone": phone,
                "phone_e164": e164,
                "country_code": country,
                "name": None,
                "email": None,
                "source_row": i + 1,
                "custom_fields": {},
                "is_valid": True,
                "validation_errors": [],
            })
        else:
            invalid_phones.append({
                "phone": phone,
                "phone_e164": "",
                "country_code": "",
                "name": None,
                "email": None,
                "source_row": i + 1,
                "custom_fields": {},
                "is_valid": False,
                "validation_errors": [f"Invalid phone number: {phone}"],
                "quality_score": 0,
                "is_duplicate": False,
                "duplicate_of": None,
            })

    # Step 2: Deduplicate valid contacts
    unique, duplicates = deduplicate_contacts(contacts, default_country=default_country)

    # Mark duplicates
    dup_records = []
    for d in duplicates:
        d["is_duplicate"] = True
        d["is_valid"] = True
        d["quality_score"] = 0
        dup_records.append(d)

    # Step 3: Quality score unique contacts
    score_contacts(unique)
    for c in unique:
        c["is_duplicate"] = False
        c["duplicate_of"] = None

    # Step 4: Store all contacts in DB
    all_records = unique + dup_records + invalid_phones
    with get_session() as session:
        contact_repo = ProcessedContactRepository(session=session)
        count = contact_repo.bulk_create(all_records, broadcast_job_id, user_id)

        # Update broadcast job with valid phone list
        valid_phones = [c["phone_e164"] for c in unique]
        broadcast_repo = BroadcastJobRepository(session=session)
        broadcast_repo.update_contacts(
            job_id=broadcast_job_id,
            contacts_data=json.dumps(valid_phones),
            total=len(phone_numbers),
            valid=len(unique),
            invalid=len(invalid_phones)
        )

    # Build quality distribution
    scores = [c.get("quality_score", 0) for c in unique]
    avg_score = sum(scores) / len(scores) if scores else 0

    # Country breakdown
    countries = {}
    for c in unique:
        cc = c.get("country_code", "UNKNOWN")
        countries[cc] = countries.get(cc, 0) + 1

    return {
        "status": "success" if len(unique) > 0 else "failed",
        "total_provided": len(phone_numbers),
        "valid_count": len(unique),
        "invalid_count": len(invalid_phones),
        "duplicates_removed": len(duplicates),
        "duplicate_breakdown": _count_dedup_stages(duplicates),
        "avg_quality_score": round(avg_score, 1),
        "quality_distribution": {
            "high": sum(1 for s in scores if s >= 70),
            "medium": sum(1 for s in scores if 40 <= s < 70),
            "low": sum(1 for s in scores if s < 40),
        },
        "country_breakdown": countries,
        "invalid_numbers": [p["phone"] for p in invalid_phones[:10]],
        "records_stored": count,
        "message": (
            f"Processed {len(phone_numbers)} contacts: "
            f"{len(unique)} valid, {len(invalid_phones)} invalid, "
            f"{len(duplicates)} duplicates removed. "
            f"Average quality score: {avg_score:.0f}/100."
        ),
    }


@tool
def process_phone_list(
    user_id: str,
    broadcast_job_id: str,
    phone_numbers: list,
    default_country: str = "IN",
) -> str:
    """
    Validate, deduplicate, and score a list of phone numbers.

    Runs the full data processing pipeline:
    1. E.164 phone validation (using phonenumbers library)
    2. 4-stage deduplication (exact, normalized, fuzzy, cross-campaign)
    3. Quality scoring (0-100 based on validity, completeness, recency, engagement)
    4. Store processed contacts in database

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID from initialize_broadcast
        phone_numbers: List of phone number strings
        default_country: Default country code for numbers without country prefix (default "IN")

    Returns:
        JSON string with processing results including quality distribution
    """
    logger.info("[DATA_PROCESSING] process_phone_list: %d numbers", len(phone_numbers))
    try:
        future = _executor.submit(
            _run_process_phone_list_sync,
            user_id=user_id,
            broadcast_job_id=broadcast_job_id,
            phone_numbers=phone_numbers,
            default_country=default_country,
        )
        result = future.result(timeout=60)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DATA_PROCESSING] process_phone_list error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 4: PROCESS CONTACT FILE (File upload)
# ============================================

def _run_process_file_sync(
    user_id: str,
    broadcast_job_id: str,
    file_path: str,
    phone_column: str = None,
    name_column: str = None,
    default_country: str = "IN",
):
    """Parse file, validate, deduplicate, score, and store contacts."""
    from app.utils.data_processing.file_parser import parse_file
    from app.utils.data_processing.phone_validator import validate_phone
    from app.utils.data_processing.deduplicator import deduplicate_contacts
    from app.utils.data_processing.quality_scorer import score_contacts
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    # Step 1: Parse file
    raw_contacts = parse_file(file_path, phone_column=phone_column, name_column=name_column)
    logger.info(f"Parsed {len(raw_contacts)} contacts from file")

    if not raw_contacts:
        return {
            "status": "failed",
            "message": "No contacts found in the uploaded file. Please check the file format and column names."
        }

    # Step 2: Validate phone numbers
    valid_contacts = []
    invalid_contacts = []

    for contact in raw_contacts:
        phone = contact.get("phone", "")
        is_valid, e164, country = validate_phone(phone, default_country)

        contact["phone_e164"] = e164
        contact["country_code"] = country
        contact["is_valid"] = is_valid

        if is_valid:
            contact["validation_errors"] = []
            valid_contacts.append(contact)
        else:
            contact["validation_errors"] = [f"Invalid phone: {phone}"]
            contact["quality_score"] = 0
            contact["is_duplicate"] = False
            contact["duplicate_of"] = None
            invalid_contacts.append(contact)

    # Step 3: Deduplicate valid contacts
    unique, duplicates = deduplicate_contacts(valid_contacts, default_country=default_country)

    dup_records = []
    for d in duplicates:
        d["is_duplicate"] = True
        d["quality_score"] = 0
        dup_records.append(d)

    # Step 4: Quality score unique contacts
    score_contacts(unique)
    for c in unique:
        c["is_duplicate"] = False
        c["duplicate_of"] = None

    # Step 5: Store in DB
    all_records = unique + dup_records + invalid_contacts
    with get_session() as session:
        contact_repo = ProcessedContactRepository(session=session)
        count = contact_repo.bulk_create(all_records, broadcast_job_id, user_id)

        valid_phones = [c["phone_e164"] for c in unique]
        broadcast_repo = BroadcastJobRepository(session=session)
        broadcast_repo.update_contacts(
            job_id=broadcast_job_id,
            contacts_data=json.dumps(valid_phones),
            total=len(raw_contacts),
            valid=len(unique),
            invalid=len(invalid_contacts)
        )

    # Quality distribution
    scores = [c.get("quality_score", 0) for c in unique]
    avg_score = sum(scores) / len(scores) if scores else 0

    countries = {}
    for c in unique:
        cc = c.get("country_code", "UNKNOWN")
        countries[cc] = countries.get(cc, 0) + 1

    return {
        "status": "success" if len(unique) > 0 else "failed",
        "file_path": file_path,
        "total_parsed": len(raw_contacts),
        "valid_count": len(unique),
        "invalid_count": len(invalid_contacts),
        "duplicates_removed": len(duplicates),
        "duplicate_breakdown": _count_dedup_stages(duplicates),
        "avg_quality_score": round(avg_score, 1),
        "quality_distribution": {
            "high": sum(1 for s in scores if s >= 70),
            "medium": sum(1 for s in scores if 40 <= s < 70),
            "low": sum(1 for s in scores if s < 40),
        },
        "country_breakdown": countries,
        "invalid_samples": [
            {"phone": c["phone"], "row": c.get("source_row")}
            for c in invalid_contacts[:10]
        ],
        "records_stored": count,
        "message": (
            f"File processed: {len(raw_contacts)} contacts parsed, "
            f"{len(unique)} valid, {len(invalid_contacts)} invalid, "
            f"{len(duplicates)} duplicates removed. "
            f"Average quality score: {avg_score:.0f}/100."
        ),
    }


@tool
def process_contact_file(
    user_id: str,
    broadcast_job_id: str,
    file_path: str,
    phone_column: str = None,
    name_column: str = None,
    default_country: str = "IN",
) -> str:
    """
    Parse and process a contact file (Excel/CSV) for broadcasting.

    Runs the full pipeline:
    1. File parsing with auto-column detection
    2. E.164 phone validation
    3. 4-stage deduplication
    4. Quality scoring (0-100)
    5. Store processed contacts in database

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        file_path: Path to the uploaded file (.xlsx, .xls, .csv)
        phone_column: Explicit phone column name (auto-detected if None)
        name_column: Explicit name column name (auto-detected if None)
        default_country: Default country code (default "IN")

    Returns:
        JSON string with processing results including quality distribution
    """
    logger.info("[DATA_PROCESSING] process_contact_file: file=%s", file_path)
    try:
        future = _executor.submit(
            _run_process_file_sync,
            user_id=user_id,
            broadcast_job_id=broadcast_job_id,
            file_path=file_path,
            phone_column=phone_column,
            name_column=name_column,
            default_country=default_country,
        )
        result = future.result(timeout=120)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DATA_PROCESSING] process_contact_file error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 5: GET PROCESSING SUMMARY
# ============================================

def _run_get_summary_sync(broadcast_job_id: str):
    """Get quality summary from processed_contacts table."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository

    with get_session() as session:
        repo = ProcessedContactRepository(session=session)
        summary = repo.get_quality_summary(broadcast_job_id)

    return {
        "status": "success",
        "summary": summary,
        "message": (
            f"Processing summary: {summary['valid_count']} valid contacts, "
            f"avg score {summary['avg_score']}/100, "
            f"{summary['duplicate_count']} duplicates removed."
        ),
    }


@tool
def get_processing_summary(broadcast_job_id: str) -> str:
    """
    Get data processing summary for a broadcast job.

    Returns quality score distribution, country breakdown,
    invalid count, and duplicate count.

    Args:
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with processing summary and quality metrics
    """
    logger.info("[DATA_PROCESSING] get_processing_summary: job=%s", broadcast_job_id)
    try:
        future = _executor.submit(_run_get_summary_sync, broadcast_job_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[DATA_PROCESSING] get_processing_summary error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# HELPER
# ============================================

def _count_dedup_stages(duplicates: list) -> dict:
    """Count duplicates by dedup stage."""
    counts = {}
    for d in duplicates:
        stage = d.get("dedup_stage", "unknown")
        counts[stage] = counts.get(stage, 0) + 1
    return counts


# ============================================
# TOOLS EXPORT
# ============================================

BACKEND_TOOLS = [
    check_beginner_status,
    # verify_facebook_business,
    process_phone_list,
    process_contact_file,
    get_processing_summary,
]

BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
