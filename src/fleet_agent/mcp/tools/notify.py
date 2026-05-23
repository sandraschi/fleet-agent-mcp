"""Email notification tool + background scheduler for recurring tasks."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
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
            now = datetime.now(UTC)
            tasks = store.todo_list(status="pending")
            for t in tasks:
                rec = t.get("recurrence")
                if not rec:
                    continue
                updated = t.get("updated_at") or t.get("created_at", "")
                should_fire = False

                # Time-of-day recurrence: "09:00", "14:30" (fires daily at that time)
                if ":" in rec and len(rec) <= 5:
                    try:
                        h, m = rec.split(":")
                        target_min = int(h) * 60 + int(m)
                        current_min = now.hour * 60 + now.minute
                        last_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        # Fire if time matches and hasn't fired today
                        if current_min >= target_min and last_dt.date() < now.date():
                            should_fire = True
                    except ValueError:
                        pass

                # Interval recurrence: "3600" (seconds), "1h", "30m"
                elif rec.isdigit():
                    interval = int(rec)
                    last_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if (now - last_dt).total_seconds() >= interval:
                        should_fire = True
                elif rec.endswith("h"):
                    interval = int(rec[:-1]) * 3600
                    last_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if (now - last_dt).total_seconds() >= interval:
                        should_fire = True
                elif rec.endswith("m"):
                    interval = int(rec[:-1]) * 60
                    last_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if (now - last_dt).total_seconds() >= interval:
                        should_fire = True

                if should_fire:
                    logs.add("info", f"Firing: {t['task'][:60]}", "heartbeat")

                    # Try to execute the task via fleet tools
                    task_lower = t["task"].lower()
                    try:
                        if "arxiv" in task_lower or "paper" in task_lower:
                            from ...llm_client import chat_completion
                            query = await chat_completion([
                                {"role": "system", "content": "Extract a short arxiv search query from this task. Reply with ONLY the query, no quotes."},
                                {"role": "user", "content": t["task"]},
                            ])
                            logs.add("info", f"  Searching arxiv for: {query}", "heartbeat")
                            import httpx
                            headers = {"Accept": "application/json, text/event-stream"}
                            r = httpx.post(
                                "http://127.0.0.1:10996/mcp/",
                                json={"jsonrpc":"2.0","method":"tools/call","params":{"name":"fleet_call_tool","arguments":{"server":"arxiv","tool":"search_papers","arguments":{"query":query,"limit":5}}},"id":1},
                                headers=headers, timeout=120,
                            )
                            logs.add("info", f"  Arxiv result: {r.text[:200]}", "heartbeat")
                        elif "browser" in task_lower or "chrome" in task_lower or "website" in task_lower or "tab" in task_lower:
                            logs.add("info", "  Browser task detected — pywinauto or browser-mcp needed", "heartbeat")
                    except Exception as ex:
                        logs.add("error", f"  Task executor: {ex}", "heartbeat")

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
