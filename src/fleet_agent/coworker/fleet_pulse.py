"""Morning Fleet Pulse — gather fleet health and deliver a markdown report."""

from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..config import settings

logger = logging.getLogger("fleet_agent.coworker.fleet_pulse")

FLEET_PULSE_PROJECT = "fleet-pulse"


def _git_snapshot(repos_root: Path, repo_names: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in repo_names:
        repo = repos_root / name
        entry: dict[str, Any] = {"repo": name, "path": str(repo)}
        if not repo.is_dir():
            entry["error"] = "path missing"
            rows.append(entry)
            continue
        if not (repo / ".git").is_dir():
            entry["error"] = "not a git repo"
            rows.append(entry)
            continue
        try:
            status = subprocess.run(
                ["git", "-C", str(repo), "status", "-sb"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            entry["status"] = (status.stdout or status.stderr).strip() or "(empty)"
            log = subprocess.run(
                ["git", "-C", str(repo), "log", "-1", "--oneline"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            entry["last_commit"] = (log.stdout or "").strip() or "unknown"
        except (subprocess.TimeoutExpired, OSError) as exc:
            entry["error"] = str(exc)
        rows.append(entry)
    return rows


def format_fleet_pulse_report(
    *,
    pulse_date: str,
    health: dict[str, Any],
    discovery: dict[str, Any],
    git_rows: list[dict[str, Any]],
    pipeline: dict[str, Any] | None = None,
) -> str:
    """Build markdown report from gathered data."""
    lines = [
        f"# Fleet Pulse — {pulse_date}",
        "",
        "## Fritz",
        "",
    ]
    h = health.get("health") or health
    lines.append(f"- Agent: **{h.get('agent_name', 'Fritz')}**")
    lines.append(f"- Uptime: {h.get('uptime_human', '?')}")
    lines.append(f"- Pending tasks: {h.get('tasks', {}).get('pending', '?')}")
    lines.append(f"- Memory cards: {h.get('memory_cards', '?')}")
    wf = h.get("active_workflow")
    lines.append(f"- Active workflow: {wf or 'none'}")
    lines.append("")

    servers = (discovery.get("data") or {}).get("servers") or []
    online = sum(1 for s in servers if s.get("online"))
    lines.extend([
        "## MCP fleet",
        "",
        f"- Online: **{online}/{len(servers)}**",
        "",
    ])
    for server in servers:
        mark = "up" if server.get("online") else "down"
        alias = server.get("alias", "?")
        err = server.get("error")
        suffix = f" — {err[:80]}" if err and not server.get("online") else ""
        lines.append(f"- `{alias}`: **{mark}** ({server.get('tool_count', 0)} tools){suffix}")
    lines.append("")

    if pipeline is not None:
        from .pipeline_liveness import format_pipeline_liveness_section

        lines.extend(format_pipeline_liveness_section(pipeline))

    lines.extend(["## Git (watched repos)", ""])
    for row in git_rows:
        if row.get("error"):
            lines.append(f"- **{row['repo']}**: {row['error']}")
            continue
        status_line = row.get("status", "").splitlines()[0] if row.get("status") else "?"
        lines.append(f"- **{row['repo']}**: `{status_line}`")
        if row.get("last_commit"):
            lines.append(f"  - last: {row['last_commit']}")
    lines.append("")

    down = [s["alias"] for s in servers if not s.get("online")]
    dirty: list[str] = []
    for r in git_rows:
        st = r.get("status") or ""
        if not st or r.get("error"):
            continue
        body = "\n".join(st.splitlines()[1:]) if len(st.splitlines()) > 1 else ""
        first = st.splitlines()[0]
        if body.strip() or " M" in first or first.startswith("M ") or "??" in st:
            dirty.append(r["repo"])

    lines.extend(["## Action items", ""])
    item_n = 1
    if pipeline and not pipeline.get("healthy"):
        for alert in pipeline.get("alerts") or []:
            if alert.get("severity") == "critical":
                lines.append(
                    f"{item_n}. Pipeline: {alert.get('code')} — {alert.get('message', '')[:120]}"
                )
                item_n += 1
    if down:
        lines.append(f"{item_n}. Restart offline MCP servers: {', '.join(down)}")
        item_n += 1
    elif item_n == 1:
        lines.append("1. All registered fleet MCP servers reachable.")
        item_n += 1
    if dirty:
        lines.append(f"{item_n}. Uncommitted changes in: {', '.join(dirty)}")
    else:
        lines.append(f"{item_n}. Watched repos clean on branch tip.")
    lines.append("")

    return "\n".join(lines)


async def run_fleet_pulse(*, deliver: bool = True) -> dict[str, Any]:
    """Run Morning Fleet Pulse: discover fleet, git snapshot, report, persist, deliver."""
    from ..engine.sqlite_store import get_store
    from ..mcp.tools.fleet_bridge import fleet_discover
    from ..mcp.tools.heartbeat import heartbeat_status
    from ..settings_store import get_settings_store

    store_settings = get_settings_store()
    tz_name = store_settings.get("coworker_timezone", "Europe/Vienna")
    pulse_date = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M %Z")

    health = await heartbeat_status()
    discovery = await fleet_discover()

    from .pipeline_liveness import check_pipeline_liveness

    pipeline = await check_pipeline_liveness()

    repos_root = Path(store_settings.get("fleet_repos_root", "D:/Dev/repos"))
    watched = store_settings.get("fleet_pulse_repos") or [
        "fleet-agent-mcp",
        "mcp-central-docs",
    ]
    git_rows = _git_snapshot(repos_root, list(watched))

    report = format_fleet_pulse_report(
        pulse_date=pulse_date,
        health=health,
        discovery=discovery,
        git_rows=git_rows,
        pipeline=pipeline,
    )

    artifacts_dir = settings.data_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo(tz_name)).strftime("%Y%m%d")
    artifact_path = artifacts_dir / f"fleet-pulse-{stamp}.md"
    artifact_path.write_text(report, encoding="utf-8")

    store = get_store()
    now = datetime.now(UTC).isoformat()
    existing = store.project_get(FLEET_PULSE_PROJECT)
    if existing:
        existing["content"] = existing["content"] + f"\n\n---\n### {pulse_date}\n\n{report[:2000]}"
        existing["updated_at"] = now
        store.project_upsert(existing)
    else:
        store.project_upsert({
            "id": "fleet-pulse",
            "project_name": FLEET_PULSE_PROJECT,
            "content": f"# {FLEET_PULSE_PROJECT}\n\n{report[:2000]}",
            "tags": ["coworker", "fleet-pulse"],
            "created_at": now,
            "updated_at": now,
        })

    delivery: dict[str, Any] = {"email": None}
    if deliver:
        from ..mcp.tools.notify import _send_email_smtp

        to = store_settings.get("heartbeat_email") or store_settings.get("fleet_pulse_email")
        host = store_settings.get("smtp_host", "")
        user = store_settings.get("smtp_user", "")
        if to and host and user:
            subject = f"Fleet Pulse — {datetime.now(ZoneInfo(tz_name)).strftime('%Y-%m-%d')}"
            email_result = await _send_email_smtp(
                to=to,
                subject=subject,
                body=report,
                smtp_host=host,
                smtp_port=int(store_settings.get("smtp_port", 587)),
                smtp_user=user,
                smtp_pass=store_settings.get("smtp_pass", ""),
            )
            delivery["email"] = email_result
        else:
            delivery["email"] = {
                "success": False,
                "message": "Email skipped (set heartbeat_email + SMTP in settings)",
            }

    servers = (discovery.get("data") or {}).get("servers") or []
    online = sum(1 for s in servers if s.get("online"))

    return {
        "success": True,
        "message": f"Fleet Pulse complete: {online}/{len(servers)} MCP servers online",
        "report": report,
        "artifact_path": str(artifact_path),
        "delivery": delivery,
        "stats": {
            "servers_online": online,
            "servers_total": len(servers),
            "git_repos_checked": len(git_rows),
            "pipeline_healthy": pipeline.get("healthy"),
            "pipeline_critical_alerts": pipeline.get("critical_count", 0),
        },
        "pipeline": pipeline,
    }
