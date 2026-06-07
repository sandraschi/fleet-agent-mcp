"""Cursor spend watch — guardrail poll via cursor-mcp."""

from __future__ import annotations

from typing import Any

from .common import (
    deliver_report,
    fleet_call,
    log_project_note,
    now_label,
    parse_fleet_payload,
    save_artifact,
)

CURSOR_SPEND_PROJECT = "cursor-spend-watch"


def format_cursor_spend_report(*, pulse_date: str, payload: dict[str, Any]) -> str:
    alert = payload.get("alert") or {}
    metrics = alert.get("metrics") or {}
    partial = payload.get("partial_errors") or {}
    reasons = alert.get("reasons") or []

    lines = [
        f"# Cursor Spend Watch — {pulse_date}",
        "",
        f"**Alert level:** {alert.get('level', 'unknown').upper()}",
        "",
        "## Metrics",
        "",
        f"- Hourly spend (est.): ${metrics.get('hourly_spend_usd', '?')}",
        f"- On-demand (cycle): ${metrics.get('on_demand_spend_usd', '?')}",
        f"- Overall (cycle): ${metrics.get('overall_spend_usd', '?')}",
        f"- Running cloud agents: {metrics.get('running_cloud_agents', '?')}",
        f"- Monthly limit ($): {metrics.get('monthly_limit_dollars', 'n/a')}",
        "",
        "## Reasons",
        "",
    ]
    for reason in reasons:
        lines.append(f"- {reason}")

    errors = {k: v for k, v in partial.items() if v}
    if errors:
        lines.extend(["", "## Partial errors", ""])
        for key, err in errors.items():
            lines.append(f"- **{key}:** {err}")
        lines.append("")
        lines.append("_Add CURSOR_ADMIN_API_KEY on cursor-mcp for full spend/events API._")

    lines.extend([
        "",
        "## Dashboard",
        "",
        "https://cursor.com/dashboard",
        "",
    ])
    return "\n".join(lines)


async def run_cursor_spend_watch(*, deliver: bool = True) -> dict[str, Any]:
    from ..settings_store import get_settings_store

    settings = get_settings_store()
    tz_name = settings.get("coworker_timezone", "Europe/Vienna")
    pulse_date = now_label(tz_name)

    raw = await fleet_call(
        "cursor",
        "cursor_usage",
        {"operation": "alert_check", "hours": 1},
    )
    payload = parse_fleet_payload(raw)
    if not isinstance(payload, dict):
        payload = {
            "success": False,
            "error": str(payload),
            "alert": {"level": "warn", "reasons": ["cursor-mcp unreachable"]},
        }

    alert_level = (payload.get("alert") or {}).get("level", "warn")
    report = format_cursor_spend_report(pulse_date=pulse_date, payload=payload)
    artifact_path = save_artifact("cursor-spend-watch", report, tz_name)
    log_project_note(CURSOR_SPEND_PROJECT, pulse_date, report, tags=["coworker", "cursor", "spend"])

    should_deliver = deliver and alert_level in {"warn", "critical"}
    subject = f"Cursor Spend {alert_level.upper()} — {pulse_date.split()[0]}"
    delivery = {"email": await deliver_report(report, subject, deliver=should_deliver)}

    return {
        "success": payload.get("success", True),
        "message": f"Cursor spend watch: {alert_level}",
        "alert_level": alert_level,
        "report": report,
        "artifact_path": artifact_path,
        "delivery": delivery,
        "payload": payload,
    }
