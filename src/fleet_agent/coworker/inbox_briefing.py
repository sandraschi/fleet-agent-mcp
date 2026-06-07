"""Inbox Briefing — unread email digest via email-mcp."""

from __future__ import annotations

from typing import Any

from ..settings_store import get_settings_store
from .common import (
    deliver_report,
    fleet_call,
    log_project_note,
    now_label,
    parse_fleet_payload,
    save_artifact,
)

INBOX_PROJECT = "inbox-briefing"


def format_inbox_briefing(
    *,
    pulse_date: str,
    inbox: dict[str, Any],
    email_status: dict[str, Any] | None,
) -> str:
    lines = [
        f"# Inbox Briefing — {pulse_date}",
        "",
        "## Summary",
        "",
    ]
    if not inbox.get("success"):
        err = inbox.get("error") or inbox.get("message") or "email-mcp unreachable"
        lines.append(f"- **Status:** failed — {err}")
        lines.append("")
        lines.append(
            "Start email-mcp on port 10813 or check "
            "`/api/settings` → `inbox_briefing_service`."
        )
        return "\n".join(lines)

    emails = inbox.get("emails") or []
    lines.append(f"- **Unread fetched:** {inbox.get('count', len(emails))}")
    lines.append(f"- **Service:** {inbox.get('service', '?')} / {inbox.get('folder', 'INBOX')}")
    if email_status and email_status.get("success"):
        services = email_status.get("services") or email_status.get("data") or email_status
        svc_label = services if isinstance(services, str) else len(services)
        lines.append(f"- **Configured services:** {svc_label}")
    lines.extend(["", "## Messages", ""])

    if not emails:
        lines.append("_No unread messages — inbox zero._")
    else:
        for i, msg in enumerate(emails[:20], 1):
            subject = msg.get("subject") or "(no subject)"
            sender = msg.get("from") or msg.get("sender") or "?"
            date = msg.get("date") or "?"
            lines.append(f"{i}. **{subject}**")
            lines.append(f"   - From: {sender}")
            lines.append(f"   - Date: {date}")
        if len(emails) > 20:
            lines.append(f"\n_…and {len(emails) - 20} more._")

    lines.extend([
        "",
        "## Suggested actions",
        "",
        "1. Reply to urgent senders first (human gate — Fritz does not send without approval).",
        "2. Move newsletters to archive if `mailing_list_latest` covers them.",
        "3. `pulse_add` follow-ups for anything needing work this week.",
        "",
    ])
    return "\n".join(lines)


async def run_inbox_briefing(*, deliver: bool = True) -> dict[str, Any]:
    settings = get_settings_store()
    tz_name = settings.get("coworker_timezone", "Europe/Vienna")
    pulse_date = now_label(tz_name)

    service = settings.get("inbox_briefing_service", "default")
    limit = int(settings.get("inbox_briefing_limit", 15))

    inbox_raw = await fleet_call(
        "email",
        "check_inbox",
        {"service": service, "unread_only": True, "limit": limit},
    )
    inbox = parse_fleet_payload(inbox_raw)
    if isinstance(inbox, dict) and "success" not in inbox and inbox_raw.get("success"):
        inbox = {"success": True, **inbox}

    status_raw = await fleet_call("email", "email_status", {})
    email_status = parse_fleet_payload(status_raw)
    if not isinstance(email_status, dict):
        email_status = None

    report = format_inbox_briefing(
        pulse_date=pulse_date,
        inbox=inbox if isinstance(inbox, dict) else {"success": False, "error": str(inbox)},
        email_status=email_status if isinstance(email_status, dict) else None,
    )

    artifact_path = save_artifact("inbox-briefing", report, tz_name)
    log_project_note(INBOX_PROJECT, pulse_date, report, tags=["coworker", "office", "email"])

    subject = f"Inbox Briefing — {pulse_date.split()[0]}"
    delivery = {"email": await deliver_report(report, subject, deliver=deliver)}

    count = inbox.get("count", 0) if isinstance(inbox, dict) else 0
    ok = isinstance(inbox, dict) and inbox.get("success", False)

    return {
        "success": ok,
        "message": (
            f"Inbox Briefing: {count} unread messages"
            if ok
            else "Inbox Briefing failed (is email-mcp up?)"
        ),
        "report": report,
        "artifact_path": artifact_path,
        "delivery": delivery,
        "stats": {"unread_count": count},
    }
