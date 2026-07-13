"""Fleet health surveillance — checks NSSM services for errors, escalates."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from .common import fleet_call, save_artifact

logger = logging.getLogger("fleet_agent.coworker.surveillance_watch")

NSSM_SERVERS = [
    ("fleet-agent", "http://127.0.0.1:10996"),
    ("aiwatcher", "http://127.0.0.1:10946"),
    ("devices-mcp", "http://127.0.0.1:10717"),
    ("tvtropes-mcp", "http://127.0.0.1:10964"),
    ("yahboom-mcp", "http://127.0.0.1:10892"),
    ("email-mcp", "http://127.0.0.1:10813"),
]


async def check_server_health(name: str, base_url: str) -> dict[str, Any]:
    """Check if a server is healthy and has errors in its logs."""
    import httpx

    result = {"name": name, "health": "unknown", "errors": [], "log_errors": 0}

    # Health check
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{base_url}/api/health")
            if r.status_code == 200:
                data = r.json()
                result["health"] = data.get("status", "ok")
            else:
                result["health"] = f"http_{r.status_code}"
    except Exception as e:
        result["health"] = "down"
        result["error"] = str(e)
        return result

    # Log check — try query_logs MCP tool via fleet bridge
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{base_url}/mcp/",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "query_logs", "arguments": {"level": "error", "limit": 5}},
                    "id": 1,
                },
            )
            if r.status_code == 200:
                data = r.json()
                logs = data.get("result", {}).get("logs", [])
                result["errors"] = [
                    {"ts": e.get("timestamp", "?"), "msg": e.get("message", "")[:120]}
                    for e in logs[:5]
                ]
                result["log_errors"] = len(logs)
    except Exception:
        result["log_check"] = "unavailable"

    return result


async def run_surveillance_watch(*, deliver: bool = True) -> dict[str, Any]:
    """Check all NSSM services, report findings, escalate if needed."""
    from ..settings_store import get_settings_store

    settings = get_settings_store()
    report_lines = ["# Fleet Surveillance Report", f"Generated: {datetime.now(UTC).isoformat()}", ""]

    status = "green"
    all_errors = []
    down_services = []

    for name, url in NSSM_SERVERS:
        result = await check_server_health(name, url)
        report_lines.append(f"## {name}")
        report_lines.append(f"- Health: {result['health']}")
        report_lines.append(f"- Log errors: {result['log_errors']}")

        if result["health"] == "down":
            down_services.append(name)
            status = "red"
        elif result["health"] not in ("ok", "shutting_down"):
            status = "yellow"

        for err in result.get("errors", []):
            all_errors.append(f"{name}: {err['msg']}")
            report_lines.append(f"  - ERROR: {err['msg']}")

        if result.get("error"):
            report_lines.append(f"  - {result['error']}")

        report_lines.append("")

    if all_errors:
        report_lines.append(f"## Total errors: {len(all_errors)}")
    if down_services:
        report_lines.append(f"## DOWN: {', '.join(down_services)}")

    report = "\n".join(report_lines)
    artifact_path = save_artifact("surveillance-watch", report, "Europe/Vienna")

    # Escalate
    if status == "red" and deliver:
        to = settings.get("heartbeat_email", "")
        smtp_host = settings.get("smtp_host", "")
        smtp_user = settings.get("smtp_user", "")
        smtp_pass = settings.get("smtp_pass", "")

        if to and smtp_host and smtp_user:
            from ..mcp.tools.notify import _send_email_smtp

            await _send_email_smtp(
                to=to,
                subject=f"FLEET SURVEILLANCE — {status.upper()} — {len(all_errors)} errors, {len(down_services)} down",
                body=report,
                smtp_host=smtp_host,
                smtp_port=int(settings.get("smtp_port", 587)),
                smtp_user=smtp_user,
                smtp_pass=smtp_pass,
            )

    return {
        "success": True,
        "status": status,
        "down_services": down_services,
        "error_count": len(all_errors),
        "message": f"Surveillance: {status.upper()} — {len(down_services)} down, {len(all_errors)} errors",
        "artifact_path": artifact_path,
    }
