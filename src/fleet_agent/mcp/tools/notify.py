"""Email notification tool + background scheduler for recurring tasks."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.notify")

_SCHEDULER_TASK: asyncio.Task | None = None


async def _send_email_smtp(
    to,
    subject,
    body,
    smtp_host,
    smtp_port,
    smtp_user,
    smtp_pass,
    attachment_paths: list[str] | None = None,
):
    return await send_email_message(
        to=to,
        subject=subject,
        body=body,
        attachment_paths=attachment_paths,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_pass=smtp_pass,
    )


async def send_email_message(
    *,
    to: str,
    subject: str,
    body: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    attachment_paths: list[str] | None = None,
) -> dict[str, Any]:
    import smtplib
    from email import encoders
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        files = [Path(p) for p in (attachment_paths or []) if Path(p).is_file()]
        if files:
            msg = MIMEMultipart()
            msg.attach(MIMEText(body, "plain", "utf-8"))
            for path in files:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(path.read_bytes())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{path.name}"')
                msg.attach(part)
        else:
            msg = MIMEText(body, "plain", "utf-8")

        msg["Subject"] = subject
        msg["To"] = to
        msg["From"] = smtp_user
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
            attach_note = f" (+{len(files)} attachment(s))" if files else ""
            return {"success": True, "message": f"Email sent to {to}{attach_note}"}
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
    from ...coworker.recurrence import recurrence_due
    from ...coworker.tasks import coworker_sends_own_email, execute_recurring_task, touch_recurring_task
    from ...log_store import get_log_store
    from ...settings_store import get_settings_store

    logs = get_log_store()
    logs.add("info", "Heartbeat scheduler started (60s interval)", "system")
    while True:
        try:
            from ...engine.sqlite_store import get_store
            store = get_store()
            settings = get_settings_store()
            tz_name = settings.get("coworker_timezone", "Europe/Vienna")
            now = datetime.now(UTC)
            tasks = store.todo_list(status="pending")

            for t in tasks:
                rec = t.get("recurrence")
                if not rec:
                    continue
                updated = t.get("updated_at") or t.get("created_at", "")
                if not recurrence_due(rec, updated, tz_name=tz_name):
                    continue

                logs.add("info", f"Firing: {t['task'][:60]}", "heartbeat")
                try:
                    result = await execute_recurring_task(t)
                    logs.add(
                        "info",
                        f"  {result.get('handler', '?')}: {result.get('message', '')[:120]}",
                        "heartbeat",
                    )
                except Exception as ex:
                    logs.add("error", f"  Task executor: {ex}", "heartbeat")
                    result = {"success": False}

                if not coworker_sends_own_email(result):
                    to = settings.get("heartbeat_email", "")
                    if to and settings.get("smtp_host") and settings.get("smtp_user"):
                        await _send_email_smtp(
                            to=to,
                            subject=f"Fritz Heartbeat - {now.strftime('%Y-%m-%d %H:%M')}",
                            body=f"Fritz alive. Task: {t['task']}\n\n{result.get('message', '')}",
                            smtp_host=settings.get("smtp_host", ""),
                            smtp_port=int(settings.get("smtp_port", 587)),
                            smtp_user=settings.get("smtp_user", ""),
                            smtp_pass=settings.get("smtp_pass", ""),
                        )

                touch_recurring_task(store, t)

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


def start_scheduler() -> None:
    """Start the scheduler and track it in the module variable.

    Called from server.main() on boot to auto-start the heartbeat loop.
    """
    global _SCHEDULER_TASK
    if _SCHEDULER_TASK is None or _SCHEDULER_TASK.done():
        _SCHEDULER_TASK = asyncio.create_task(_scheduler_loop())


@mcp.tool(version="0.1.0")
async def cron_status() -> dict[str, Any]:
    """Check if the heartbeat scheduler is running.

    ## Return Format
    {"success": bool, "running": bool, "message": str}
    """
    global _SCHEDULER_TASK
    running = _SCHEDULER_TASK is not None and not _SCHEDULER_TASK.done()
    return {"success": True, "running": running, "message": "running" if running else "stopped"}
