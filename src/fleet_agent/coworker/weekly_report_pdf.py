"""Weekly Report PDF — Fleet Pulse markdown → LibreOffice PDF → email."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..config import settings
from ..settings_store import get_settings_store
from .common import (
    deliver_report,
    extract_libreoffice_output,
    fleet_call,
    log_project_note,
    markdown_to_plain,
    now_label,
    parse_fleet_payload,
)
from .fleet_pulse import run_fleet_pulse

WEEKLY_REPORT_PROJECT = "weekly-report-pdf"


def _latest_fleet_pulse_artifact() -> Path | None:
    artifacts_dir = settings.data_dir / "artifacts"
    if not artifacts_dir.is_dir():
        return None
    matches = sorted(artifacts_dir.glob("fleet-pulse-*.md"), reverse=True)
    return matches[0] if matches else None


async def run_weekly_report_pdf(*, deliver: bool = True) -> dict[str, Any]:
    """Convert latest Fleet Pulse markdown to PDF and optionally email it."""
    store_settings = get_settings_store()
    tz_name = store_settings.get("coworker_timezone", "Europe/Vienna")
    pulse_date = now_label(tz_name)

    md_path = _latest_fleet_pulse_artifact()
    pulse_result: dict[str, Any] | None = None
    if md_path is None:
        pulse_result = await run_fleet_pulse(deliver=False)
        md_path = Path(pulse_result["artifact_path"])

    if not md_path.is_file():
        return {
            "success": False,
            "message": "No Fleet Pulse markdown artifact available",
            "artifact_path": None,
        }

    report_md = md_path.read_text(encoding="utf-8")
    stamp = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")

    merge_result = await fleet_call(
        "libreoffice",
        "libreoffice",
        {
            "operation": "merge",
            "template": "fleet-report.odt",
            "placeholders": {
                "TITLE": f"Weekly Fleet Report — {stamp}",
                "DATE": pulse_date,
                "SUMMARY": "Automated Fleet Pulse export",
                "BODY": markdown_to_plain(report_md),
            },
            "output_format": "pdf",
            "output_stem": f"weekly-report-{datetime.now(ZoneInfo(tz_name)).strftime('%Y%m%d')}",
        },
    )

    inner = parse_fleet_payload(merge_result)
    lo_data = inner.get("data") if isinstance(inner, dict) and isinstance(inner.get("data"), dict) else inner
    pdf_path = None
    if merge_result.get("success") and isinstance(lo_data, dict) and lo_data.get("success", inner.get("success") if isinstance(inner, dict) else False):
        pdf_path = extract_libreoffice_output(merge_result) or lo_data.get("output")

    if not pdf_path:
        convert_result = await fleet_call(
            "libreoffice",
            "libreoffice",
            {
                "operation": "convert",
                "input_path": str(md_path),
                "output_format": "pdf",
            },
        )
        inner = parse_fleet_payload(convert_result)
        if not convert_result.get("success") or not isinstance(inner, dict):
            err = convert_result.get("message") or merge_result.get("message") or "libreoffice export failed"
            return {
                "success": False,
                "message": err,
                "artifact_path": str(md_path),
            }
        lo_data = inner.get("data") if isinstance(inner.get("data"), dict) else inner
        if not lo_data.get("success", inner.get("success")):
            return {
                "success": False,
                "message": lo_data.get("error") or "Conversion failed",
                "artifact_path": str(md_path),
            }
        pdf_path = extract_libreoffice_output(convert_result) or lo_data.get("output")

    if not pdf_path:
        return {
            "success": False,
            "message": "Convert succeeded but PDF path missing",
            "artifact_path": str(md_path),
            "convert": inner,
        }

    pdf_file = Path(pdf_path)
    report = (
        f"Weekly Fleet Report PDF\n\n"
        f"- Source: `{md_path.name}`\n"
        f"- PDF: `{pdf_file.name}`\n"
        f"- Generated: {pulse_date}\n"
    )
    log_project_note(WEEKLY_REPORT_PROJECT, pulse_date, report, tags=["coworker", "office", "pdf"])

    subject = f"Weekly Fleet Report — {datetime.now(ZoneInfo(tz_name)).strftime('%Y-%m-%d')}"
    delivery = await deliver_report(
        report,
        subject,
        deliver=deliver,
        attachment_paths=[pdf_file],
    )

    return {
        "success": True,
        "message": f"Weekly report PDF ready: {pdf_file.name}",
        "artifact_path": str(md_path),
        "pdf_path": str(pdf_file),
        "delivery": delivery,
        "pulse_refreshed": pulse_result is not None,
        "convert": lo_data,
    }