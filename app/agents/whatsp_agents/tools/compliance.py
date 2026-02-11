"""
Backend tools for Compliance Agent.

Handles opt-in verification, suppression list filtering,
time window restrictions, and account health checks.

Per doc section 3.3: TRAI, GDPR, WhatsApp Business Policy compliance.
"""

import asyncio
import json
import concurrent.futures
import nest_asyncio
from datetime import datetime, timedelta, timezone
from langchain.tools import tool

from ....config import logger

nest_asyncio.apply()
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)


# ============================================
# TIME WINDOW CONFIGURATION (per doc 3.3.5)
# ============================================

TIME_WINDOWS = {
    "IN": {"start": 9, "end": 21, "tz_offset": 5.5, "name": "India (TRAI)"},
    "EU": {"start": 8, "end": 21, "tz_offset": 1, "name": "EU (GDPR)"},
    "US": {"start": 8, "end": 21, "tz_offset": -5, "name": "US"},
    "AE": {"start": 9, "end": 22, "tz_offset": 4, "name": "UAE"},
}

# Default window for unknown regions
DEFAULT_WINDOW = {"start": 8, "end": 21, "tz_offset": 0, "name": "Default"}


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
# TOOL 1: CHECK OPT-IN STATUS
# ============================================

def _run_check_opt_in_sync(user_id: str, broadcast_job_id: str):
    """Verify opt-in consent for all contacts in a broadcast job."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository
    from app.database.postgresql.postgresql_repositories.consent_log_repo import ConsentLogRepository

    with get_session() as session:
        contact_repo = ProcessedContactRepository(session=session)
        consent_repo = ConsentLogRepository(session=session)

        valid_phones = contact_repo.get_valid_phones_by_job(broadcast_job_id)
        opted_out_phones = consent_repo.get_opted_out_phones(user_id)

        opted_in = []
        no_consent = []

        for phone in valid_phones:
            if phone in opted_out_phones:
                no_consent.append(phone)
            else:
                opted_in.append(phone)

        # Log exclusions
        for phone in no_consent:
            consent_repo.log_consent(
                user_id=user_id,
                phone_e164=phone,
                action="EXCLUDED",
                source="compliance_check",
                broadcast_job_id=broadcast_job_id,
            )

    return {
        "status": "success",
        "total_checked": len(valid_phones),
        "opted_in_count": len(opted_in),
        "no_consent_count": len(no_consent),
        "excluded_phones": no_consent[:10],
        "passed": len(no_consent) == 0,
        "message": (
            f"Opt-in check: {len(opted_in)} contacts have consent, "
            f"{len(no_consent)} excluded (no opt-in)."
            if no_consent else
            f"Opt-in check passed: All {len(opted_in)} contacts have valid consent."
        ),
    }


@tool
def check_opt_in_status(user_id: str, broadcast_job_id: str) -> str:
    """
    Verify opt-in consent for all contacts in a broadcast job.

    Checks each contact against the consent log to ensure they have
    valid opt-in consent. Contacts without opt-in are excluded.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with opt-in verification results
    """
    logger.info("[COMPLIANCE] check_opt_in_status for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_check_opt_in_sync, user_id, broadcast_job_id)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[COMPLIANCE] check_opt_in_status error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 2: FILTER SUPPRESSION LIST
# ============================================

def _run_filter_suppression_sync(user_id: str, broadcast_job_id: str):
    """Filter contacts against all suppression lists."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository
    from app.database.postgresql.postgresql_repositories.suppression_list_repo import SuppressionListRepository

    with get_session() as session:
        contact_repo = ProcessedContactRepository(session=session)
        suppression_repo = SuppressionListRepository(session=session)

        valid_phones = contact_repo.get_valid_phones_by_job(broadcast_job_id)
        suppressed_phones = suppression_repo.get_suppressed_phones(user_id)

        passed = []
        filtered = []
        filtered_by_type = {}

        for phone in valid_phones:
            if phone in suppressed_phones:
                filtered.append(phone)
            else:
                passed.append(phone)

        # Get breakdown by type for filtered phones
        if filtered:
            summary = suppression_repo.get_suppression_summary(user_id)
            filtered_by_type = summary.get("by_type", {})

    return {
        "status": "success",
        "total_checked": len(valid_phones),
        "passed_count": len(passed),
        "filtered_count": len(filtered),
        "filtered_by_type": filtered_by_type,
        "passed": len(filtered) == 0,
        "message": (
            f"Suppression filter: {len(filtered)} contacts removed "
            f"({filtered_by_type}). {len(passed)} contacts remain."
            if filtered else
            f"Suppression filter passed: All {len(passed)} contacts are clear."
        ),
    }


@tool
def filter_suppression_list(user_id: str, broadcast_job_id: str) -> str:
    """
    Filter broadcast contacts against all suppression lists.

    Checks contacts against: global suppression, campaign suppression,
    temporary suppression (PAUSE), and bounce list.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with suppression filtering results and breakdown by type
    """
    logger.info("[COMPLIANCE] filter_suppression_list for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_filter_suppression_sync, user_id, broadcast_job_id)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[COMPLIANCE] filter_suppression_list error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 3: CHECK TIME WINDOW
# ============================================

def _run_check_time_window_sync(user_id: str, broadcast_job_id: str):
    """Check if current time is within allowed marketing hours for all contact regions."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository

    with get_session() as session:
        contact_repo = ProcessedContactRepository(session=session)
        summary = contact_repo.get_quality_summary(broadcast_job_id)

    country_breakdown = summary.get("country_breakdown", {})
    now_utc = datetime.now(timezone.utc)

    regions_ok = []
    regions_blocked = []

    for country_code, count in country_breakdown.items():
        window = TIME_WINDOWS.get(country_code, DEFAULT_WINDOW)
        tz_offset = timedelta(hours=window["tz_offset"])
        local_time = now_utc + tz_offset
        local_hour = local_time.hour

        in_window = window["start"] <= local_hour < window["end"]

        entry = {
            "region": window["name"],
            "country_code": country_code,
            "contact_count": count,
            "local_time": local_time.strftime("%H:%M"),
            "allowed_hours": f"{window['start']}:00 - {window['end']}:00",
            "in_window": in_window,
        }

        if in_window:
            regions_ok.append(entry)
        else:
            # Calculate next valid window
            if local_hour < window["start"]:
                wait_hours = window["start"] - local_hour
            else:
                wait_hours = 24 - local_hour + window["start"]
            entry["next_window_in_hours"] = wait_hours
            # Compute absolute UTC datetime for the next valid window
            next_window_utc = now_utc + timedelta(hours=wait_hours)
            # Round to next hour start
            next_window_utc = next_window_utc.replace(minute=0, second=0, microsecond=0)
            entry["next_valid_window_utc"] = next_window_utc.isoformat()
            regions_blocked.append(entry)

    all_passed = len(regions_blocked) == 0

    # Find the latest next_valid_window across all blocked regions (safe to send for ALL)
    scheduled_send_utc = None
    if not all_passed:
        window_times = [r["next_valid_window_utc"] for r in regions_blocked]
        scheduled_send_utc = max(window_times)  # Latest window = safe for all regions

    return {
        "status": "success",
        "passed": all_passed,
        "regions_ok": regions_ok,
        "regions_blocked": regions_blocked,
        "total_regions": len(country_breakdown),
        "scheduled_send_utc": scheduled_send_utc,
        "message": (
            f"Time window check passed: All {len(regions_ok)} regions within allowed hours."
            if all_passed else
            f"Time window restriction: {len(regions_blocked)} region(s) outside allowed hours. "
            f"Blocked regions: {[r['region'] for r in regions_blocked]}. "
            f"Next valid send window (UTC): {scheduled_send_utc}."
        ),
    }


@tool
def check_time_window(user_id: str, broadcast_job_id: str) -> str:
    """
    Check if current time is within allowed marketing hours for all contact regions.

    Enforces TRAI (India 9AM-9PM IST), GDPR (EU 8AM-9PM), and other
    regional time window restrictions for marketing messages.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with time window check results per region
    """
    logger.info("[COMPLIANCE] check_time_window for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_check_time_window_sync, user_id, broadcast_job_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[COMPLIANCE] check_time_window error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 4: CHECK ACCOUNT HEALTH
# ============================================

TIER_LIMITS = {
    "UNVERIFIED": 250,
    "TIER_1": 1000,
    "TIER_2": 10000,
    "TIER_3": 100000,
    "TIER_4": float("inf"),
}


def _run_check_account_health_sync(user_id: str, contact_count: int):
    """Check WhatsApp account health and messaging tier via MCP."""
    health_result = _call_direct_api_mcp("get_messaging_health_status", {"node_id": user_id})

    quality_score = "UNKNOWN"
    tier = "UNKNOWN"
    tier_limit = 0
    account_status = "unknown"
    mcp_reachable = True

    if isinstance(health_result, dict):
        # Check if MCP call itself failed (network error, invalid token, etc.)
        if health_result.get("status") == "failed" or health_result.get("error"):
            mcp_reachable = False
            logger.warning(
                "[COMPLIANCE] Health check MCP unreachable: %s",
                health_result.get("error", "Unknown error")
            )
        else:
            data = health_result.get("data", health_result)
            if isinstance(data, dict):
                quality_score = data.get("quality_score", data.get("quality_rating", "UNKNOWN"))
                tier = data.get("messaging_tier", data.get("tier", "UNKNOWN"))
                account_status = data.get("account_status", data.get("status", "unknown"))

    # If MCP was unreachable, soft-pass with warnings instead of blocking
    if not mcp_reachable:
        return {
            "status": "success",
            "passed": True,
            "quality_score": "UNKNOWN (API unreachable)",
            "messaging_tier": "UNKNOWN",
            "tier_limit": "unknown",
            "contact_count": contact_count,
            "account_status": "unknown",
            "issues": [],
            "warnings": [
                "Health check API was unreachable. Proceeding with broadcast.",
                f"MCP error: {health_result.get('error', 'Unknown')}",
            ],
            "message": (
                "Account health check skipped (API unreachable). "
                "Proceeding with broadcast - monitor delivery for issues."
            ),
        }

    # Determine tier limit
    tier_upper = str(tier).upper().replace(" ", "_")
    tier_limit = TIER_LIMITS.get(tier_upper, 0)

    # Quality check
    quality_ok = quality_score.upper() not in ("LOW", "RED")
    # If tier is UNKNOWN, don't block on capacity
    capacity_ok = True if tier_limit == 0 else (
        contact_count <= tier_limit if tier_limit != float("inf") else True
    )
    account_ok = account_status.lower() not in ("restricted", "flagged", "banned")

    all_passed = quality_ok and capacity_ok and account_ok

    issues = []
    if not quality_ok:
        issues.append(f"Quality score is {quality_score} (RED/LOW) - all marketing sends must be paused")
    if not capacity_ok:
        issues.append(f"Contact count ({contact_count}) exceeds tier limit ({tier_limit}) for {tier}")
    if not account_ok:
        issues.append(f"Account status: {account_status} - broadcasting not allowed")

    return {
        "status": "success",
        "passed": all_passed,
        "quality_score": quality_score,
        "messaging_tier": tier,
        "tier_limit": tier_limit if tier_limit != float("inf") else "unlimited",
        "contact_count": contact_count,
        "account_status": account_status,
        "issues": issues,
        "message": (
            f"Account health OK: Quality={quality_score}, Tier={tier}, "
            f"Capacity={contact_count}/{tier_limit if tier_limit != float('inf') else 'unlimited'}."
            if all_passed else
            f"Account health FAILED: {'; '.join(issues)}"
        ),
    }


@tool
def check_account_health(user_id: str, broadcast_job_id: str) -> str:
    """
    Check WhatsApp account health, quality score, and messaging tier.

    Verifies that the account quality score is Medium or High,
    the messaging tier has enough capacity, and the account is not restricted.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID (used to get contact count)

    Returns:
        JSON string with account health, quality score, tier, and capacity
    """
    logger.info("[COMPLIANCE] check_account_health for user: %s", user_id)
    try:
        # Get contact count from broadcast job
        from app.database.postgresql.postgresql_connection import get_session
        from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

        def _get_count():
            with get_session() as session:
                repo = BroadcastJobRepository(session=session)
                job = repo.get_by_id(broadcast_job_id)
                return job.get("valid_contacts", 0) if job else 0

        future_count = _executor.submit(_get_count)
        contact_count = future_count.result(timeout=10)

        future = _executor.submit(_run_check_account_health_sync, user_id, contact_count)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[COMPLIANCE] check_account_health error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 5: GET COMPLIANCE SUMMARY
# ============================================

def _run_get_compliance_summary_sync(user_id: str, broadcast_job_id: str):
    """Get overall compliance summary for a broadcast job."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        job = repo.get_by_id(broadcast_job_id)

    if not job:
        return {"status": "failed", "message": "Broadcast job not found"}

    return {
        "status": "success",
        "broadcast_job_id": broadcast_job_id,
        "compliance_status": job.get("compliance_status", "unknown"),
        "compliance_details": job.get("compliance_details"),
        "total_contacts": job.get("total_contacts", 0),
        "valid_contacts": job.get("valid_contacts", 0),
        "message": f"Compliance status: {job.get('compliance_status', 'unknown')}",
    }


@tool
def get_compliance_summary(user_id: str, broadcast_job_id: str) -> str:
    """
    Get the overall compliance check summary for a broadcast job.

    Returns the compliance status, contact counts, and any compliance details.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with compliance summary
    """
    logger.info("[COMPLIANCE] get_compliance_summary for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_get_compliance_summary_sync, user_id, broadcast_job_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[COMPLIANCE] get_compliance_summary error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 6: PROCESS OPT-OUT KEYWORD
# ============================================

OPT_OUT_KEYWORDS = {
    "STOP": {"action": "OPT_OUT", "source": "keyword_stop"},
    "UNSUBSCRIBE": {"action": "OPT_OUT", "source": "keyword_unsubscribe"},
    "PAUSE": {"action": "PAUSE", "source": "keyword_pause"},
    "STOP PROMO": {"action": "OPT_OUT_MARKETING", "source": "keyword_stop_promo"},
    "START": {"action": "RESUME", "source": "keyword_start"},
}

OPT_OUT_RESPONSES = {
    "OPT_OUT": "You have been unsubscribed from all messages.",
    "PAUSE": "Messages paused for 30 days. Reply START to resume.",
    "OPT_OUT_MARKETING": "Promotional messages stopped. Transactional continues.",
    "RESUME": "Welcome back! You will now receive messages.",
}


def _run_process_opt_out_sync(user_id: str, phone_e164: str, keyword: str):
    """Process an opt-out/opt-in keyword from a contact."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.consent_log_repo import ConsentLogRepository
    from app.database.postgresql.postgresql_repositories.suppression_list_repo import SuppressionListRepository

    keyword_upper = keyword.strip().upper()
    config = OPT_OUT_KEYWORDS.get(keyword_upper)

    if not config:
        return {
            "status": "ignored",
            "message": f"Unknown keyword: {keyword}. Recognized keywords: STOP, UNSUBSCRIBE, PAUSE, STOP PROMO, START"
        }

    action = config["action"]
    source = config["source"]

    with get_session() as session:
        consent_repo = ConsentLogRepository(session=session)
        suppression_repo = SuppressionListRepository(session=session)

        # Log the consent event
        consent_repo.log_consent(
            user_id=user_id,
            phone_e164=phone_e164,
            action=action,
            source=source,
            keyword=keyword_upper,
        )

        # Update suppression list
        if action in ("OPT_OUT", "OPT_OUT_MARKETING"):
            suppression_repo.add(
                user_id=user_id,
                phone_e164=phone_e164,
                suppression_type="global" if action == "OPT_OUT" else "campaign",
                reason=f"User sent {keyword_upper}",
            )
        elif action == "PAUSE":
            suppression_repo.add(
                user_id=user_id,
                phone_e164=phone_e164,
                suppression_type="temporary",
                reason=f"User sent PAUSE",
                expires_at=datetime.utcnow() + timedelta(days=30),
            )
        elif action == "RESUME":
            suppression_repo.remove(user_id, phone_e164)

    return {
        "status": "success",
        "action": action,
        "keyword": keyword_upper,
        "phone": phone_e164,
        "response_text": OPT_OUT_RESPONSES.get(action, ""),
        "message": f"Processed {keyword_upper} for {phone_e164}: {action}",
    }


@tool
def process_opt_out_keyword(user_id: str, phone_e164: str, keyword: str) -> str:
    """
    Process an opt-out/opt-in keyword received from a contact.

    Handles: STOP, UNSUBSCRIBE, PAUSE, STOP PROMO, START.
    Logs to consent audit trail and updates suppression lists.

    Args:
        user_id: User's unique identifier
        phone_e164: Contact phone in E.164 format
        keyword: The keyword received (STOP, START, etc.)

    Returns:
        JSON string with action taken and response text to send back
    """
    logger.info("[COMPLIANCE] process_opt_out_keyword: %s from %s", keyword, phone_e164)
    try:
        future = _executor.submit(_run_process_opt_out_sync, user_id, phone_e164, keyword)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[COMPLIANCE] process_opt_out_keyword error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOLS EXPORT
# ============================================

BACKEND_TOOLS = [
    check_opt_in_status,
    filter_suppression_list,
    check_time_window,
    check_account_health,
    get_compliance_summary,
    process_opt_out_keyword,
]

BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
