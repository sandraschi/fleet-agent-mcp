"""Batch artifact pack — combine ~/.fleet-agent/artifacts/*.md → styled PDF."""

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

ARTIFACT_PACK_PROJECT = "artifact-pack"


def _collect_artifacts(*, glob_pattern: str, max_files: int) -> list[Path]:
    artifacts_dir = settings.data_dir / "artifacts"
    if not artifacts_dir.is_dir():
        return []
    paths = sorted(
        artifacts_dir.glob(glob_pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [p for p in paths if p.is_file()][:max_files]


async def run_artifact_pack(*, deliver: bool = True, template: str = "fleet-artifact-pack.odt") -> dict[str, Any]:
    """Merge recent coworker markdown artifacts into one styled PDF."""
    store_settings = get_settings_store()
    tz_name = store_settings.get("coworker_timezone", "Europe/Vienna")
    pulse_date = now_label(tz_name)
    stamp = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")

    glob_pattern = store_settings.get("artifact_pack_glob", "*.md")
    max_files = int(store_settings.get("artifact_pack_max_files", 20))
    paths = _collect_artifacts(glob_pattern=glob_pattern, max_files=max_files)

    if not paths:
        return {
            "success": False,
            "message": f"No artifacts matching {glob_pattern} in {settings.data_dir / 'artifacts'}",
        }

    body_parts: list[str] = []
    for path in paths:
        body_parts.append(f"=== {path.name} ===")
        body_parts.append(markdown_to_plain(path.read_text(encoding="utf-8", errors="replace")))
        body_parts.append("")

    placeholders = {
        "TITLE": f"Fleet Artifact Pack — {stamp}",
        "DATE": pulse_date,
        "FILE_COUNT": str(len(paths)),
        "BODY": "\n".join(body_parts).strip(),
    }

    merge_result = await fleet_call(
        "libreoffice",
        "libreoffice",
        {
            "operation": "merge",
            "template": template,
            "placeholders": placeholders,
            "output_format": "pdf",
            "output_stem": f"artifact-pack-{datetime.now(ZoneInfo(tz_name)).strftime('%Y%m%d')}",
        },
    )

    inner = parse_fleet_payload(merge_result)
    if not merge_result.get("success") or not isinstance(inner, dict):
        return {
            "success": False,
            "message": merge_result.get("message") or "artifact pack merge failed",
            "sources": [str(p) for p in paths],
        }

    lo_data = inner.get("data") if isinstance(inner.get("data"), dict) else inner
    if not lo_data.get("success", inner.get("success")):
        return {
            "success": False,
            "message": lo_data.get("error") or "Artifact pack merge failed",
            "sources": [str(p) for p in paths],
            "merge": inner,
        }

    pdf_path = extract_libreoffice_output(merge_result) or lo_data.get("output")
    if not pdf_path:
        return {"success": False, "message": "Merge succeeded but PDF path missing", "merge": lo_data}

    pdf_file = Path(pdf_path)
    summary = (
        f"Artifact Pack PDF\n\n"
        f"- Files: {len(paths)}\n"
        f"- PDF: `{pdf_file.name}`\n"
        f"- Generated: {pulse_date}\n"
    )
    log_project_note(ARTIFACT_PACK_PROJECT, pulse_date, summary, tags=["coworker", "office", "artifact-pack"])

    subject = f"Fleet Artifact Pack — {stamp} ({len(paths)} files)"
    delivery = await deliver_report(
        summary,
        subject,
        deliver=deliver,
        attachment_paths=[pdf_file],
    )

    return {
        "success": True,
        "message": f"Artifact pack PDF: {len(paths)} files → {pdf_file.name}",
        "pdf_path": str(pdf_file),
        "sources": [str(p) for p in paths],
        "delivery": delivery,
        "merge": lo_data,
    }
