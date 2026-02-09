"""
Backend tools for Analytics & Optimization Agent.

Uses MCP tools:
- get_waba_analytics (port 9002) - WABA-level analytics
- get_messaging_health_status (port 9002) - Quality & health monitoring

Per doc section 3.7: Post-delivery analytics, quality monitoring,
and AI optimization recommendations.

NOTE: Cost tracking excluded (future enhancement).
"""

import asyncio
import json
import time
import concurrent.futures
import nest_asyncio
from datetime import datetime, timezone, timedelta
from langchain.tools import tool

from ....config import logger

nest_asyncio.apply()
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
# TOOL 1: BROADCAST DELIVERY REPORT
# ============================================

def _run_delivery_report_sync(user_id: str, broadcast_job_id: str):
    """Pull delivery metrics for a broadcast job from DB."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        job = repo.get_by_id(broadcast_job_id)

    if not job:
        return {"status": "failed", "message": "Broadcast job not found"}

    total = job.get("valid_contacts", 0)
    sent = job.get("sent_count", 0)
    delivered = job.get("delivered_count", 0)
    failed = job.get("failed_count", 0)
    pending = job.get("pending_count", 0)

    delivery_rate = round((sent / total * 100), 1) if total > 0 else 0
    read_rate = round((delivered / sent * 100), 1) if sent > 0 else 0

    # Calculate duration
    started = job.get("started_sending_at")
    completed = job.get("completed_at")
    duration = None
    if started and completed:
        try:
            start_dt = datetime.fromisoformat(started) if isinstance(started, str) else started
            end_dt = datetime.fromisoformat(completed) if isinstance(completed, str) else completed
            diff = end_dt - start_dt
            minutes = int(diff.total_seconds() / 60)
            seconds = int(diff.total_seconds() % 60)
            duration = f"{minutes}m {seconds}s"
        except Exception:
            duration = "unknown"

    return {
        "status": "success",
        "broadcast_job_id": broadcast_job_id,
        "phase": job.get("phase"),
        "total_contacts": total,
        "sent": sent,
        "delivered": delivered,
        "failed": failed,
        "pending": pending,
        "delivery_rate": delivery_rate,
        "read_rate": read_rate,
        "template_name": job.get("template_name"),
        "template_category": job.get("template_category"),
        "started_at": started,
        "completed_at": completed,
        "duration": duration,
        "message": (
            f"Broadcast delivery report: {sent}/{total} sent ({delivery_rate}% delivery rate), "
            f"{delivered} delivered ({read_rate}% read rate), "
            f"{failed} failed, {pending} pending."
            + (f" Duration: {duration}." if duration else "")
        ),
    }


@tool
def get_broadcast_delivery_report(user_id: str, broadcast_job_id: str) -> str:
    """
    Get detailed delivery metrics for a specific broadcast job.

    Returns sent, delivered, failed, pending counts with delivery/read rates,
    template info, and broadcast duration.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID

    Returns:
        JSON string with delivery report metrics
    """
    logger.info("[ANALYTICS] get_broadcast_delivery_report for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_delivery_report_sync, user_id, broadcast_job_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[ANALYTICS] get_broadcast_delivery_report error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 2: WABA ANALYTICS REPORT
# ============================================

def _run_waba_analytics_sync(
    user_id: str,
    time_range: str = "last_7_days",
    country_codes: list = None
):
    """Fetch WABA analytics via MCP for a given time range."""
    now = datetime.now(timezone.utc)

    # Calculate time range
    range_config = {
        "today": (now.replace(hour=0, minute=0, second=0, microsecond=0), now, "HOUR"),
        "last_7_days": (now - timedelta(days=7), now, "DAY"),
        "last_30_days": (now - timedelta(days=30), now, "DAY"),
        "last_90_days": (now - timedelta(days=90), now, "MONTH"),
    }

    config = range_config.get(time_range, range_config["last_7_days"])
    start_dt, end_dt, granularity = config
    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())

    params = {
        "fields": "analytics",
        "start": start_ts,
        "end": end_ts,
        "granularity": granularity,
    }
    if country_codes:
        params["country_codes"] = country_codes

    result = _call_direct_api_mcp("get_waba_analytics", params)

    if isinstance(result, dict) and result.get("success"):
        data = result.get("data", {})
        return {
            "status": "success",
            "time_range": time_range,
            "granularity": granularity,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "analytics_data": data,
            "country_filter": country_codes,
            "message": (
                f"WABA analytics for {time_range} ({granularity} granularity). "
                f"Period: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}."
            ),
        }
    else:
        error = result.get("error", "Unknown error") if isinstance(result, dict) else str(result)
        return {
            "status": "failed",
            "message": f"Failed to fetch WABA analytics: {error}",
        }


@tool
def get_waba_analytics_report(
    user_id: str,
    time_range: str = "last_7_days",
    country_codes: list = None
) -> str:
    """
    Fetch WABA-level analytics for message counts, delivery rates, and engagement.

    Uses get_waba_analytics MCP tool for account-wide analytics.

    Args:
        user_id: User's unique identifier
        time_range: One of "today", "last_7_days", "last_30_days", "last_90_days"
        country_codes: Optional list of country codes to filter (e.g., ["IN", "US"])

    Returns:
        JSON string with WABA analytics data for the specified period
    """
    logger.info("[ANALYTICS] get_waba_analytics_report: range=%s", time_range)
    try:
        future = _executor.submit(
            _run_waba_analytics_sync, user_id, time_range, country_codes
        )
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[ANALYTICS] get_waba_analytics_report error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 3: MESSAGING HEALTH REPORT
# ============================================

def _run_health_report_sync(user_id: str):
    """Fetch messaging health status via MCP."""
    result = _call_direct_api_mcp("get_messaging_health_status", {"node_id": user_id})

    if isinstance(result, dict) and (result.get("success") or result.get("data")):
        data = result.get("data", result)
        if isinstance(data, dict):
            quality_score = data.get("quality_score", data.get("quality_rating", "UNKNOWN"))
            tier = data.get("messaging_tier", data.get("tier", "UNKNOWN"))
            status = data.get("account_status", data.get("status", "UNKNOWN"))
        else:
            quality_score = "UNKNOWN"
            tier = "UNKNOWN"
            status = "UNKNOWN"

        # Determine alert level
        quality_upper = str(quality_score).upper()
        if quality_upper in ("RED", "LOW"):
            alert = "CRITICAL - Stop all sending immediately. Review flagged content."
        elif quality_upper in ("YELLOW", "MEDIUM"):
            alert = "WARNING - Reduce send volume. Review recent templates for spam signals."
        else:
            alert = "HEALTHY - No action needed."

        return {
            "status": "success",
            "quality_score": quality_score,
            "messaging_tier": tier,
            "account_status": status,
            "alert": alert,
            "health_data": data,
            "message": (
                f"Messaging health: Quality={quality_score}, "
                f"Tier={tier}, Status={status}. {alert}"
            ),
        }
    else:
        error = result.get("error", "Unknown error") if isinstance(result, dict) else str(result)
        return {
            "status": "failed",
            "message": f"Failed to fetch messaging health: {error}",
        }


@tool
def get_messaging_health_report(user_id: str) -> str:
    """
    Get messaging health status including quality score, tier, and alerts.

    Uses get_messaging_health_status MCP tool. Returns quality score
    (GREEN/YELLOW/RED), messaging tier, account status, and action alerts.

    Args:
        user_id: User's unique identifier

    Returns:
        JSON string with health status, quality score, tier, and alerts
    """
    logger.info("[ANALYTICS] get_messaging_health_report for user: %s", user_id)
    try:
        future = _executor.submit(_run_health_report_sync, user_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[ANALYTICS] get_messaging_health_report error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 4: BROADCAST HISTORY
# ============================================

def _run_broadcast_history_sync(user_id: str):
    """Get list of recent broadcast jobs for the user."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        jobs = repo.get_active_by_user(user_id)

    if not jobs:
        return {
            "status": "success",
            "broadcasts": [],
            "total_broadcasts": 0,
            "message": "No broadcast history found for this user.",
        }

    # Build summary for each broadcast
    summaries = []
    total_sent_all = 0
    total_delivered_all = 0

    for job in jobs[:20]:  # Limit to 20 most recent
        total = job.get("valid_contacts", 0)
        sent = job.get("sent_count", 0)
        delivered = job.get("delivered_count", 0)
        failed = job.get("failed_count", 0)
        rate = round((sent / total * 100), 1) if total > 0 else 0

        total_sent_all += sent
        total_delivered_all += delivered

        summaries.append({
            "broadcast_job_id": job["id"],
            "phase": job.get("phase"),
            "template_name": job.get("template_name"),
            "template_category": job.get("template_category"),
            "total_contacts": total,
            "sent": sent,
            "delivered": delivered,
            "failed": failed,
            "delivery_rate": rate,
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
        })

    avg_rate = round((total_sent_all / sum(j.get("valid_contacts", 0) for j in jobs[:20]) * 100), 1) if sum(j.get("valid_contacts", 0) for j in jobs[:20]) > 0 else 0

    return {
        "status": "success",
        "total_broadcasts": len(jobs),
        "broadcasts": summaries,
        "average_delivery_rate": avg_rate,
        "total_messages_sent": total_sent_all,
        "total_messages_delivered": total_delivered_all,
        "message": (
            f"Broadcast history: {len(jobs)} campaigns. "
            f"Average delivery rate: {avg_rate}%. "
            f"Total sent: {total_sent_all}, delivered: {total_delivered_all}."
        ),
    }


@tool
def get_broadcast_history(user_id: str) -> str:
    """
    Get broadcast campaign history with performance comparison.

    Returns list of recent broadcasts with delivery metrics, allowing
    cross-campaign performance comparison.

    Args:
        user_id: User's unique identifier

    Returns:
        JSON string with broadcast history and aggregate metrics
    """
    logger.info("[ANALYTICS] get_broadcast_history for user: %s", user_id)
    try:
        future = _executor.submit(_run_broadcast_history_sync, user_id)
        result = future.result(timeout=15)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[ANALYTICS] get_broadcast_history error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOL 5: OPTIMIZATION RECOMMENDATIONS
# ============================================

def _run_recommendations_sync(user_id: str, broadcast_job_id: str):
    """Generate optimization recommendations based on metrics + health."""
    from app.database.postgresql.postgresql_connection import get_session
    from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository

    # Get broadcast job metrics
    with get_session() as session:
        repo = BroadcastJobRepository(session=session)
        job = repo.get_by_id(broadcast_job_id)
        all_jobs = repo.get_active_by_user(user_id)

    if not job:
        return {"status": "failed", "message": "Broadcast job not found"}

    total = job.get("valid_contacts", 0)
    sent = job.get("sent_count", 0)
    delivered = job.get("delivered_count", 0)
    failed = job.get("failed_count", 0)
    delivery_rate = round((sent / total * 100), 1) if total > 0 else 0
    read_rate = round((delivered / sent * 100), 1) if sent > 0 else 0

    # Get health status
    health_result = _call_direct_api_mcp("get_messaging_health_status", {"node_id": user_id})
    quality_score = "UNKNOWN"
    tier = "UNKNOWN"
    if isinstance(health_result, dict):
        data = health_result.get("data", health_result)
        if isinstance(data, dict):
            quality_score = str(data.get("quality_score", data.get("quality_rating", "UNKNOWN"))).upper()
            tier = data.get("messaging_tier", data.get("tier", "UNKNOWN"))

    # Generate recommendations
    recommendations = []

    # Delivery rate recommendations
    if delivery_rate >= 90:
        recommendations.append({
            "category": "delivery_rate",
            "severity": "info",
            "title": "Excellent delivery rate",
            "detail": f"Your delivery rate of {delivery_rate}% is excellent. Maintain current approach.",
        })
    elif delivery_rate >= 70:
        recommendations.append({
            "category": "delivery_rate",
            "severity": "warning",
            "title": "Good delivery rate - room for improvement",
            "detail": (
                f"Delivery rate is {delivery_rate}%. Review {failed} failed contacts. "
                "Consider cleaning your contact list and re-validating phone numbers."
            ),
        })
    elif delivery_rate >= 50:
        recommendations.append({
            "category": "delivery_rate",
            "severity": "warning",
            "title": "Delivery rate needs improvement",
            "detail": (
                f"Delivery rate is {delivery_rate}%. Validate phone numbers, "
                "check opt-in status, and remove inactive contacts from your list."
            ),
        })
    else:
        recommendations.append({
            "category": "delivery_rate",
            "severity": "critical",
            "title": "Poor delivery rate - action required",
            "detail": (
                f"Delivery rate is only {delivery_rate}%. Stop sending until list quality improves. "
                "Re-verify all phone numbers, check for invalid/disconnected numbers, "
                "and ensure contacts have opted in."
            ),
        })

    # Quality score recommendations
    if quality_score in ("RED", "LOW"):
        recommendations.append({
            "category": "quality",
            "severity": "critical",
            "title": "Quality score is RED - PAUSE ALL CAMPAIGNS",
            "detail": (
                "Your WhatsApp quality score is RED. Immediately pause all campaigns. "
                "Review and remove flagged templates. Check for high spam report rates. "
                "Contact Meta support if needed."
            ),
        })
    elif quality_score in ("YELLOW", "MEDIUM"):
        recommendations.append({
            "category": "quality",
            "severity": "warning",
            "title": "Quality score declining",
            "detail": (
                "Your quality score is YELLOW. Reduce send volume temporarily. "
                "Review recent templates for spam triggers. "
                "Ensure opt-out instructions are clear in all messages."
            ),
        })

    # Failed messages analysis
    if failed > 0:
        fail_rate = round((failed / total * 100), 1) if total > 0 else 0
        recommendations.append({
            "category": "failures",
            "severity": "warning" if fail_rate < 20 else "critical",
            "title": f"{failed} messages failed ({fail_rate}%)",
            "detail": (
                f"{failed} out of {total} messages failed. "
                "Common causes: invalid numbers (131026), re-engagement required (131047), "
                "rate limits (130429). Review error codes in delivery summary."
            ),
        })

    # Historical comparison
    if len(all_jobs) > 1:
        completed_jobs = [j for j in all_jobs if j.get("phase") == "COMPLETED" and j["id"] != broadcast_job_id]
        if completed_jobs:
            avg_hist_rate = sum(
                (j.get("sent_count", 0) / j.get("valid_contacts", 1)) * 100
                for j in completed_jobs
            ) / len(completed_jobs)
            avg_hist_rate = round(avg_hist_rate, 1)

            if delivery_rate < avg_hist_rate - 10:
                recommendations.append({
                    "category": "trend",
                    "severity": "warning",
                    "title": "Below historical average",
                    "detail": (
                        f"This broadcast ({delivery_rate}%) is below your average ({avg_hist_rate}%). "
                        "Investigate potential issues with contact list quality or template content."
                    ),
                })
            elif delivery_rate > avg_hist_rate + 5:
                recommendations.append({
                    "category": "trend",
                    "severity": "info",
                    "title": "Above historical average",
                    "detail": (
                        f"This broadcast ({delivery_rate}%) is above your average ({avg_hist_rate}%). "
                        "Good job! Consider replicating this approach in future campaigns."
                    ),
                })

    # Tier recommendation
    tier_upper = str(tier).upper().replace(" ", "_")
    if tier_upper in ("UNVERIFIED", "TIER_1") and total > 500:
        recommendations.append({
            "category": "tier",
            "severity": "info",
            "title": "Consider tier upgrade",
            "detail": (
                f"You're on {tier} with {total} contacts. "
                "Maintain high quality scores to qualify for tier upgrade, "
                "allowing higher daily message volumes."
            ),
        })

    return {
        "status": "success",
        "broadcast_job_id": broadcast_job_id,
        "delivery_rate": delivery_rate,
        "read_rate": read_rate,
        "quality_score": quality_score,
        "messaging_tier": tier,
        "recommendations": recommendations,
        "recommendation_count": len(recommendations),
        "message": (
            f"Generated {len(recommendations)} optimization recommendations. "
            f"Delivery rate: {delivery_rate}%, Quality: {quality_score}, Tier: {tier}."
        ),
    }


@tool
def generate_optimization_recommendations(user_id: str, broadcast_job_id: str) -> str:
    """
    Generate AI-powered optimization recommendations for a broadcast.

    Analyzes delivery metrics, messaging health, quality score, and
    historical performance to provide actionable recommendations.

    Args:
        user_id: User's unique identifier
        broadcast_job_id: The broadcast job ID to analyze

    Returns:
        JSON string with categorized recommendations (delivery, quality, failures, trends)
    """
    logger.info("[ANALYTICS] generate_optimization_recommendations for job: %s", broadcast_job_id)
    try:
        future = _executor.submit(_run_recommendations_sync, user_id, broadcast_job_id)
        result = future.result(timeout=30)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error("[ANALYTICS] generate_optimization_recommendations error: %s", e, exc_info=True)
        return json.dumps({"error": str(e), "status": "failed"}, ensure_ascii=False)


# ============================================
# TOOLS EXPORT
# ============================================

BACKEND_TOOLS = [
    get_broadcast_delivery_report,
    get_waba_analytics_report,
    get_messaging_health_report,
    get_broadcast_history,
    generate_optimization_recommendations,
]

BACKEND_TOOL_NAMES = {t.name for t in BACKEND_TOOLS}
