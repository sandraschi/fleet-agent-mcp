"""Probe arxiv-mcp, aiwatcher-mcp, and vla-mcp pipeline liveness for Fleet Pulse."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("fleet_agent.coworker.pipeline_liveness")

_ARXIV = "http://127.0.0.1:10770/api/pipeline/liveness"
_AIWATCHER = "http://127.0.0.1:10946/api/pipeline/liveness"
_VLA = "http://127.0.0.1:11024/api/pipeline/liveness"


async def check_pipeline_liveness(*, stale_hours: int = 48) -> dict[str, Any]:
    """GET both pipeline liveness endpoints; aggregate alerts."""
    stale_hours = max(1, int(stale_hours))
    params = {"stale_hours": stale_hours}
    services: dict[str, Any] = {}
    alerts: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for key, url in (
            ("arxiv_mcp", _ARXIV),
            ("aiwatcher_mcp", _AIWATCHER),
            ("vla_mcp", _VLA),
        ):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                services[key] = data
                for alert in data.get("alerts") or []:
                    alerts.append({**alert, "source": key})
            except httpx.HTTPError as exc:
                logger.warning("Pipeline probe failed for %s: %s", url, exc)
                services[key] = {"success": False, "healthy": False, "error": str(exc)}
                alerts.append(
                    {
                        "severity": "critical",
                        "code": "PIPELINE_PROBE_FAILED",
                        "source": key,
                        "message": f"Failed to probe {url}: {exc}",
                    }
                )

    critical = [a for a in alerts if a.get("severity") == "critical"]
    return {
        "success": True,
        "healthy": not critical,
        "stale_hours": stale_hours,
        "critical_count": len(critical),
        "alerts": alerts,
        "services": services,
    }


def format_pipeline_liveness_section(pipeline: dict[str, Any]) -> list[str]:
    """Markdown lines for Fleet Pulse."""
    lines = ["## Research & robotics pipelines", ""]
    if pipeline.get("healthy"):
        lines.append("- **Status:** healthy (no critical alerts)")
    else:
        lines.append(f"- **Status:** **DEGRADED** ({pipeline.get('critical_count', 0)} critical)")
    lines.append("")
    for alert in pipeline.get("alerts") or []:
        sev = alert.get("severity", "?").upper()
        src = alert.get("source", "?")
        code = alert.get("code", "?")
        msg = alert.get("message", "")
        lines.append(f"- [{sev}] `{src}` / `{code}`: {msg}")
    lines.append("")
    return lines
