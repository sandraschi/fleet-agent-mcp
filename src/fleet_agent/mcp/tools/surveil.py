"""fritz_surveil MCP tool - fleet triage portmanteau (P3).

[RATIONAL]: One tool, five operations per FLEET_DEEP_ANALYSIS_2026-07-13
section 1.2: scan_now / scan_all / set_thresholds / history / ack. External
domain (aiwatcher urgency) is handled by aiwatcher surge mode; this tool is
the fleet-domain leg of the same triage pipeline.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from pydantic import Field

from ...coworker import surveil
from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.surveil")


@mcp.tool(annotations={"readonly": False}, version="0.1.0")
async def fritz_surveil(
    operation: Annotated[
        Literal["scan_all", "scan_now", "set_thresholds", "history", "ack"],
        Field(description="Surveillance operation."),
    ],
    server_id: Annotated[
        str | None, Field(description="Target server (scan_now, set_thresholds, history).")
    ] = None,
    rules_json: Annotated[
        str | None, Field(description="Rules override JSON (set_thresholds).")
    ] = None,
    since: Annotated[
        str | None, Field(description="ISO timestamp - only alerts after this (history).")
    ] = None,
    alert_id: Annotated[str | None, Field(description="Alert id (ack).")] = None,
) -> dict[str, Any]:
    """Fleet-domain triage: scan hub health/uptime/supervisor for precursors.

    - scan_all: evaluate every supervised server; urgent hits -> hub inbox to
      admiral + #sfb-alerts crosspost; notices -> inbox to fritz; deduped per
      (server, rule) with escalation override.
    - scan_now: one server only.
    - set_thresholds: store a per-server rules override (JSON, same shape as
      the defaults; overrides are kept in the surveil state file).
    - history: recent alerts (filter by server_id / since).
    - ack: mark an alert acknowledged.

    ## Return Format
    {"success": bool, "scanned": int, "hits": [...], "rules": {...}}

    ## Examples
    fritz_surveil(operation="scan_all")
    fritz_surveil(operation="scan_now", server_id="calibre-mcp")
    fritz_surveil(operation="history", server_id="calibre-mcp")
    fritz_surveil(operation="ack", alert_id="abc12345")
    """
    try:
        if operation in ("scan_all", "scan_now"):
            result = await surveil.scan_fleet(
                server_filter=server_id if operation == "scan_now" else None
            )
            return result
        if operation == "set_thresholds":
            if not server_id or not rules_json:
                return {"success": False, "error": "server_id and rules_json required"}
            import json

            rules = json.loads(rules_json)
            surveil.set_thresholds(server_id, rules)
            return {"success": True, "server_id": server_id, "rules": rules}
        if operation == "history":
            return surveil.alert_history(server_id=server_id, since=since)
        if operation == "ack":
            if not alert_id:
                return {"success": False, "error": "alert_id required"}
            return surveil.ack_alert(alert_id)
        return {"success": False, "error": f"unknown operation {operation}"}
    except Exception as exc:
        logger.warning("fritz_surveil %s failed: %s", operation, exc)
        return {"success": False, "error": str(exc)}
