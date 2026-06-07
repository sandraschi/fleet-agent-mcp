"""Poll devices-mcp priority incidents → urgent email, hub, AIWatcher."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import httpx

from ..config import settings
from ..settings_store import get_settings_store
from .common import publish_intel_report
from .urgent_notify import deliver_urgent_alert, urgent_threshold

logger = logging.getLogger("fleet_agent.coworker.devices_watch")

_STATE_FILE = "devices_watch_state.json"


def devices_http_base() -> str:
    return os.environ.get(
        "FLEET_AGENT_DEVICES_HTTP_BASE",
        get_settings_store().get("devices_mcp_http_base", "http://127.0.0.1:10717"),
    ).rstrip("/")


def _state_path():
    return settings.data_dir / _STATE_FILE


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.is_file():
        return {"seen_ids": [], "last_run": None}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"seen_ids": [], "last_run": None}


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now(UTC).isoformat()
    # Keep last 500 ids for dedup
    state["seen_ids"] = list(state.get("seen_ids") or [])[-500:]
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


async def fetch_priority_incidents() -> dict[str, Any]:
    url = f"{devices_http_base()}/api/fleet/priority"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


def format_devices_report(payload: dict[str, Any], *, new_incidents: list[dict[str, Any]]) -> str:
    lines = [
        "# Devices Priority Watch",
        "",
        f"- Scanned: {payload.get('timestamp', '?')}",
        f"- Total incidents: {payload.get('incident_count', 0)}",
        f"- Critical: {payload.get('critical_count', 0)}",
        f"- Highest urgency: {payload.get('highest_urgency', 0)}",
        "",
    ]
    if new_incidents:
        lines.append("## New incidents")
        lines.append("")
        for inc in new_incidents:
            lines.append(
                f"- **[{inc.get('urgency', '?')}]** {inc.get('title', '?')} "
                f"(`{inc.get('kind', '?')}` / {inc.get('source', '?')})"
            )
            if inc.get("description"):
                lines.append(f"  {inc['description'][:200]}")
        lines.append("")
    all_inc = payload.get("incidents") or []
    if all_inc:
        lines.append("## Active (all sources)")
        lines.append("")
        for inc in all_inc[:12]:
            lines.append(f"- [{inc.get('urgency', '?')}] {inc.get('title', '?')}")
    else:
        lines.append("_No active priority incidents._")
    return "\n".join(lines)


async def run_devices_watch(*, deliver: bool = True) -> dict[str, Any]:
    """Poll devices-mcp /api/fleet/priority; alert on new critical incidents."""
    state = _load_state()
    seen: set[str] = set(state.get("seen_ids") or [])

    try:
        payload = await fetch_priority_incidents()
    except httpx.HTTPError as exc:
        return {
            "success": False,
            "message": f"devices-mcp unreachable at {devices_http_base()}: {exc}",
        }

    if not payload.get("success", True) and payload.get("error"):
        return {"success": False, "message": payload.get("error", "scan failed")}

    incidents = payload.get("incidents") or []
    new_incidents = [i for i in incidents if i.get("id") and i["id"] not in seen]
    threshold = urgent_threshold()
    critical_new = [
        i for i in new_incidents
        if i.get("critical") or float(i.get("urgency") or 0) >= threshold
    ]

    report = format_devices_report(payload, new_incidents=new_incidents)
    hub_result: dict[str, Any] = {}
    urgent_result: dict[str, Any] = {}
    ingest_results: list[dict[str, Any]] = []

    if new_incidents and deliver:
        title = f"Devices Alert — {len(new_incidents)} new"
        if critical_new:
            title = f"🚨 Devices URGENT — {len(critical_new)} critical"

        hub_result = await publish_intel_report(
            title=title,
            markdown=report,
            source="devices-mcp",
            tags=["devices", "priority", "home"],
        )

        hub_link = ""
        if hub_result.get("success"):
            from ..intel_hub.client import hub_base_url

            hub_link = f"{hub_base_url()}{hub_result.get('url_path', '/')}"

        if critical_new:
            body_lines = [
                f"{inc.get('title')}: {inc.get('description', '')[:120]}"
                for inc in critical_new[:6]
            ]
            max_urgency = max(float(i.get("urgency") or 0) for i in critical_new)
            urgent_result = await deliver_urgent_alert(
                subject=title.replace("🚨 ", ""),
                body="\n".join(body_lines),
                reason="devices-mcp priority",
                urgency=max_urgency,
                critical=True,
                hub_url=hub_link,
            )

        try:
            from .aiwatcher_ingest import push_fleet_event

            for inc in critical_new[:3]:
                ing = await push_fleet_event(
                    title=inc.get("title", "Device alert")[:200],
                    summary=inc.get("description", "")[:500],
                    source="devices-mcp",
                    url=f"devices://{inc.get('kind', 'alert')}",
                    urgency_hint=float(inc.get("urgency") or 9.0),
                )
                ingest_results.append(ing)
        except Exception as exc:
            logger.info("AIWatcher ingest for devices skipped: %s", exc)

    for inc in new_incidents:
        if inc.get("id"):
            seen.add(inc["id"])
    state["seen_ids"] = list(seen)
    _save_state(state)

    return {
        "success": True,
        "message": (
            f"Devices watch: {payload.get('incident_count', 0)} active, "
            f"{len(new_incidents)} new, {len(critical_new)} critical new"
        ),
        "report": report,
        "stats": {
            "incident_count": payload.get("incident_count", 0),
            "critical_count": payload.get("critical_count", 0),
            "new_count": len(new_incidents),
            "critical_new_count": len(critical_new),
            "sources": payload.get("sources", {}),
        },
        "intel_hub": hub_result,
        "urgent_alert": urgent_result,
        "aiwatcher_ingest": ingest_results,
        "new_incidents": new_incidents,
    }
