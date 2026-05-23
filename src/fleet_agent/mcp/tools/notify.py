"""Email notification tool + background scheduler for recurring tasks."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import Field

from ...log_store import get_log_store
from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.notify")

_SCHEDULER_TASK: asyncio.Task | None = None


async def _send_email_smtp(
    to: str, subject: str, body: str,
    smtp_host: str, smtp_port: int, smtp_user: str, smtp_pass: str,
) -> dict:
    """Send email via SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["To"] = to
        msg["From"] = smtp_user
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
            return {"success": True, "message": f"Email sent to {to}"}
    except Exception as e:
        return {"success": False, "message": f"SMTP failed: {e}"}


@mcp.tool(version="0.1.0")
async def notify_email(
    to: Annotated[str, Field(description="Recipient email address")],
    subject: Annotated[str, Field(description="Email subject")],
    body: Annotated[str, Field(description="Email body text")],
) -> dict[str, Any]:
    """Send an email via SMTP. Requires SMTP settings configured in /api/settings.

    Settings keys: smtp_host, smtp_port, smtp_user, smtp_pass.

    ## Return Format
    {"success": bool, "message": str}
    """
    from ...settings_store import get_settings_store
    store = get_settings_store()
    host = store.get("smtp_host", "")
    port = store.get("smtp_port", 587)
    user = store.get("smtp_user", "")
    pwd = store.get("smtp_pass", "")
    if not host or not user:
        return {"success": False, "message": "SMTP not configured. Set smtp_host, smtp_user in /api/settings"}
    return await _send_email_smtp(to, subject, body, host, port, user, pwd)


async def _scheduler_loop():
    """Background loop: every 60s check for due recurring tasks and execute them."""
    logs = get_log_store()
    logs.add("info", "Heartbeat scheduler started (60s interval)", "system")

    while True:
        try:
            from ...engine.sqlite_store import get_store
            store = get_store()
            now = datetime.now(UTC)
            tasks = store.todo_list(status="pending")

            for t in tasks:
                rec = t.get("recurrence")
                if not rec:
                    continue
                last = t.get("completed_at") or t.get("created_at", "")
                if last:
                    try:
                        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                        delta = (now - last_dt).total_seconds()
                        # Parse simple recurrence like "3600" (seconds) or "1h", "60m"
                        if rec.isdigit():
                            interval = int(rec)
                        elif rec.endswith("h"):
                            interval = int(rec[:-1]) * 3600
                        elif rec.endswith("m"):
                            interval = int(rec[:-1]) * 60
                        else:
                            continue
                        if delta >= interval:
                            logs.add("info", f"Scheduler firing: {t['task'][:60]}", "heartbeat")
                            # Execute the task — send heartbeat email
                            from ...settings_store import get_settings_store
                            s = get_settings_store()
                            to = s.get("heartbeat_email", "")
                            if to:
                                await _send_email_smtp(
                                    to=to,
                                    subject=f"Fritz Heartbeat — {now.strftime('%Y-%m-%d %H:%M')}",
                                    body=f"Fritz is alive.\nUptime: {time.time():.0f}s\nTask: {t['task']}",
                                    smtp_host=s.get("smtp_host", ""),
                                    smtp_port=s.get("smtp_port", 587),
                                    smtp_user=s.get("smtp_user", ""),
                                    smtp_pass=s.get("smtp_pass", ""),
                                )
                            # Reset the timer by touching updated_at
                            store.todo_complete(t["id"])
                            store.todo_add(t["task"], t.get("group", "self"), t.get("priority", "medium"), recurrence=rec)
                    except Exception as e:
                        logs.add("error", f"Scheduler error: {e}", "heartbeat")

        except Exception as e:
            logs.add("error", f"Scheduler loop error: {e}", "heartbeat")

        await asyncio.sleep(60)


@mcp.tool(version="0.1.0")
async def cron_start() -> dict[str, Any]:
    """Start the background heartbeat scheduler.

    The scheduler runs every 60 seconds, checks for recurring tasks
    (tasks with a `recurrence` field like "3600" or "1h"), and fires
    them when due. Sends heartbeat email if smtp + heartbeat_email
    are configured in /api/settings.

    ## Return Format
    {"success": bool, "message": str}
    """
    global _SCHEDULER_TASK
    if _SCHEDULER_TASK and not _SCHEDULER_TASK.done():
        return {"success": True, "message": "Scheduler already running"}
    _SCHEDULER_TASK = asyncio.create_task(_scheduler_loop())
    return {"success": True, "message": "Heartbeat scheduler started (60s interval)"}


@mcp.tool(version="0.1.0")
async def cron_status() -> dict[str, Any]:
    """Check if the background heartbeat scheduler is running.

    ## Return Format
    {"success": bool, "running": bool, "message": str}
    """
    global _SCHEDULER_TASK
    running = _SCHEDULER_TASK is not None and not _SCHEDULER_TASK.done()
    return {"success": True, "running": running, "message": "Scheduler running" if running else "Scheduler not running"}
