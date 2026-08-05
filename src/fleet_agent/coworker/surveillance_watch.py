"""Fleet health surveillance — checks NSSM services for errors, escalates."""

import logging
from datetime import UTC, datetime
from typing import Any

from .common import save_artifact

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


async def restart_hung_service(
    name: str, base_url: str, wait_timeout: float = 30.0
) -> dict[str, Any]:
    """Restart a hung NSSM service by making it EXIT.

    NSSM auto-restarts a service when its process exits, but NOT when the
    process hangs (alive, port dead). So: find the service PID, taskkill it -
    NSSM sees the exit and starts a fresh process. Then poll the health URL.

    Requires the service to run as the current user (taskkill without admin).
    Returns {"action": ..., "detail": ..., "healthy_after": bool}.
    """
    import asyncio
    import subprocess

    import httpx

    def _service_pid() -> int | None:
        try:
            out = subprocess.run(
                ["sc", "queryex", name], capture_output=True, text=True, timeout=10
            ).stdout
            for line in out.splitlines():
                line = line.strip()
                if line.upper().startswith("PID") and ":" in line:
                    pid = line.split(":", 1)[1].strip()
                    if pid.isdigit():
                        return int(pid)
        except Exception:
            pass
        return None

    pid = _service_pid()
    if pid is None:
        return {
            "action": "no_service",
            "detail": f"no service '{name}' or no PID",
            "healthy_after": False,
        }

    try:
        kill = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid), "/T"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        detail = f"killed PID {pid} -> nssm should auto-restart"
        if kill.returncode != 0:
            detail = f"taskkill PID {pid} failed: {kill.stderr.strip()[:120]} (access denied?)"
            return {"action": "kill_failed", "detail": detail, "healthy_after": False}
    except Exception as e:
        return {"action": "kill_failed", "detail": f"taskkill error: {e}", "healthy_after": False}

    # Poll health after the nssm restart
    deadline = asyncio.get_event_loop().time() + wait_timeout
    healthy = False
    while asyncio.get_event_loop().time() < deadline:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{base_url}/api/health")
                if r.status_code == 200:
                    healthy = True
                    break
        except Exception:
            pass
        await asyncio.sleep(2)
    return {"action": "restarted", "detail": detail, "healthy_after": healthy}


async def run_surveillance_watch(*, deliver: bool = True) -> dict[str, Any]:
    """Check all NSSM services, report findings, escalate if needed."""
    from ..settings_store import get_settings_store

    settings = get_settings_store()
    report_lines = [
        "# Fleet Surveillance Report",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
    ]

    status = "green"
    all_errors = []
    down_services = []
    restart_count = 0

    for name, url in NSSM_SERVERS:
        result = await check_server_health(name, url)
        report_lines.append(f"## {name}")
        report_lines.append(f"- Health: {result['health']}")
        report_lines.append(f"- Log errors: {result['log_errors']}")

        if result["health"] == "down":
            down_services.append(name)
            status = "red"
            # Self-heal: hung NSSM service -> kill process, nssm restarts
            restart = await restart_hung_service(name, url)
            if restart["action"] == "restarted":
                if restart["healthy_after"]:
                    report_lines.append(
                        f"- RESTARTED (was hung): {restart['detail']} - now healthy"
                    )
                    restart_count += 1
                    down_services.remove(name)
                    if status == "red" and not down_services:
                        status = "green"
                else:
                    report_lines.append(f"- RESTARTED but STILL DOWN: {restart['detail']}")
            else:
                report_lines.append(f"- Restart failed ({restart['action']}): {restart['detail']}")
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
    if restart_count:
        report_lines.append(f"## Restarted hung services: {restart_count}")
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
                subject=f"FLEET SURV {status.upper()} - e={len(all_errors)} d={len(down_services)}",
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
        "message": f"Surveillance: {status.upper()} - d={len(down_services)} e={len(all_errors)}",
        "artifact_path": artifact_path,
    }
