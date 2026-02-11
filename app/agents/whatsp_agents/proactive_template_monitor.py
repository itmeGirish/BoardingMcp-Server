"""
Proactive Template Approval Monitor.

A background agent that monitors WhatsApp template approval status using
APScheduler. Once started for a given template, it polls the WhatsApp API
via the Direct API MCP server every 15 seconds and updates the local
database when the status changes. Polling stops automatically when the
template reaches a final status (APPROVED, REJECTED, PAUSED, DISABLED).

Usage:
    from app.agents.whatsp_agents.proactive_template_monitor import (
        start_template_monitoring,
        stop_template_monitoring,
    )

    # Fire-and-forget: starts background polling
    start_template_monitoring(user_id="u123", template_id="t456")

    # With optional callback
    start_template_monitoring(
        user_id="u123",
        template_id="t456",
        callback=my_async_or_sync_callback,
    )

    # Manual stop (e.g., user cancels)
    stop_template_monitoring(template_id="t456")
"""

from __future__ import annotations

import asyncio
import json
import threading
import concurrent.futures
from datetime import datetime
from typing import Callable, Dict, Optional

import nest_asyncio
from pydantic import BaseModel, Field
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import logger

# Allow nested event-loop usage (required when called from sync contexts)
nest_asyncio.apply()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLL_INTERVAL_SECONDS: int = 15
MAX_CONSECUTIVE_ERRORS: int = 10
FINAL_STATUSES = frozenset({"APPROVED", "REJECTED", "PAUSED", "DISABLED"})
_LOG_PREFIX = "[TemplateMonitor]"

# ---------------------------------------------------------------------------
# Pydantic schema -- structured result for each poll cycle
# ---------------------------------------------------------------------------


class TemplateStatusResult(BaseModel):
    """Structured output representing a single poll result."""

    template_id: str = Field(..., description="WhatsApp template ID being monitored")
    status: str = Field(..., description="Current approval status from WhatsApp API")
    is_final: bool = Field(
        default=False,
        description="True when status is a terminal state (APPROVED/REJECTED/PAUSED/DISABLED)",
    )
    message: str = Field(
        default="",
        description="Human-readable summary of the status check",
    )


# ---------------------------------------------------------------------------
# MCP helper -- mirrors the pattern in tools/content_creation.py
# ---------------------------------------------------------------------------

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


def _call_direct_api_mcp(tool_name: str, params: dict) -> dict:
    """Call a Direct API MCP tool (port 9002) synchronously."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    from app.utils.whsp_onboarding_agent import (
        parse_mcp_result_with_debug as parse_mcp_result,
    )

    async def _call():
        client = MultiServerMCPClient(
            {
                "DirectApiMCP": {
                    "url": "http://127.0.0.1:9002/mcp",
                    "transport": "streamable-http",
                }
            }
        )
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


# ---------------------------------------------------------------------------
# Core polling logic
# ---------------------------------------------------------------------------


def _poll_template_status(user_id: str, template_id: str) -> TemplateStatusResult:
    """
    Fetch template status from the WhatsApp API via MCP and return a
    structured ``TemplateStatusResult``.

    This function is intentionally synchronous so it can be dispatched
    easily inside an APScheduler job running on the default executor.
    """
    try:
        mcp_result = _call_direct_api_mcp(
            "get_template_by_id",
            {"user_id": user_id, "template_id": template_id},
        )
    except Exception as exc:
        logger.error(
            "%s MCP call failed for template %s: %s",
            _LOG_PREFIX, template_id, exc, exc_info=True,
        )
        return TemplateStatusResult(
            template_id=template_id,
            status="ERROR",
            is_final=False,
            message=f"MCP call failed: {exc}",
        )

    api_status = "UNKNOWN"
    rejected_reason: Optional[str] = None

    if isinstance(mcp_result, dict) and mcp_result.get("success"):
        api_data = mcp_result.get("data", {})
        if isinstance(api_data, dict):
            api_status = api_data.get("status", "UNKNOWN").upper()
            rejected_reason = api_data.get(
                "rejected_reason",
                api_data.get("quality_score", {}).get("reasons") if isinstance(api_data.get("quality_score"), dict) else None,
            )

    is_final = api_status in FINAL_STATUSES

    # Build human-readable message
    msg = f"Template {template_id}: status is {api_status}."
    if rejected_reason and api_status == "REJECTED":
        msg += f" Rejection reason: {rejected_reason}"
    if is_final:
        msg += " (final -- monitoring will stop)"

    return TemplateStatusResult(
        template_id=template_id,
        status=api_status,
        is_final=is_final,
        message=msg,
    )


def _sync_status_to_db(
    template_id: str,
    api_status: str,
    rejected_reason: Optional[str] = None,
) -> bool:
    """
    Persist the latest status to the local PostgreSQL database.

    Returns True on success, False on failure.
    """
    try:
        from app.database.postgresql.postgresql_connection import get_session
        from app.database.postgresql.postgresql_repositories.template_creation_repo import (
            TemplateCreationRepository,
        )

        with get_session() as session:
            repo = TemplateCreationRepository(session=session)
            updated = repo.update_status(
                template_id,
                api_status,
                rejected_reason=str(rejected_reason) if rejected_reason else None,
            )
        if updated:
            logger.info(
                "%s DB status synced for template %s -> %s",
                _LOG_PREFIX, template_id, api_status,
            )
        else:
            logger.warning(
                "%s Template %s not found in DB during status sync",
                _LOG_PREFIX, template_id,
            )
        return bool(updated)
    except Exception as exc:
        logger.error(
            "%s DB sync failed for template %s: %s",
            _LOG_PREFIX, template_id, exc, exc_info=True,
        )
        return False


# ---------------------------------------------------------------------------
# Monitor registry -- tracks active scheduler jobs
# ---------------------------------------------------------------------------


class _MonitorEntry:
    """Internal bookkeeping for a single monitored template."""

    __slots__ = (
        "user_id",
        "template_id",
        "callback",
        "consecutive_errors",
        "last_known_status",
        "started_at",
    )

    def __init__(
        self,
        user_id: str,
        template_id: str,
        callback: Optional[Callable] = None,
    ):
        self.user_id = user_id
        self.template_id = template_id
        self.callback = callback
        self.consecutive_errors: int = 0
        self.last_known_status: Optional[str] = None
        self.started_at: datetime = datetime.utcnow()


# Module-level state -- one scheduler shared across all monitors
_scheduler: Optional[AsyncIOScheduler] = None
_scheduler_lock = threading.Lock()
_active_monitors: Dict[str, _MonitorEntry] = {}


def _get_scheduler() -> AsyncIOScheduler:
    """Lazily create and start the shared AsyncIOScheduler."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler is None or not _scheduler.running:
            _scheduler = AsyncIOScheduler()
            _scheduler.start()
            logger.info("%s Shared APScheduler started", _LOG_PREFIX)
    return _scheduler


def _job_id_for(template_id: str) -> str:
    """Deterministic APScheduler job ID for a given template."""
    return f"template_monitor_{template_id}"


# ---------------------------------------------------------------------------
# Scheduled job -- executed by APScheduler on each tick
# ---------------------------------------------------------------------------


async def _monitor_tick(template_id: str) -> None:
    """
    Single polling tick executed by APScheduler.

    Runs the poll in a thread executor (MCP call is sync), then processes
    the result on the async side.
    """
    entry = _active_monitors.get(template_id)
    if entry is None:
        # Entry removed while job was still scheduled; clean up silently.
        logger.debug("%s Tick for unknown template %s -- skipping", _LOG_PREFIX, template_id)
        return

    logger.info(
        "%s Polling template %s (user=%s, errors=%d, last=%s)",
        _LOG_PREFIX,
        template_id,
        entry.user_id,
        entry.consecutive_errors,
        entry.last_known_status,
    )

    # Run the synchronous MCP poll in the thread-pool executor
    loop = asyncio.get_event_loop()
    try:
        result: TemplateStatusResult = await loop.run_in_executor(
            _executor,
            _poll_template_status,
            entry.user_id,
            template_id,
        )
    except Exception as exc:
        logger.error(
            "%s Executor error for template %s: %s",
            _LOG_PREFIX, template_id, exc, exc_info=True,
        )
        entry.consecutive_errors += 1
        if entry.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logger.error(
                "%s Max consecutive errors (%d) reached for template %s -- stopping monitor",
                _LOG_PREFIX, MAX_CONSECUTIVE_ERRORS, template_id,
            )
            stop_template_monitoring(template_id)
        return

    # Handle transient MCP errors
    if result.status == "ERROR":
        entry.consecutive_errors += 1
        logger.warning(
            "%s Poll error (%d/%d) for template %s: %s",
            _LOG_PREFIX,
            entry.consecutive_errors,
            MAX_CONSECUTIVE_ERRORS,
            template_id,
            result.message,
        )
        if entry.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            logger.error(
                "%s Max consecutive errors (%d) reached for template %s -- stopping monitor",
                _LOG_PREFIX, MAX_CONSECUTIVE_ERRORS, template_id,
            )
            stop_template_monitoring(template_id)
        return

    # Reset error counter on successful poll
    entry.consecutive_errors = 0

    # Detect status change
    status_changed = result.status != entry.last_known_status
    if status_changed:
        logger.info(
            "%s Status change detected for template %s: %s -> %s",
            _LOG_PREFIX,
            template_id,
            entry.last_known_status or "N/A",
            result.status,
        )
        entry.last_known_status = result.status

        # Persist to database
        await loop.run_in_executor(
            _executor,
            _sync_status_to_db,
            template_id,
            result.status,
            None,  # rejected_reason extracted inside _poll but we re-derive below
        )

        # If REJECTED, do a targeted DB update with the reason from the message
        if result.status == "REJECTED" and "Rejection reason:" in result.message:
            reason = result.message.split("Rejection reason:")[-1].strip()
            await loop.run_in_executor(
                _executor,
                _sync_status_to_db,
                template_id,
                result.status,
                reason,
            )

        # Fire user callback if provided
        if entry.callback is not None:
            try:
                cb_result = entry.callback(result)
                # Support async callbacks transparently
                if asyncio.iscoroutine(cb_result):
                    await cb_result
            except Exception as cb_exc:
                logger.error(
                    "%s Callback error for template %s: %s",
                    _LOG_PREFIX, template_id, cb_exc, exc_info=True,
                )
    else:
        logger.debug(
            "%s No change for template %s (still %s)",
            _LOG_PREFIX, template_id, result.status,
        )

    # Stop monitoring if we reached a terminal status
    if result.is_final:
        logger.info(
            "%s Final status %s reached for template %s -- stopping monitor",
            _LOG_PREFIX, result.status, template_id,
        )
        stop_template_monitoring(template_id)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def start_template_monitoring(
    user_id: str,
    template_id: str,
    callback: Optional[Callable] = None,
    poll_interval: int = POLL_INTERVAL_SECONDS,
) -> bool:
    """
    Start background monitoring for a WhatsApp template.

    Registers an APScheduler job that polls ``get_template_by_id`` via MCP
    at the specified interval (default 15 s). When the status changes the
    local DB is updated and the optional *callback* is invoked with a
    ``TemplateStatusResult``.

    Monitoring stops automatically when a final status is reached or after
    ``MAX_CONSECUTIVE_ERRORS`` consecutive MCP failures.

    Args:
        user_id:       User ID that owns the template.
        template_id:   WhatsApp template ID to monitor.
        callback:      Optional callable(TemplateStatusResult) -- may be
                       sync or async.
        poll_interval: Seconds between polls (default 15).

    Returns:
        True if monitoring was started, False if already active for this
        template.
    """
    job_id = _job_id_for(template_id)

    if template_id in _active_monitors:
        logger.warning(
            "%s Monitoring already active for template %s -- ignoring duplicate start",
            _LOG_PREFIX, template_id,
        )
        return False

    # Register the monitor entry
    entry = _MonitorEntry(
        user_id=user_id,
        template_id=template_id,
        callback=callback,
    )
    _active_monitors[template_id] = entry

    # Schedule the recurring job
    scheduler = _get_scheduler()
    scheduler.add_job(
        _monitor_tick,
        trigger=IntervalTrigger(seconds=poll_interval),
        args=[template_id],
        id=job_id,
        name=f"Monitor template {template_id}",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=poll_interval * 2,
    )

    logger.info(
        "%s Started monitoring template %s for user %s (interval=%ds)",
        _LOG_PREFIX, template_id, user_id, poll_interval,
    )
    return True


def stop_template_monitoring(template_id: str) -> bool:
    """
    Stop background monitoring for a WhatsApp template.

    Removes the APScheduler job and cleans up internal state.

    Args:
        template_id: WhatsApp template ID to stop monitoring.

    Returns:
        True if monitoring was stopped, False if no active monitor found.
    """
    job_id = _job_id_for(template_id)
    entry = _active_monitors.pop(template_id, None)

    if entry is None:
        logger.debug(
            "%s No active monitor for template %s -- nothing to stop",
            _LOG_PREFIX, template_id,
        )
        return False

    # Remove the APScheduler job (safe even if already removed)
    scheduler = _get_scheduler()
    try:
        scheduler.remove_job(job_id)
    except Exception:
        # Job may have already been removed by a concurrent stop
        pass

    elapsed = (datetime.utcnow() - entry.started_at).total_seconds()
    logger.info(
        "%s Stopped monitoring template %s (ran for %.1fs, last_status=%s)",
        _LOG_PREFIX, template_id, elapsed, entry.last_known_status,
    )
    return True


def get_monitored_templates() -> Dict[str, dict]:
    """
    Return a snapshot of all actively monitored templates.

    Useful for debugging and admin dashboards.

    Returns:
        Dict mapping template_id to a summary dict.
    """
    return {
        tid: {
            "user_id": entry.user_id,
            "last_known_status": entry.last_known_status,
            "consecutive_errors": entry.consecutive_errors,
            "started_at": entry.started_at.isoformat(),
        }
        for tid, entry in _active_monitors.items()
    }


def stop_all_monitors() -> int:
    """
    Stop all active template monitors.

    Intended for graceful application shutdown.

    Returns:
        Number of monitors stopped.
    """
    template_ids = list(_active_monitors.keys())
    count = 0
    for tid in template_ids:
        if stop_template_monitoring(tid):
            count += 1

    # Shut down the scheduler itself if nothing is left
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("%s Shared APScheduler shut down", _LOG_PREFIX)
            _scheduler = None

    logger.info("%s All monitors stopped (count=%d)", _LOG_PREFIX, count)
    return count
