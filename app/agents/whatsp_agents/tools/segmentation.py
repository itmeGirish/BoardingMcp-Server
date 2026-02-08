"""
Backend tools for Segmentation Agent.

Handles lifecycle classification, 24-hour window detection,
timezone clustering, frequency capping, and audience segment creation.

Per doc section 3.4: Behavioral, demographic, lifecycle analysis,
timezone clustering, and frequency capping.
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
# LIFECYCLE STAGE DEFINITIONS (per doc 3.4.2)
# ============================================

LIFECYCLE_STAGES = {
    "new": {"max_days": 7, "label": "New", "action": "Welcome series, onboarding content"},
    "engaged": {"max_days": 30, "label": "Engaged", "action": "Regular campaigns, promotions"},
    "active": {"max_days": 60, "label": "Active", "action": "Loyalty rewards, exclusive offers"},
    "at_risk": {"max_days": 60, "label": "At-Risk", "action": "Re-engagement campaign, feedback"},
    "dormant": {"max_days": 90, "label": "Dormant", "action": "Win-back offer, final warning"},
    "churned": {"max_days": None, "label": "Churned", "action": "Exclude from broadcasts"},
}


# ============================================
# FREQUENCY CAP DEFAULTS (per doc 3.4.5)
# ============================================

FREQUENCY_CAPS = {
    "marketing": {"default": 2, "min": 1, "max": 5, "period_days": 7},
    "transactional": {"default": None, "min": None, "max": None, "period_days": None},
    "promotional": {"default": 1, "min": 1, "max": 3, "period_days": 7},
    "combined": {"default": 4, "min": 2, "max": 7, "period_days": 7},
}


# ============================================
# TIMEZONE MAP (from phone country code)
# ============================================

COUNTRY_TIMEZONE_OFFSETS = {
    "IN": 5.5, "US": -5, "GB": 0, "DE": 1, "FR": 1,
    "AE": 4, "SA": 3, "SG": 8, "AU": 10, "JP": 9,
    "BR": -3, "CA": -5, "MX": -6, "ZA": 2, "NG": 1,
    "KE": 3, "EG": 2, "PH": 8, "ID": 7, "MY": 8,
    "TH": 7, "VN": 7, "KR": 9, "CN": 8, "RU": 3,
}

OPTIMAL_SEND_HOURS = (10, 14)  # 10 AM to 2 PM local time


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
# TOOL 1: CLASSIFY LIFECYCLE STAGES
# ============================================

def _run_classify_lifecycle_sync(user_id: str, broadcast_job_id: str):
    """Classify contacts into lifecycle stages based on interaction history."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository
    from app.database.postgresql.postgresql_repositories.consent_log_repo import ConsentLogRepository

    with get_session() as session:
        contact_repo = ProcessedContactRepository(session=session)
        consent_repo = ConsentLogRepository(session=session)

        contacts = contact_repo.get_by_broadcast_job(broadcast_job_id)
        now = datetime.utcnow()

        stages = {
            "new": [], "engaged": [], "active": [],
            "at_risk": [], "dormant": [], "churned": [],
        }

        for contact in contacts:
            if contact.get("is_duplicate"):
                continue

            phone = contact["phone_e164"]
            latest = consent_repo.get_latest_consent(user_id, phone)

            if latest and latest.get("created_at"):
                last_interaction = datetime.fromisoformat(latest["created_at"])
                days_since = (now - last_interaction).days
            else:
                # No consent record - treat as new (from manual import)
                days_since = 0

            if days_since <= 7:
                stages["new"].append(phone)
            elif days_since <= 30:
                stages["engaged"].append(phone)
            elif days_since <= 60:
                stages["active"].append(phone)
            elif days_since <= 90:
                # Check if they were active before (60+ days tenure)
                # vs just at risk (no interaction 31-60 days)
                if days_since <= 60:
                    stages["active"].append(phone)
                else:
                    stages["at_risk"].append(phone)
            elif days_since <= 90:
                stages["dormant"].append(phone)
            else:
                stages["churned"].append(phone)

    stage_counts = {k: len(v) for k, v in stages.items()}
    total = sum(stage_counts.values())
    excluded = len(stages["churned"])

    return {
        "status": "success",
        "total_classified": total,
        "stages": stage_counts,
        "churned_excluded": excluded,
        "eligible_count": total - excluded,
        "stage_details": {
            k: {"count": len(v), "action": LIFECYCLE_STAGES[k]["action"]}
            for k, v in stages.items()
        },
        "message": (
            f"Lifecycle classification: {total} contacts classified. "
            f"{excluded} churned contacts will be excluded. "
            f"{total - excluded} eligible for broadcast."
        ),
    }


@tool
def classify_lifecycle_stages(user_id: str, broadcast_job_id: str) -> str:
    """
    Classify broadcast contacts into lifecycle stages.

    Stages: New (<=7d), Engaged (<=30d), Active (<=60d),
    At-Risk (31-60d inactive), Dormant (61-90d), Churned (90+d).
    Churned contacts are excluded from broadcasts.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with lifecycle stage counts and exclusions
    """
    logger.info("[SEGMENTATION] classify_lifecycle_stages for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_classify_lifecycle_sync, user_id, broadcast_job_id)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[SEGMENTATION] classify_lifecycle_stages error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 2: DETECT 24-HOUR WINDOWS
# ============================================

def _run_detect_24hr_windows_sync(user_id: str, broadcast_job_id: str):
    """Detect contacts within the free 24-hour service window."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository

    # Try to get last message timestamps via MCP
    try:
        conversations = _call_direct_api_mcp("get_recent_conversations", {"user_id": user_id})
    except Exception:
        conversations = {}

    # Build phone -> last_message_time map from conversations
    last_message_map = {}
    if isinstance(conversations, dict):
        data = conversations.get("data", conversations.get("conversations", []))
        if isinstance(data, list):
            for conv in data:
                phone = conv.get("phone", conv.get("from", ""))
                ts = conv.get("last_message_time", conv.get("timestamp", ""))
                if phone and ts:
                    try:
                        last_message_map[phone] = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass

    now = datetime.now(timezone.utc)
    window_cutoff = now - timedelta(hours=24)

    with get_session() as session:
        contact_repo = ProcessedContactRepository(session=session)
        valid_phones = contact_repo.get_valid_phones_by_job(broadcast_job_id)

    in_window = []
    outside_window = []

    for phone in valid_phones:
        last_msg = last_message_map.get(phone)
        if last_msg and last_msg > window_cutoff:
            in_window.append(phone)
        else:
            outside_window.append(phone)

    # Estimate cost savings (marketing messages in India: ~₹0.88 each)
    estimated_savings = len(in_window) * 0.88

    return {
        "status": "success",
        "total_checked": len(valid_phones),
        "in_24hr_window": len(in_window),
        "outside_window": len(outside_window),
        "estimated_savings_inr": round(estimated_savings, 2),
        "priority_contacts": in_window[:20],  # Show first 20 for preview
        "message": (
            f"24-hour window detection: {len(in_window)} contacts in active window "
            f"(FREE messaging). {len(outside_window)} outside window. "
            f"Estimated savings: ₹{estimated_savings:.2f}"
        ),
    }


@tool
def detect_24hr_windows(user_id: str, broadcast_job_id: str) -> str:
    """
    Detect contacts within the free 24-hour WhatsApp service window.

    Messages to contacts who messaged the business within 24 hours are FREE.
    Prioritizing these contacts first can reduce campaign costs by 30-50%.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with window detection results and cost savings estimate
    """
    logger.info("[SEGMENTATION] detect_24hr_windows for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_detect_24hr_windows_sync, user_id, broadcast_job_id)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[SEGMENTATION] detect_24hr_windows error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 3: CLUSTER BY TIMEZONE
# ============================================

def _run_cluster_by_timezone_sync(user_id: str, broadcast_job_id: str):
    """Group contacts by timezone for optimal delivery timing."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository

    with get_session() as session:
        contact_repo = ProcessedContactRepository(session=session)
        contacts = contact_repo.get_by_broadcast_job(broadcast_job_id)

    now_utc = datetime.now(timezone.utc)
    clusters = {}  # tz_offset -> {phones, country_codes, local_time, optimal_send}

    for contact in contacts:
        if contact.get("is_duplicate"):
            continue

        country = contact.get("country_code", "").upper()
        tz_offset = COUNTRY_TIMEZONE_OFFSETS.get(country, 0)

        tz_key = f"UTC{'+' if tz_offset >= 0 else ''}{tz_offset}"

        if tz_key not in clusters:
            local_time = now_utc + timedelta(hours=tz_offset)
            local_hour = local_time.hour

            # Calculate optimal send time
            if local_hour < OPTIMAL_SEND_HOURS[0]:
                wait_hours = OPTIMAL_SEND_HOURS[0] - local_hour
            elif local_hour >= OPTIMAL_SEND_HOURS[1]:
                wait_hours = 24 - local_hour + OPTIMAL_SEND_HOURS[0]
            else:
                wait_hours = 0

            clusters[tz_key] = {
                "offset": tz_offset,
                "countries": set(),
                "count": 0,
                "local_time": local_time.strftime("%H:%M"),
                "in_optimal_window": OPTIMAL_SEND_HOURS[0] <= local_hour < OPTIMAL_SEND_HOURS[1],
                "wait_hours_to_optimal": wait_hours,
                "optimal_window": f"{OPTIMAL_SEND_HOURS[0]}:00 - {OPTIMAL_SEND_HOURS[1]}:00",
            }

        clusters[tz_key]["countries"].add(country or "UNKNOWN")
        clusters[tz_key]["count"] += 1

    # Convert sets to lists for JSON serialization
    for tz_key in clusters:
        clusters[tz_key]["countries"] = sorted(clusters[tz_key]["countries"])

    # Sort clusters by count descending
    sorted_clusters = dict(sorted(clusters.items(), key=lambda x: x[1]["count"], reverse=True))

    # Count contacts in optimal window right now
    in_optimal = sum(c["count"] for c in clusters.values() if c["in_optimal_window"])
    total = sum(c["count"] for c in clusters.values())

    return {
        "status": "success",
        "total_clustered": total,
        "timezone_count": len(clusters),
        "in_optimal_window_now": in_optimal,
        "clusters": sorted_clusters,
        "message": (
            f"Timezone clustering: {total} contacts across {len(clusters)} timezones. "
            f"{in_optimal} contacts currently in optimal send window (10AM-2PM local)."
        ),
    }


@tool
def cluster_by_timezone(user_id: str, broadcast_job_id: str) -> str:
    """
    Group broadcast contacts by timezone for optimal delivery timing.

    Detects timezone from phone country code and calculates optimal
    send time (10 AM - 2 PM local) for each timezone cluster.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with timezone clusters, optimal windows, and delivery schedule
    """
    logger.info("[SEGMENTATION] cluster_by_timezone for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_cluster_by_timezone_sync, user_id, broadcast_job_id)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[SEGMENTATION] cluster_by_timezone error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 4: CHECK FREQUENCY CAPS
# ============================================

def _run_check_frequency_caps_sync(
    user_id: str, broadcast_job_id: str, campaign_type: str = "marketing"
):
    """Check frequency caps to prevent message fatigue."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    cap_config = FREQUENCY_CAPS.get(campaign_type, FREQUENCY_CAPS["marketing"])
    combined_config = FREQUENCY_CAPS["combined"]

    if cap_config["default"] is None:
        # Transactional - no frequency cap
        with get_session() as session:
            contact_repo = ProcessedContactRepository(session=session)
            valid_phones = contact_repo.get_valid_phones_by_job(broadcast_job_id)
        return {
            "status": "success",
            "campaign_type": campaign_type,
            "cap_applied": False,
            "total_contacts": len(valid_phones),
            "eligible_count": len(valid_phones),
            "capped_count": 0,
            "message": f"Transactional messages: No frequency cap applied. All {len(valid_phones)} contacts eligible.",
        }

    with get_session() as session:
        contact_repo = ProcessedContactRepository(session=session)
        broadcast_repo = BroadcastJobRepository(session=session)

        valid_phones = contact_repo.get_valid_phones_by_job(broadcast_job_id)

        # Get recent broadcast jobs for this user (within rolling period)
        cutoff = datetime.utcnow() - timedelta(days=cap_config["period_days"])
        recent_jobs = broadcast_repo.get_active_by_user(user_id)

        # Count messages sent to each phone in the rolling period
        phone_message_count = {}
        for job in recent_jobs:
            if job["id"] == broadcast_job_id:
                continue  # Skip current job
            if not job.get("completed_at"):
                continue
            completed = datetime.fromisoformat(job["completed_at"])
            if completed < cutoff:
                continue
            # Get contacts from completed jobs
            if job.get("contacts_data"):
                try:
                    sent_phones = json.loads(job["contacts_data"])
                    for phone in sent_phones:
                        phone_message_count[phone] = phone_message_count.get(phone, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    pass

    # Check caps
    eligible = []
    capped = []
    type_cap = cap_config["default"]
    combined_cap = combined_config["default"]

    for phone in valid_phones:
        count = phone_message_count.get(phone, 0)
        if count >= type_cap or count >= combined_cap:
            capped.append({"phone": phone, "messages_this_period": count})
        else:
            eligible.append(phone)

    return {
        "status": "success",
        "campaign_type": campaign_type,
        "cap_applied": True,
        "frequency_cap": f"{type_cap} per {cap_config['period_days']} days",
        "combined_cap": f"{combined_cap} per {combined_config['period_days']} days",
        "total_contacts": len(valid_phones),
        "eligible_count": len(eligible),
        "capped_count": len(capped),
        "capped_preview": capped[:10],
        "message": (
            f"Frequency cap check ({campaign_type}): "
            f"{len(capped)} contacts exceeded cap ({type_cap}/week). "
            f"{len(eligible)} contacts eligible."
        ),
    }


@tool
def check_frequency_caps(
    user_id: str, broadcast_job_id: str, campaign_type: str = "marketing"
) -> str:
    """
    Check frequency caps to prevent message fatigue and reduce blocks.

    Caps: Marketing 2/week, Promotional 1/week, Combined 4/week.
    Transactional has no limit. Contacts exceeding caps are excluded.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        campaign_type: Type of campaign (marketing, transactional, promotional)

    Returns:
        JSON string with frequency cap check results
    """
    logger.info("[SEGMENTATION] check_frequency_caps for job: %s, type: %s", broadcast_job_id, campaign_type)
    try:
        future = _executor.submit(
            _run_check_frequency_caps_sync, user_id, broadcast_job_id, campaign_type
        )
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[SEGMENTATION] check_frequency_caps error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 5: CREATE AUDIENCE SEGMENTS
# ============================================

def _run_create_segments_sync(
    user_id: str, broadcast_job_id: str, segment_by: str = "lifecycle"
):
    """Create audience segments based on analysis results."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository
    from app.database.postgresql.postgresql_repositories.consent_log_repo import ConsentLogRepository

    with get_session() as session:
        contact_repo = ProcessedContactRepository(session=session)
        broadcast_repo = BroadcastJobRepository(session=session)

        contacts = contact_repo.get_by_broadcast_job(broadcast_job_id)
        now = datetime.utcnow()

        segments = []

        if segment_by == "all":
            # Single segment with all valid contacts
            valid = [c for c in contacts if not c.get("is_duplicate")]
            segments.append({
                "name": "All Contacts",
                "criteria": "all",
                "contact_count": len(valid),
            })
        elif segment_by == "lifecycle":
            # Segment by lifecycle stage
            consent_repo = ConsentLogRepository(session=session)
            stage_buckets = {
                "new": [], "engaged": [], "active": [],
                "at_risk": [], "dormant": [],
            }
            excluded_churned = 0

            for contact in contacts:
                if contact.get("is_duplicate"):
                    continue
                phone = contact["phone_e164"]
                latest = consent_repo.get_latest_consent(user_id, phone)

                if latest and latest.get("created_at"):
                    last_dt = datetime.fromisoformat(latest["created_at"])
                    days = (now - last_dt).days
                else:
                    days = 0

                if days <= 7:
                    stage_buckets["new"].append(phone)
                elif days <= 30:
                    stage_buckets["engaged"].append(phone)
                elif days <= 60:
                    stage_buckets["active"].append(phone)
                elif days <= 90:
                    stage_buckets["at_risk"].append(phone)
                else:
                    # Dormant or churned
                    if days <= 90:
                        stage_buckets["dormant"].append(phone)
                    else:
                        excluded_churned += 1

            for stage, phones in stage_buckets.items():
                if phones:
                    segments.append({
                        "name": LIFECYCLE_STAGES[stage]["label"],
                        "criteria": f"lifecycle_{stage}",
                        "contact_count": len(phones),
                        "recommended_action": LIFECYCLE_STAGES[stage]["action"],
                    })

        elif segment_by == "country":
            # Segment by country code
            country_buckets = {}
            for contact in contacts:
                if contact.get("is_duplicate"):
                    continue
                cc = contact.get("country_code", "UNKNOWN") or "UNKNOWN"
                country_buckets.setdefault(cc, []).append(contact["phone_e164"])

            for cc, phones in sorted(country_buckets.items(), key=lambda x: len(x[1]), reverse=True):
                segments.append({
                    "name": f"Country: {cc}",
                    "criteria": f"country_{cc}",
                    "contact_count": len(phones),
                })

        # Store segments in broadcast job
        broadcast_repo.update_segments(broadcast_job_id, json.dumps(segments))

    total_in_segments = sum(s["contact_count"] for s in segments)

    return {
        "status": "success",
        "segment_by": segment_by,
        "segment_count": len(segments),
        "total_contacts_in_segments": total_in_segments,
        "segments": segments,
        "message": (
            f"Segmentation complete: {len(segments)} segment(s) created "
            f"with {total_in_segments} total contacts."
        ),
    }


@tool
def create_audience_segments(
    user_id: str, broadcast_job_id: str, segment_by: str = "lifecycle"
) -> str:
    """
    Create audience segments based on analysis.

    Segmentation options:
    - "all": Single segment with all valid contacts
    - "lifecycle": Segment by lifecycle stage (New, Engaged, Active, At-Risk, Dormant)
    - "country": Segment by country code

    Churned contacts (90+ days inactive) are automatically excluded.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID
        segment_by: Segmentation strategy ("all", "lifecycle", "country")

    Returns:
        JSON string with created segments and contact counts
    """
    logger.info("[SEGMENTATION] create_audience_segments for job: %s, by: %s", broadcast_job_id, segment_by)
    try:
        future = _executor.submit(
            _run_create_segments_sync, user_id, broadcast_job_id, segment_by
        )
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[SEGMENTATION] create_audience_segments error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 6: GET SEGMENTATION SUMMARY
# ============================================

def _run_get_segmentation_summary_sync(user_id: str, broadcast_job_id: str):
    """Get overall segmentation summary for a broadcast job."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        job = repo.get_by_id(broadcast_job_id)

    if not job:
        return {"status": "failed", "message": "Broadcast job not found"}

    segments = []
    if job.get("segments_data"):
        try:
            segments = json.loads(job["segments_data"])
        except (json.JSONDecodeError, TypeError):
            pass

    total_in_segments = sum(s.get("contact_count", 0) for s in segments)

    return {
        "status": "success",
        "broadcast_job_id": broadcast_job_id,
        "segment_count": len(segments),
        "total_contacts_in_segments": total_in_segments,
        "valid_contacts": job.get("valid_contacts", 0),
        "segments": segments,
        "message": (
            f"Segmentation summary: {len(segments)} segment(s), "
            f"{total_in_segments} contacts ready for content creation."
        ),
    }


@tool
def get_segmentation_summary(user_id: str, broadcast_job_id: str) -> str:
    """
    Get the overall segmentation summary for a broadcast job.

    Returns segment counts, contact distribution, and readiness for next phase.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with segmentation summary
    """
    logger.info("[SEGMENTATION] get_segmentation_summary for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_get_segmentation_summary_sync, user_id, broadcast_job_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[SEGMENTATION] get_segmentation_summary error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOLS EXPORT
# ============================================

BACKEND_TOOLS = [
    classify_lifecycle_stages,
    detect_24hr_windows,
    cluster_by_timezone,
    check_frequency_caps,
    create_audience_segments,
    get_segmentation_summary,
]

BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
