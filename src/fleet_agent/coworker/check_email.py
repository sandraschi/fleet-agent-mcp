"""Check Email — security-focused inbox scan via email-mcp.

Scans for security-relevant emails (password resets, service alerts, phishing)
and escalates via Fritz's alert chain. Runs on a tighter interval than the
morning inbox briefing.

Uses email-mcp's prompt injection sanitization (sanitize_text + safety boundary
wrapping) which is already applied at the MCP tool boundary in email-mcp.

Only email metadata (subject, from, date) is extracted for security triage.
Full email bodies are NOT stored or passed to LLM context unless explicitly
requested by the user.
"""

from __future__ import annotations

import logging
from typing import Any

from .common import (
    deliver_report,
    fleet_call,
    log_project_note,
    now_label,
    parse_fleet_payload,
    save_artifact,
)

logger = logging.getLogger("fleet_agent.coworker.check_email")

CHECK_EMAIL_PROJECT = "check-email"

# Security-relevant subject patterns — emails that should alert Fritz
_SECURITY_PATTERNS = (
    "password reset", "password changed", "account access",
    "security alert", "unusual sign-in", "suspicious login",
    "new device", "sign-in from", "2fa", "two-factor",
    "authentication", "security code", "verify your",
    "account recovery", "account locked", "account suspended",
    "breach", "data leak", "your password",
    "billing alert", "payment failed", "subscription canceled",
    "service outage", "incident report", "downtime",
)


def _is_security_relevant(subject: str) -> bool:
    lower = subject.lower()
    return any(p in lower for p in _SECURITY_PATTERNS)


def format_check_report(
    *,
    pulse_date: str,
    inbox: dict[str, Any],
    security_hits: list[dict[str, Any]],
) -> str:
    lines = [
        f"# Email Security Scan — {pulse_date}",
        "",
    ]

    if not inbox.get("success"):
        err = inbox.get("error") or inbox.get("message") or "email-mcp unreachable"
        lines.append(f"- **Status:** failed — {err}")
        lines.append("")
        return "\n".join(lines)

    emails = inbox.get("emails") or []
    lines.append(f"- **Scanned:** {inbox.get('count', len(emails))} unread messages")
    lines.append(f"- **Security hits:** {len(security_hits)}")
    lines.append("")

    if not security_hits:
        lines.append("_No security-relevant emails found._")
        return "\n".join(lines)

    lines.append("## Security Alerts")
    lines.append("")
    for alert in security_hits:
        lines.append(f"- **{alert.get('subject', '(no subject)')}**")
        lines.append(f"  - From: {alert.get('from', '?')}")
        lines.append(f"  - Date: {alert.get('date', '?')}")
        lines.append("")

    lines.extend([
        "## Actions required",
        "",
        "1. Review security alerts above — do not click links in suspicious emails.",
        "2. If password reset was not requested, change credentials immediately.",
        "3. Check services dashboard to verify account status.",
        "",
    ])
    return "\n".join(lines)


async def run_check_email(*, deliver: bool = True) -> dict[str, Any]:
    from ..settings_store import get_settings_store

    settings = get_settings_store()
    tz_name = settings.get("coworker_timezone", "Europe/Vienna")
    pulse_date = now_label(tz_name)

    service = settings.get("check_email_service", "default")
    limit = int(settings.get("check_email_scan_limit", 30))

    raw = await fleet_call(
        "email",
        "check_inbox",
        {"service": service, "unread_only": True, "limit": limit},
    )
    inbox = parse_fleet_payload(raw)
    if not isinstance(inbox, dict):
        inbox = {"success": False, "error": str(inbox)}

    security_hits: list[dict[str, Any]] = []
    for msg in inbox.get("emails") or []:
        subject = msg.get("subject") or msg.get("title") or ""
        if _is_security_relevant(subject):
            security_hits.append({
                "subject": subject,
                "from": msg.get("from") or msg.get("sender") or "?",
                "date": msg.get("date") or "?",
            })

    report = format_check_report(
        pulse_date=pulse_date,
        inbox=inbox,
        security_hits=security_hits,
    )

    artifact_path = save_artifact("check-email", report, tz_name)
    log_project_note(CHECK_EMAIL_PROJECT, pulse_date, report, tags=["coworker", "email", "security"])

    has_hits = bool(security_hits)
    subject = f"Email Security: {len(security_hits)} alerts" if has_hits else "Email Security: clean"
    delivery = {"email": await deliver_report(report, subject, deliver=deliver and has_hits)}

    return {
        "success": inbox.get("success", False),
        "message": f"Email security scan: {len(security_hits)} alerts from {inbox.get('count', 0)} unread",
        "security_hits": len(security_hits),
        "total_scanned": inbox.get("count", 0),
        "report": report,
        "artifact_path": artifact_path,
        "delivery": delivery,
    }
