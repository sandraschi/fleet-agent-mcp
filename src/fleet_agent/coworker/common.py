"""Shared helpers for coworker flows."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..config import settings
from ..engine.sqlite_store import get_store
from ..settings_store import get_settings_store

logger = logging.getLogger("fleet_agent.coworker.common")


def task_metadata(task: dict[str, Any]) -> dict[str, Any]:
    raw = task.get("metadata_json") or task.get("metadata") or "{}"
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def coworker_type(task: dict[str, Any]) -> str | None:
    meta = task_metadata(task)
    if meta.get("coworker"):
        return str(meta["coworker"])
    text = (task.get("task") or "").lower()
    if "coworker:" in text:
        return text.split("coworker:", 1)[1].strip().split()[0]
    if "fleet pulse" in text:
        return "fleet_pulse"
    if "inbox briefing" in text:
        return "inbox_briefing"
    if "docs drift" in text:
        return "docs_drift"
    if "morning brief" in text or "morning_brief" in text:
        return "morning_brief"
    if "day prep" in text or "office day" in text:
        return "day_prep"
    if "weekly report" in text or "report pdf" in text:
        return "weekly_report_pdf"
    if "board pack" in text:
        return "board_pack"
    if "artifact pack" in text:
        return "artifact_pack"
    if "cursor spend" in text:
        return "cursor_spend_watch"
    if "devices watch" in text or "devices priority" in text:
        return "devices_watch"
    return None


def markdown_to_plain(md: str, *, max_chars: int = 8000) -> str:
    """Strip markdown for ODT/email placeholders."""
    import re

    lines: list[str] = []
    for raw in md.splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        if line.startswith("#"):
            lines.append(line.lstrip("#").strip())
            continue
        line = re.sub(r"`([^`]+)`", r"\1", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        if line.startswith("- "):
            lines.append(f"• {line[2:]}")
        else:
            lines.append(line)
    text = "\n".join(lines).strip()
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text


async def fleet_call(
    server: str, tool: str, arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from ..mcp.tools.fleet_bridge import fleet_call_tool

    return await fleet_call_tool(server=server, tool=tool, arguments=arguments or {})


def parse_fleet_payload(result: dict[str, Any]) -> Any:
    if not result.get("success"):
        return result
    content = (result.get("data") or {}).get("content") or []
    for part in content:
        if not isinstance(part, str):
            continue
        try:
            return json.loads(part)
        except json.JSONDecodeError:
            continue
    return {"raw": content}


def extract_libreoffice_output(result: dict[str, Any]) -> str | None:
    """Pull output file path from a libreoffice fleet_call result."""
    payload = parse_fleet_payload(result)
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict):
        if data.get("output"):
            return str(data["output"])
        nested = data.get("data")
        if isinstance(nested, dict) and nested.get("output"):
            return str(nested["output"])
    if payload.get("output"):
        return str(payload["output"])
    return None


def now_label(tz_name: str) -> str:
    return datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M %Z")


def save_artifact(slug: str, report: str, tz_name: str) -> str:
    artifacts_dir = settings.data_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo(tz_name)).strftime("%Y%m%d")
    path = artifacts_dir / f"{slug}-{stamp}.md"
    path.write_text(report, encoding="utf-8")
    return str(path)


def log_project_note(project: str, title: str, body: str, tags: list[str] | None = None) -> None:
    store = get_store()
    now = datetime.now(UTC).isoformat()
    snippet = body[:2000]
    existing = store.project_get(project)
    if existing:
        existing["content"] = existing["content"] + f"\n\n---\n### {title}\n\n{snippet}"
        existing["updated_at"] = now
        if tags:
            existing["tags"] = list(set((existing.get("tags") or []) + tags))
        store.project_upsert(existing)
    else:
        store.project_upsert({
            "id": project,
            "project_name": project,
            "content": f"# {project}\n\n### {title}\n\n{snippet}",
            "tags": tags or ["coworker"],
            "created_at": now,
            "updated_at": now,
        })


async def publish_intel_report(
    *,
    title: str,
    markdown: str,
    source: str = "fritz",
    summary: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Publish markdown report to Intel Hub (iPad / Tailscale)."""
    from ..intel_hub.client import publish_to_hub

    return await publish_to_hub(
        title=title,
        source=source,
        markdown=markdown,
        summary=summary or markdown[:280].replace("\n", " "),
        tags=tags,
    )


async def deliver_report(
    report: str,
    subject: str,
    *,
    deliver: bool,
    attachment_paths: list[Path] | None = None,
) -> dict[str, Any]:
    if not deliver:
        return {"success": False, "message": "Delivery disabled"}

    store_settings = get_settings_store()
    to = store_settings.get("heartbeat_email") or store_settings.get("fleet_pulse_email")
    host = store_settings.get("smtp_host", "")
    user = store_settings.get("smtp_user", "")
    if not (to and host and user):
        return {
            "success": False,
            "message": "Email skipped (set heartbeat_email + SMTP in settings)",
        }

    from ..mcp.tools.notify import send_email_message

    attachments = [str(p) for p in attachment_paths or [] if Path(p).is_file()]
    return await send_email_message(
        to=to,
        subject=subject,
        body=report,
        attachment_paths=attachments,
        smtp_host=host,
        smtp_port=int(store_settings.get("smtp_port", 587)),
        smtp_user=user,
        smtp_pass=store_settings.get("smtp_pass", ""),
    )
