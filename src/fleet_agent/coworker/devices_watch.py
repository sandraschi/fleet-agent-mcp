"""Poll devices-mcp priority incidents → urgent email, hub, AIWatcher."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ..config import settings
from ..settings_store import get_settings_store
from .common import publish_intel_report
from .urgent_notify import deliver_urgent_alert, urgent_threshold

logger = logging.getLogger("fleet_agent.coworker.devices_watch")

_STATE_FILE = "devices_watch_state.json"

# Report the same incident (by kind/source/title) at most once per day.
# Raw incident ids churn when a device flaps or a new message row is created,
# so id-based dedup alone lets the same offline camera re-report every poll.
_REPORT_WINDOW_DAYS = 1
_REPORT_WINDOW_SECONDS = _REPORT_WINDOW_DAYS * 24 * 3600


def _incident_key(inc: dict[str, Any]) -> str:
    return f"{inc.get('kind')}|{inc.get('source')}|{inc.get('title')}"


def _iso_age_seconds(iso_value: str | None, now: datetime) -> float | None:
    if not iso_value:
        return None
    try:
        ts = datetime.fromisoformat(str(iso_value).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return (now - ts).total_seconds()
    except (ValueError, TypeError):
        return None


def devices_http_base() -> str:
    base = os.environ.get("FLEET_AGENT_DEVICES_HTTP_BASE")
    if not base:
        store = get_settings_store()
        base = (
            store.get("devices_mcp_http_base", "http://127.0.0.1:10717")
            if store
            else "http://127.0.0.1:10717"
        )
    return str(base).rstrip("/")


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


def _devices_port() -> int:
    base = devices_http_base()
    try:
        return int(base.rsplit(":", 1)[1].rstrip("/"))
    except (ValueError, IndexError):
        return 10717


def _find_devices_mcp() -> str | None:
    candidates = [
        os.environ.get("DEVICES_MCP_PATH", ""),
        str(Path.home() / "Dev" / "repos" / "devices-mcp"),
        r"D:\Dev\repos\devices-mcp",
        r"D:\Dev\Repos\devices-mcp",
    ]
    for c in candidates:
        if c and Path(c).is_dir():
            return c
    return None


async def _wait_port(port: int, timeout: float = 30.0) -> bool:
    import asyncio
    import socket

    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except OSError:
            await asyncio.sleep(0.5)
    return False


async def ensure_devices_mcp() -> str | None:
    """Ensure devices-mcp is reachable; autostart it from the repo if not.

    Ensure-before-open (fleet standard): never fetch from a port that may be
    down - start the service first, wait for its port, then proceed.
    """
    port = _devices_port()
    if await _wait_port(port, timeout=2):
        return None  # already running

    mcp_path = _find_devices_mcp()
    if not mcp_path:
        return (
            "devices-mcp not found. Clone it to D:\\Dev\\repos\\devices-mcp "
            "or set DEVICES_MCP_PATH."
        )

    try:
        start_script = Path(mcp_path) / "start.bat"
        if start_script.is_file():
            subprocess.Popen(
                ["cmd", "/c", str(start_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            subprocess.Popen(
                ["uv", "run", "--directory", mcp_path, "devices-mcp"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        if await _wait_port(port, timeout=30):
            return f"devices-mcp launched on :{port}."
        return f"devices-mcp launch attempted but not detected on :{port}."
    except Exception as e:
        return f"Failed to launch devices-mcp: {e}"


def _ago(iso: str | None, now: datetime | None = None) -> str:
    """Human-relative age of an ISO timestamp (e.g. '3m ago')."""
    if not iso:
        return ""
    try:
        from datetime import datetime as _dt

        parsed = _dt.fromisoformat(iso.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        now = now or datetime.now(UTC)
        seconds = max(0, int((now - parsed).total_seconds()))
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"
    except Exception:
        return ""


def format_devices_report(payload: dict[str, Any], *, new_incidents: list[dict[str, Any]]) -> str:
    scanned = payload.get("timestamp") or payload.get("scanned_at") or "?"
    lines = [
        "# Devices Priority Watch",
        "",
        f"- Scanned: {scanned} ({_ago(scanned)})",
        f"- Total incidents: {payload.get('incident_count', 0)}",
        f"- Critical: {payload.get('critical_count', 0)}",
        f"- Highest urgency: {payload.get('highest_urgency', 0)}",
        "- Dashboard: http://127.0.0.1:10716",
        "",
    ]
    if new_incidents:
        lines.append("## New incidents")
        lines.append("")
        for inc in new_incidents:
            title = str(inc.get("title", "?"))
            kind = str(inc.get("kind", "?"))
            src = str(inc.get("source", "?"))
            urgency = str(inc.get("urgency", "?"))
            lines.append(f"- **[{urgency}]** {title} (`{kind}` / {src})")
            if inc.get("description"):
                lines.append(f"  {inc['description'][:200]}")
        lines.append("")

    all_inc = payload.get("incidents") or []
    if all_inc:
        lines.append("## Active (all sources)")
        lines.append("")
        seen_titles: set[str] = set()
        shown = 0
        for inc in all_inc:
            title = str(inc.get("title", "")).strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            if shown >= 12:
                break
            shown += 1
            kind = str(inc.get("kind", ""))
            src = str(inc.get("source", ""))
            desc = str(inc.get("description", "") or "")[:120]
            meta = f" ({kind} / {src})" if kind or src else ""
            lines.append(f"- **[{inc.get('urgency', '?')}]** {title}{meta}")
            if desc:
                lines.append(f"  {desc}")
        remaining = len(all_inc) - shown
        if remaining > 0:
            lines.append("")
            lines.append(f"_...and {remaining} more._")
    else:
        lines.append("_No active priority incidents._")
    return "\n".join(lines)


async def run_devices_watch(*, deliver: bool = True) -> dict[str, Any]:
    """Poll devices-mcp /api/fleet/priority; alert on new critical incidents."""
    state = _load_state()
    seen: set[str] = set(state.get("seen_ids") or [])
    reported_keys: dict[str, str] = state.get("reported_keys") or {}
    now = datetime.now(UTC)

    ensure_msg = await ensure_devices_mcp()
    try:
        payload = await fetch_priority_incidents()
    except httpx.HTTPError as exc:
        offline = {
            "success": False,
            "message": f"devices-mcp unreachable at {devices_http_base()}: {exc}",
            "ensure": ensure_msg,
        }
        # Honest offline report to the hub - the outage must be visible,
        # not silent (fleet ensure-before-open standard). Throttled to
        # once per day so a sustained outage does not spam the hub.
        last_offline = state.get("last_offline_report")
        age = _iso_age_seconds(last_offline, now)
        if deliver and (age is None or age > _REPORT_WINDOW_SECONDS):
            try:
                await publish_intel_report(
                    title="Devices watch - devices-mcp offline",
                    markdown=(
                        "# Devices Priority Watch\n\n"
                        f"- **devices-mcp unreachable** at {devices_http_base()}\n"
                        f"- Ensure result: {ensure_msg or 'already running (then lost)'}\n"
                        f"- Auto-launch was attempted via start.bat - check "
                        "`uv run devices-mcp` or the devices-mcp start script."
                    ),
                    source="devices-mcp",
                    tags=["devices", "offline"],
                )
                state["last_offline_report"] = now.isoformat()
                _save_state(state)
            except Exception:
                logger.warning("Failed to publish offline report to hub", exc_info=True)
        return offline

    if not payload.get("success", True) and payload.get("error"):
        return {"success": False, "message": payload.get("error", "scan failed")}

    incidents = payload.get("incidents") or []
    new_incidents = []
    for i in incidents:
        inc_id = i.get("id")
        if inc_id and inc_id in seen:
            continue
        key = _incident_key(i)
        last_reported = reported_keys.get(key)
        age = _iso_age_seconds(last_reported, now)
        if age is not None and age <= _REPORT_WINDOW_SECONDS:
            continue  # same incident already reported within the window
        new_incidents.append(i)
    threshold = urgent_threshold()
    critical_new = [
        i for i in new_incidents if i.get("critical") or float(i.get("urgency") or 0) >= threshold
    ]

    report = format_devices_report(payload, new_incidents=new_incidents)
    hub_result: dict[str, Any] = {}
    urgent_result: dict[str, Any] = {}
    ingest_results: list[dict[str, Any]] = []

    if new_incidents and deliver:
        title = f"Devices Alert - {len(new_incidents)} new"
        if critical_new:
            title = f"[URGENT] Devices - {len(critical_new)} critical"

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
        reported_keys[_incident_key(inc)] = now.isoformat()
    state["seen_ids"] = list(seen)
    state["reported_keys"] = reported_keys
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
