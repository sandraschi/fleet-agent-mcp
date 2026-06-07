"""Intel Reports Hub MCP tools + AIWatcher fleet event push."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from ...coworker.aiwatcher_ingest import push_fleet_event
from ...intel_hub.client import hub_base_url, publish_to_hub
from ...intel_hub.server import hub_port
from ...intel_hub.store import list_reports
from ..registry import mcp


@mcp.tool(version="0.1.0")
async def intel_reports_publish(
    title: Annotated[str, Field(description="Report title shown on hub index.")],
    markdown: Annotated[str, Field(description="Markdown body (rendered to HTML).")],
    source: Annotated[str, Field(description="Source badge: fritz, aiwatcher, etc.")] = "fritz",
    summary: Annotated[str, Field(description="Short blurb for index card.")] = "",
) -> dict[str, Any]:
    """Publish a report to the Intel Hub (iPad / Tailscale)."""
    result = await publish_to_hub(
        title=title,
        markdown=markdown,
        source=source,
        summary=summary,
    )
    result["hub_url"] = hub_base_url()
    return result


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def intel_reports_list(
    limit: Annotated[int, Field(description="Max reports to return.")] = 20,
) -> dict[str, Any]:
    """List published intel reports."""
    reports = list_reports(limit=limit)
    return {
        "success": True,
        "hub_url": hub_base_url(),
        "port": hub_port(),
        "reports": reports,
        "count": len(reports),
    }


@mcp.tool(version="0.1.0")
async def aiwatcher_push_event(
    title: Annotated[str, Field(description="Event title for AIWatcher Fleet Events feed.")],
    summary: Annotated[str, Field(description="Event body / context.")] = "",
    source: Annotated[str, Field(description="Producer id.")] = "fritz",
    url: Annotated[str, Field(description="Optional link.")] = "",
    urgency_hint: Annotated[
        float | None,
        Field(description="0–10 pre-score; ≥8 surfaces in bundles."),
    ] = None,
) -> dict[str, Any]:
    """Push a structured event from Fritz into AIWatcher."""
    return await push_fleet_event(
        title=title,
        summary=summary,
        source=source,
        url=url,
        urgency_hint=urgency_hint,
    )
