"""Email notification tool + background scheduler for recurring tasks."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import Field

from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.notify")

_SCHEDULER_TASK: asyncio.Task | None = None


async def _send_email_smtp(to, subject, body, smtp_host, smtp_port, smtp_user, smtp_pass):
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
    """Send an email via SMTP. Requires smtp config in /api/settings.

    Settings keys: smtp_host, smtp_port, smtp_user, smtp_pass.

    ## Return Format
    {"success": bool, "message": str}
    """
    from ...settings_store import get_settings_store
    s = get_settings_store()
    host = s.get("smtp_host", "")
    port = s.get("smtp_port", 587)
    user = s.get("smtp_user", "")
    pwd = s.get("smtp_pass", "")
    if not host or not user:
        return {"success": False, "message": "SMTP not configured. Set smtp_host, smtp_user in /api/settings"}
    return await _send_email_smtp(to, subject, body, host, port, user, pwd)


async def _scheduler_loop():
    from ...log_store import get_log_store
    logs = get_log_store()
    logs.add("info", "Heartbeat scheduler started (60s interval)", "system")
    while True:
        try:
            from ...engine.sqlite_store import get_store
            store = get_store()
            now = datetime.now(timezone.utc)
            tasks = store.todo_list(status="pending")
            for t in tasks:
                rec = t.get("recurrence")
                if not rec:
                    continue
                if rec.isdigit():
                    interval = int(rec)
                elif rec.endswith("h"):
                    interval = int(rec[:-1]) * 3600
                elif rec.endswith("m"):
                    interval = int(rec[:-1]) * 60
                else:
                    continue
                updated = t.get("updated_at") or t.get("created_at", "")
                try:
                    last_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if (now - last_dt).total_seconds() >= interval:
                        logs.add("info", f"Firing: {t['task'][:60]}", "heartbeat")
                        from ...settings_store import get_settings_store
                        s = get_settings_store()
                        to = s.get("heartbeat_email", "")
                        if to:
                            await _send_email_smtp(
                                to=to,
                                subject=f"Fritz Heartbeat - {now.strftime('%Y-%m-%d %H:%M')}",
                                body=f"Fritz alive. Task: {t['task']}",
                                smtp_host=s.get("smtp_host", ""),
                                smtp_port=s.get("smtp_port", 587),
                                smtp_user=s.get("smtp_user", ""),
                                smtp_pass=s.get("smtp_pass", ""),
                            )
                        t["updated_at"] = now.isoformat()
                        store.todo_upsert(t)
                except Exception as e:
                    logs.add("error", f"Scheduler: {e}", "heartbeat")
        except Exception as e:
            logs.add("error", f"Scheduler loop: {e}", "heartbeat")
        await asyncio.sleep(60)


@mcp.tool(version="0.1.0")
async def cron_start() -> dict[str, Any]:
    """Start the background heartbeat scheduler (60s loop).

    Checks recurring tasks and fires them when due. If heartbeat_email
    and SMTP are configured, sends a heartbeat email.

    ## Return Format
    {"success": bool, "message": str}
    """
    global _SCHEDULER_TASK
    if _SCHEDULER_TASK and not _SCHEDULER_TASK.done():
        return {"success": True, "message": "Scheduler already running"}
    _SCHEDULER_TASK = asyncio.create_task(_scheduler_loop())
    return {"success": True, "message": "Heartbeat scheduler started"}


@mcp.tool(version="0.1.0")
async def cron_status() -> dict[str, Any]:
    """Check if the heartbeat scheduler is running.

    ## Return Format
    {"success": bool, "running": bool, "message": str}
    """
    global _SCHEDULER_TASK
    running = _SCHEDULER_TASK is not None and not _SCHEDULER_TASK.done()
    return {"success": True, "running": running, "message": "running" if running else "stopped"}
