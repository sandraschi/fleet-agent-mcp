"""Coworker MCP tools — Viktor-style fleet execution."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from ...coworker.bootstrap import ensure_coworker_tasks
from ...coworker.day_prep import run_day_prep
from ...coworker.docs_drift import run_docs_drift
from ...coworker.fleet_pulse import run_fleet_pulse
from ...coworker.flows import OFFICE_FLOW_IDEAS, list_flow_catalog
from ...coworker.artifact_pack import run_artifact_pack
from ...coworker.board_pack import run_board_pack
from ...coworker.inbox_briefing import run_inbox_briefing
from ...coworker.weekly_report_pdf import run_weekly_report_pdf
from ..registry import mcp


@mcp.tool(version="0.1.0")
async def coworker_fleet_pulse(
    deliver: Annotated[bool, Field(description="Send report via email when SMTP configured.")] = True,
) -> dict[str, Any]:
    """Run Morning Fleet Pulse now."""
    return await run_fleet_pulse(deliver=deliver)


@mcp.tool(version="0.1.0")
async def coworker_inbox_briefing(
    deliver: Annotated[bool, Field(description="Email unread digest when SMTP configured.")] = True,
) -> dict[str, Any]:
    """Run Inbox Briefing — unread email via email-mcp."""
    return await run_inbox_briefing(deliver=deliver)


@mcp.tool(version="0.1.0")
async def coworker_day_prep(
    deliver: Annotated[bool, Field(description="Email combined office prep report.")] = True,
) -> dict[str, Any]:
    """Run Office Day Prep — inbox + pulse tasks + human waits."""
    return await run_day_prep(deliver=deliver)


@mcp.tool(version="0.1.0")
async def coworker_docs_drift(
    deliver: Annotated[bool, Field(description="Email weekly docs drift audit.")] = True,
) -> dict[str, Any]:
    """Run Docs Drift Audit — README/CHANGELOG hygiene on watched repos."""
    return await run_docs_drift(deliver=deliver)


@mcp.tool(version="0.1.0")
async def coworker_weekly_report_pdf(
    deliver: Annotated[bool, Field(description="Email PDF attachment when SMTP configured.")] = True,
) -> dict[str, Any]:
    """Run Weekly Report PDF — Fleet Pulse markdown → libreoffice convert → email."""
    return await run_weekly_report_pdf(deliver=deliver)


@mcp.tool(version="0.1.0")
async def coworker_board_pack(
    deliver: Annotated[bool, Field(description="Email board pack PDF when SMTP configured.")] = True,
    template: Annotated[str, Field(description="ODT template name in libreoffice-mcp templates dir.")] = "fleet-board-pack.odt",
) -> dict[str, Any]:
    """Run Board Pack — Fleet Pulse KPIs + narrative via ODT merge → PDF → email."""
    return await run_board_pack(deliver=deliver, template=template)


@mcp.tool(version="0.1.0")
async def coworker_artifact_pack(
    deliver: Annotated[bool, Field(description="Email combined PDF when SMTP configured.")] = True,
    template: Annotated[str, Field(description="ODT template for batch pack.")] = "fleet-artifact-pack.odt",
) -> dict[str, Any]:
    """Run Artifact Pack — merge recent ~/.fleet-agent/artifacts/*.md → styled PDF."""
    return await run_artifact_pack(deliver=deliver, template=template)


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def coworker_list_flows() -> dict[str, Any]:
    """List wired coworker flows and future office flow ideas (incl. LibreOffice)."""
    return {
        "success": True,
        "active": list_flow_catalog(),
        "office_ideas": OFFICE_FLOW_IDEAS,
        "message": f"{len(list_flow_catalog())} scheduled flows; {len(OFFICE_FLOW_IDEAS)} roadmap ideas",
    }


@mcp.tool(version="0.1.0")
async def coworker_bootstrap() -> dict[str, Any]:
    """Seed default coworker recurring tasks (fleet pulse, inbox, day prep, docs drift, weekly PDF)."""
    return ensure_coworker_tasks()
