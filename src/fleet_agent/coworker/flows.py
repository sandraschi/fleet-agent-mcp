"""Coworker flow registry — scheduled Viktor-style office + fleet automations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

FlowRunner = Callable[..., Awaitable[dict[str, Any]]]

# recurrence formats: HH:MM | wd:HH:MM | sun:HH:MM | 0 H * * * | 3600 | 30m
COWORKER_FLOWS: dict[str, dict[str, Any]] = {
    "fleet_pulse": {
        "id": "coworker-fleet-pulse",
        "label": "Morning Fleet Pulse",
        "task": "Morning Fleet Pulse — coworker:fleet_pulse",
        "category": "fleet",
        "recurrence_setting": "fleet_pulse_time",
        "default_recurrence": "07:00",
        "enabled_setting": "coworker_fleet_pulse_enabled",
        "default_enabled": True,
        "description": "MCP health, git snapshots, fleet ops digest",
    },
    "inbox_briefing": {
        "id": "coworker-inbox-briefing",
        "label": "Inbox Briefing",
        "task": "Inbox Briefing — coworker:inbox_briefing",
        "category": "office",
        "recurrence_setting": "inbox_briefing_time",
        "default_recurrence": "wd:08:00",
        "enabled_setting": "coworker_inbox_briefing_enabled",
        "default_enabled": True,
        "description": "Unread email triage via email-mcp (weekdays)",
    },
    "day_prep": {
        "id": "coworker-day-prep",
        "label": "Office Day Prep",
        "task": "Office Day Prep — coworker:day_prep",
        "category": "office",
        "recurrence_setting": "day_prep_time",
        "default_recurrence": "wd:08:30",
        "enabled_setting": "coworker_day_prep_enabled",
        "default_enabled": True,
        "description": "Inbox highlights + Fritz pulse tasks + human waiting items",
    },
    "docs_drift": {
        "id": "coworker-docs-drift",
        "label": "Docs Drift Audit",
        "task": "Docs Drift Audit — coworker:docs_drift",
        "category": "office",
        "recurrence_setting": "docs_drift_time",
        "default_recurrence": "sun:10:00",
        "enabled_setting": "coworker_docs_drift_enabled",
        "default_enabled": True,
        "description": "Weekly README/port drift vs fleet docs (Sunday)",
    },
    "weekly_report_pdf": {
        "id": "coworker-weekly-report-pdf",
        "label": "Weekly Report PDF",
        "task": "Weekly Report PDF — coworker:weekly_report_pdf",
        "category": "office",
        "recurrence_setting": "weekly_report_pdf_time",
        "default_recurrence": "fri:17:00",
        "enabled_setting": "coworker_weekly_report_pdf_enabled",
        "default_enabled": True,
        "description": "Fleet Pulse markdown → PDF via libreoffice-mcp → email",
    },
    "board_pack": {
        "id": "coworker-board-pack",
        "label": "Monthly Board Pack",
        "task": "Monthly Board Pack — coworker:board_pack",
        "category": "office",
        "recurrence_setting": "board_pack_time",
        "default_recurrence": "d1:09:00",
        "enabled_setting": "coworker_board_pack_enabled",
        "default_enabled": True,
        "description": "1st of month 09:00 — ODT board pack → PDF → email",
    },
    "artifact_pack": {
        "id": "coworker-artifact-pack",
        "label": "Artifact Pack",
        "task": "Artifact Pack — coworker:artifact_pack",
        "category": "office",
        "recurrence_setting": "artifact_pack_time",
        "default_recurrence": "sun:18:00",
        "enabled_setting": "coworker_artifact_pack_enabled",
        "default_enabled": True,
        "description": "Weekly combined ~/.fleet-agent/artifacts → styled PDF",
    },
    "cursor_spend_watch": {
        "id": "coworker-cursor-spend-watch",
        "label": "Cursor Spend Watch",
        "task": "Cursor Spend Watch — coworker:cursor_spend_watch",
        "category": "fleet",
        "recurrence_setting": "cursor_spend_watch_interval",
        "default_recurrence": "2h",
        "enabled_setting": "coworker_cursor_spend_watch_enabled",
        "default_enabled": True,
        "description": "cursor-mcp alert_check — hourly spend, on-demand, running cloud agents",
    },
    "devices_watch": {
        "id": "coworker-devices-watch",
        "label": "Devices Priority Watch",
        "task": "Devices Priority Watch — coworker:devices_watch",
        "category": "home",
        "recurrence_setting": "devices_watch_interval",
        "default_recurrence": "5m",
        "enabled_setting": "coworker_devices_watch_enabled",
        "default_enabled": True,
        "description": "devices-mcp — kitchen temp, CO, smoke, Ring burglar → Fritz urgent",
    },
    "surveillance_watch": {
        "id": "coworker-surveillance-watch",
        "label": "Fleet Health Surveillance",
        "task": "Fleet Surveillance — coworker:surveillance_watch",
        "category": "system",
        "recurrence_setting": "surveillance_watch_interval",
        "default_recurrence": "15m",
        "enabled_setting": "coworker_surveillance_watch_enabled",
        "default_enabled": True,
        "description": "Check all NSSM services: health, error logs, escalate via email/siren",
    },
    "check_email": {
        "id": "coworker-check-email",
        "label": "Email Security Scan",
        "task": "Email Security Scan — coworker:check_email",
        "category": "system",
        "recurrence_setting": "check_email_interval",
        "default_recurrence": "15m",
        "enabled_setting": "coworker_check_email_enabled",
        "default_enabled": True,
        "description": "Scan inbox for security alerts: password resets, breaches, suspicious logins",
    },
}


def list_flow_catalog() -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "label": spec["label"],
            "category": spec["category"],
            "description": spec["description"],
            "default_recurrence": spec["default_recurrence"],
        }
        for key, spec in COWORKER_FLOWS.items()
    ]


# Future office flows (not wired — ideas for roadmap)
OFFICE_FLOW_IDEAS: list[dict[str, Any]] = [
    {
        "key": "weekly_report_pdf",
        "label": "Weekly Report PDF",
        "apps": ["LibreOffice Writer", "libreoffice-mcp"],
        "needs": "Scheduled fri:17:00 or coworker_weekly_report_pdf",
        "deliverable": "Fleet Pulse markdown → PDF → email",
        "victor_analog": "Stakeholder PDF report",
        "status": "implemented",
    },
    {
        "key": "board_pack_lo",
        "label": "Board Pack (LibreOffice)",
        "apps": ["LibreOffice Writer", "libreoffice-mcp"],
        "needs": "Manual: coworker_board_pack MCP tool",
        "deliverable": "Styled board PDF via fleet-board-pack.odt template",
        "victor_analog": "Board pack assembly",
        "status": "implemented",
    },
    {
        "key": "onenote_daily",
        "label": "OneNote Daily Log",
        "apps": ["OneNote"],
        "needs": "onenote-mcp running (:10907), target section in settings",
        "deliverable": "Append Fleet Pulse + inbox summary to daily page",
        "victor_analog": "Persistent team notebook",
    },
    {
        "key": "notion_standup",
        "label": "Notion Standup Page",
        "apps": ["Notion"],
        "needs": "notion-mcp (:10811), parent page ID",
        "deliverable": "Create/update standup with yesterday done / today / blockers",
        "victor_analog": "Stakeholder reporting to Notion",
    },
    {
        "key": "invoice_inbox",
        "label": "Invoice / PDF Triage",
        "apps": ["Email", "OCR-MCP"],
        "needs": "email-mcp + ocr-mcp attachment pipeline",
        "deliverable": "Flag invoices, extract totals, queue for review",
        "victor_analog": "Document + invoice processing",
    },
    {
        "key": "excel_ops_refresh",
        "label": "Ops Model Refresh",
        "apps": ["LibreOffice Calc", "libreoffice-mcp"],
        "needs": "libreoffice-mcp + CSV from git/fleet; optional libreoffice-ext for live sheet",
        "deliverable": "Refresh ODS from CSV → PDF summary",
        "victor_analog": "Forecast + model refresh",
    },
    {
        "key": "teams_digest",
        "label": "Teams Channel Digest",
        "apps": ["Microsoft Teams"],
        "needs": "M365 MCP channel read + summarize",
        "deliverable": "Overnight mentions, decisions, action items",
        "victor_analog": "Slack morning pulse for Teams shops",
    },
    {
        "key": "planner_sync",
        "label": "Planner ↔ Pulse Sync",
        "apps": ["Microsoft Planner", "Fritz pulse"],
        "needs": "M365 planner tools + plan ID",
        "deliverable": "Bi-directional: Fritz human tasks ↔ Planner buckets",
        "victor_analog": "Linear/Jira ticket creation",
    },
    {
        "key": "word_board_pack",
        "label": "Board Pack Draft",
        "apps": ["LibreOffice Writer"],
        "needs": "libreoffice-mcp template ODT + fleet/git data sources",
        "deliverable": "Monthly update draft as ODT/PDF (FOSS path)",
        "victor_analog": "Board pack assembly",
    },
]
