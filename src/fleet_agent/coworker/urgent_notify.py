"""Urgent alerts — email (and optional cursor inbox) when thresholds trip."""

from __future__ import annotations

import logging
from typing import Any

from ..settings_store import get_settings_store
from .common import deliver_report

logger = logging.getLogger("fleet_agent.coworker.urgent_notify")


def urgent_email_enabled() -> bool:
    return bool(get_settings_store().get("urgent_email_enabled", True))


def urgent_threshold() -> float:
    try:
        return float(get_settings_store().get("urgent_email_threshold", 8.0))
    except (TypeError, ValueError):
        return 8.0


def should_send_urgent(
    *,
    urgency: float | None = None,
    force: bool = False,
    critical: bool = False,
) -> bool:
    if force:
        return True
    if critical and urgent_email_enabled():
        return True
    if urgency is not None and urgency >= urgent_threshold() and urgent_email_enabled():
        return True
    return False


async def deliver_urgent_alert(
    *,
    subject: str,
    body: str,
    reason: str,
    urgency: float | None = None,
    force: bool = False,
    critical: bool = False,
    hub_url: str = "",
    post_inbox: bool = True,
) -> dict[str, Any]:
    """Send urgent email when enabled + threshold met; optionally ping cursor inbox."""
    if not should_send_urgent(urgency=urgency, force=force, critical=critical):
        return {
            "success": False,
            "skipped": True,
            "message": f"Urgent alert skipped ({reason}); threshold {urgent_threshold()}",
        }

    link_line = f"\n\nRead on iPad: {hub_url}" if hub_url else ""
    email_body = f"**Urgent — {reason}**\n\n{body}{link_line}"

    email_result = await deliver_report(
        email_body,
        f"🚨 Fritz — {subject}",
        deliver=True,
    )

    inbox_result: dict[str, Any] = {"skipped": True}
    if post_inbox:
        try:
            from .common import fleet_call

            inbox_result = await fleet_call(
                "cursor",
                "cursor_inbox",
                {
                    "operation": "post",
                    "sender": "fritz",
                    "subject": subject,
                    "body": body[:4000] + (f"\n\nHub: {hub_url}" if hub_url else ""),
                    "priority": "high",
                    "tags": ["fritz", "urgent", reason.replace(" ", "-")],
                },
            )
        except Exception as exc:
            logger.info("Cursor inbox urgent post skipped: %s", exc)
            inbox_result = {"success": False, "message": str(exc)}

    return {
        "success": email_result.get("success", False),
        "message": email_result.get("message", inbox_result.get("message", "Notification sent")),
        "next_steps": email_result.get("next_steps", inbox_result.get("next_steps", [])),
        "skipped": False,
        "reason": reason,
        "urgency": urgency,
        "email": email_result,
        "inbox": inbox_result,
    }
