"""Board Pack — ODT template merge → styled PDF → email."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..settings_store import get_settings_store
from .common import (
    deliver_report,
    extract_libreoffice_output,
    fleet_call,
    log_project_note,
    now_label,
    parse_fleet_payload,
)
from .fleet_pulse import _git_snapshot, run_fleet_pulse
from .weekly_report_pdf import _latest_fleet_pulse_artifact

BOARD_PACK_PROJECT = "board-pack"


def _section(md: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}(.*?)(?=\n## |\Z)"
    match = re.search(pattern, md, re.DOTALL | re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def _plain_lines(text: str) -> str:
    rows: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"`([^`]+)`", r"\1", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        if line.startswith("- "):
            rows.append(f"• {line[2:]}")
        else:
            rows.append(line)
    return "\n".join(rows)


async def run_board_pack(
    *, deliver: bool = True, template: str = "fleet-board-pack.odt",
) -> dict[str, Any]:
    """Build board pack from Fleet Pulse data via libreoffice template merge."""
    store_settings = get_settings_store()
    tz_name = store_settings.get("coworker_timezone", "Europe/Vienna")
    pulse_date = now_label(tz_name)
    stamp = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")

    md_path = _latest_fleet_pulse_artifact()
    pulse_result: dict[str, Any] | None = None
    if md_path is None:
        pulse_result = await run_fleet_pulse(deliver=False)
        md_path = Path(pulse_result["artifact_path"])

    report_md = md_path.read_text(encoding="utf-8") if md_path.is_file() else ""

    repos_root = Path(store_settings.get("fleet_repos_root", "D:/Dev/repos"))
    watched = store_settings.get("fleet_pulse_repos") or ["fleet-agent-mcp", "mcp-central-docs"]
    git_rows = _git_snapshot(repos_root, list(watched))

    from ..mcp.tools.fleet_bridge import fleet_discover
    from ..mcp.tools.heartbeat import heartbeat_status

    health = await heartbeat_status()
    discovery = await fleet_discover()
    servers = (discovery.get("data") or {}).get("servers") or []
    online = sum(1 for s in servers if s.get("online"))

    kpi_lines = [
        f"MCP online: {online}/{len(servers)}",
        f"Watched repos: {len(git_rows)}",
        f"Agent: {(health.get('health') or health).get('agent_name', 'Fritz')}",
        f"Pending tasks: {(health.get('health') or health).get('tasks', {}).get('pending', '?')}",
    ]
    for row in git_rows[:5]:
        if row.get("error"):
            kpi_lines.append(f"{row['repo']}: {row['error']}")
        else:
            branch = (row.get("status") or "?").splitlines()[0]
            kpi_lines.append(f"{row['repo']}: {branch}")

    narrative = _plain_lines(_section(report_md, "MCP fleet") or report_md[:2500])
    actions = _plain_lines(_section(report_md, "Action items") or "Review fleet pulse artifact.")

    placeholders = {
        "TITLE": f"Fleet Board Pack — {stamp}",
        "DATE": pulse_date,
        "KPI_TABLE": "\n".join(kpi_lines),
        "NARRATIVE": narrative,
        "ACTION_ITEMS": actions,
    }

    merge_result = await fleet_call(
        "libreoffice",
        "libreoffice",
        {
            "operation": "merge",
            "template": template,
            "placeholders": placeholders,
            "output_format": "pdf",
            "output_stem": f"board-pack-{datetime.now(ZoneInfo(tz_name)).strftime('%Y%m%d')}",
        },
    )

    inner = parse_fleet_payload(merge_result)
    if not merge_result.get("success") or not isinstance(inner, dict):
        return {
            "success": False,
            "message": merge_result.get("message") or "libreoffice merge failed",
            "placeholders": placeholders,
        }

    lo_data = inner.get("data") if isinstance(inner.get("data"), dict) else inner
    if not lo_data.get("success", inner.get("success")):
        return {
            "success": False,
            "message": lo_data.get("error") or inner.get("error") or "Board pack merge failed",
            "placeholders": placeholders,
            "merge": inner,
        }

    pdf_path = extract_libreoffice_output(merge_result) or lo_data.get("output")
    if not pdf_path:
        return {
            "success": False,
            "message": "Merge succeeded but PDF path missing",
            "merge": lo_data,
        }

    pdf_file = Path(pdf_path)
    summary = (
        f"Board Pack PDF\n\n"
        f"- Template: `{template}`\n"
        f"- PDF: `{pdf_file.name}`\n"
        f"- Generated: {pulse_date}\n"
    )
    log_project_note(
        BOARD_PACK_PROJECT, pulse_date, summary,
        tags=["coworker", "office", "board-pack"],
    )

    subject = f"Fleet Board Pack — {stamp}"
    delivery = await deliver_report(
        summary,
        subject,
        deliver=deliver,
        attachment_paths=[pdf_file],
    )

    return {
        "success": True,
        "message": f"Board pack PDF ready: {pdf_file.name}",
        "pdf_path": str(pdf_file),
        "merged_odt": lo_data.get("merged_odt"),
        "template": template,
        "delivery": delivery,
        "pulse_refreshed": pulse_result is not None,
        "merge": lo_data,
    }
