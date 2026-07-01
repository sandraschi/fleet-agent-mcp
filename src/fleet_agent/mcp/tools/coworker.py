"""Coworker MCP tools — Viktor-style fleet execution.

[RATIONAL]: Consolidates 11 scheduled coworker flows into a single portmanteau
tool to reduce context bloat. Each flow is an operation on the coworker_execute
tool, plus two read-only discovery tools.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from ...coworker.artifact_pack import run_artifact_pack
from ...coworker.board_pack import run_board_pack
from ...coworker.bootstrap import ensure_coworker_tasks
from ...coworker.cursor_spend_watch import run_cursor_spend_watch
from ...coworker.day_prep import run_day_prep
from ...coworker.devices_watch import run_devices_watch
from ...coworker.docs_drift import run_docs_drift
from ...coworker.fleet_pulse import run_fleet_pulse
from ...coworker.flows import OFFICE_FLOW_IDEAS, list_flow_catalog
from ...coworker.inbox_briefing import run_inbox_briefing
from ...coworker.weekly_report_pdf import run_weekly_report_pdf
from ..registry import mcp

_FlowName = Literal[
    "fleet_pulse",
    "inbox_briefing",
    "day_prep",
    "docs_drift",
    "weekly_report_pdf",
    "board_pack",
    "artifact_pack",
    "devices_watch",
    "cursor_spend_watch",
]


@mcp.tool(annotations={"readonly": False}, version="0.2.0")
async def coworker_execute(
    flow: Annotated[_FlowName, Field(description="Scheduled coworker flow to run.")],
    deliver: Annotated[
        bool,
        Field(description="Send report via email when SMTP configured."),
    ] = True,
    template: Annotated[
        str,
        Field(description="ODT template name for board_pack / artifact_pack."),
    ] = "",
) -> dict[str, Any]:
    """Run a scheduled coworker flow immediately.

    Coworker flows are Viktor-style scheduled tasks that produce reports
    and deliver them via email or the Intel Reports Hub.

    ## Return Format
    {"success": bool, "flow": str, "delivered": bool, "message": str, "data": dict}

    ## Examples
    coworker_execute(flow="fleet_pulse")
    coworker_execute(flow="board_pack", deliver=True, template="fleet-board-pack.odt")
    """
    runners = {
        "fleet_pulse": lambda: run_fleet_pulse(deliver=deliver),
        "inbox_briefing": lambda: run_inbox_briefing(deliver=deliver),
        "day_prep": lambda: run_day_prep(deliver=deliver),
        "docs_drift": lambda: run_docs_drift(deliver=deliver),
        "weekly_report_pdf": lambda: run_weekly_report_pdf(deliver=deliver),
        "board_pack": lambda: run_board_pack(
            deliver=deliver,
            template=template or "fleet-board-pack.odt",
        ),
        "artifact_pack": lambda: run_artifact_pack(
            deliver=deliver,
            template=template or "fleet-artifact-pack.odt",
        ),
        "devices_watch": lambda: run_devices_watch(deliver=deliver),
        "cursor_spend_watch": lambda: run_cursor_spend_watch(deliver=deliver),
    }
    runner = runners.get(flow)
    if runner is None:
        return {"success": False, "message": f"Unknown flow: '{flow}'."}
    result = await runner()
    return {**result, "flow": flow}


@mcp.tool(annotations={"readonly": True}, version="0.2.0")
async def coworker_list_flows() -> dict[str, Any]:
    """List wired coworker flows and future office flow ideas (incl. LibreOffice).

    ## Return Format
    {"success": bool, "active": list[dict], "office_ideas": list[dict], "message": str}
    """
    active = list_flow_catalog()
    return {
        "success": True,
        "active": active,
        "office_ideas": OFFICE_FLOW_IDEAS,
        "message": (
            f"{len(active)} scheduled flows; {len(OFFICE_FLOW_IDEAS)} roadmap ideas"
        ),
    }


@mcp.tool(version="0.2.0")
async def coworker_bootstrap() -> dict[str, Any]:
    """Seed default coworker recurring tasks (pulse, inbox, day prep, docs, PDF).

    Idempotent — safe to call multiple times. Creates scheduled tasks in the
    pulse TODO list if they don't already exist.

    ## Return Format
    {"success": bool, "tasks_created": int, "message": str}
    """
    return ensure_coworker_tasks()
