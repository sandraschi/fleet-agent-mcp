"""Push Fritz-originated events into AIWatcher's Fleet Events feed."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .common import fleet_call, parse_fleet_payload

logger = logging.getLogger("fleet_agent.coworker.aiwatcher_ingest")


def aiwatcher_http_base() -> str:
    return os.environ.get("FLEET_AGENT_AIWATCHER_HTTP_BASE", "http://127.0.0.1:10946").rstrip("/")


def aiwatcher_api_key() -> str:
    return os.environ.get("FLEET_AGENT_AIWATCHER_API_KEY", "").strip()


async def push_fleet_event(
    *,
    title: str,
    summary: str = "",
    source: str = "fritz",
    url: str = "",
    urgency_hint: float | None = None,
) -> dict[str, Any]:
    """Ingest a fleet event into AIWatcher (MCP first, REST fallback)."""
    args: dict[str, Any] = {
        "title": title,
        "summary": summary,
        "source": source,
        "url": url,
    }
    if urgency_hint is not None:
        args["urgency_hint"] = urgency_hint

    mcp_result = await fleet_call("aiwatcher", "ingest_fleet_event", args)
    if mcp_result.get("success"):
        parsed = parse_fleet_payload(mcp_result)
        if isinstance(parsed, dict) and parsed.get("success"):
            parsed["via"] = "mcp"
            return parsed
        return {"success": True, "via": "mcp", "message": mcp_result.get("message", "ingested")}

    return await _push_fleet_event_rest(
        title=title,
        summary=summary,
        source=source,
        url=url,
        urgency_hint=urgency_hint,
    )


async def _push_fleet_event_rest(
    *,
    title: str,
    summary: str,
    source: str,
    url: str,
    urgency_hint: float | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "title": title,
        "summary": summary,
        "source": source,
        "url": url,
    }
    if urgency_hint is not None:
        body["urgency_hint"] = urgency_hint

    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = aiwatcher_api_key()
    if key:
        headers["X-AIWatcher-Key"] = key

    endpoint = f"{aiwatcher_http_base()}/api/fleet/ingest"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(endpoint, json=body, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                data["via"] = "rest"
                return data
            return {
                "success": False,
                "via": "rest",
                "message": f"HTTP {resp.status_code}: {resp.text[:200]}",
            }
    except httpx.HTTPError as exc:
        logger.warning("AIWatcher ingest failed: %s", exc)
        return {"success": False, "via": "rest", "message": str(exc)}


async def push_fritz_report_event(
    *,
    flow: str,
    title: str,
    summary: str,
    urgency_hint: float | None = None,
) -> dict[str, Any]:
    """Convenience wrapper for coworker report notifications."""
    return await push_fleet_event(
        title=title,
        summary=summary,
        source="fritz",
        url=f"intel://fritz/{flow}",
        urgency_hint=urgency_hint,
    )
