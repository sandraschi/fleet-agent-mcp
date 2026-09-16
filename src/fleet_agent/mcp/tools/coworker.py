"""Coworker MCP tools - Viktor-style fleet execution.

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
from ...coworker.flows import OFFICE_FLOW_IDEAS, list_flow_catalog
from ...coworker.tasks import _COWORKER_RUNNERS
from ..registry import mcp

# Kept as a plain tuple->Literal instead of hand-maintaining a duplicate list:
# this drifted out of sync with _COWORKER_RUNNERS before (scribe_watch,
# surveillance_watch, check_email were all missing here) since nothing forced
# the two to stay aligned. Deriving from _COWORKER_RUNNERS.keys() means adding
# a flow to coworker/tasks.py is enough - no second place to remember.
_FlowName = Literal[tuple(_COWORKER_RUNNERS.keys())]  # type: ignore[valid-type]


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
    # P4: repeated manual flow runs suggest a cron schedule (one-time).
    from ...memory.suggestions import record_manual_usage

    try:
        record_manual_usage(f"coworker:{flow}", kind="flow")
    except Exception:
        pass

    runner = _COWORKER_RUNNERS.get(flow)
    if runner is None:
        return {"success": False, "message": f"Unknown flow: '{flow}'."}

    if flow == "board_pack":
        result = await run_board_pack(deliver=deliver, template=template or "fleet-board-pack.odt")
    elif flow == "artifact_pack":
        result = await run_artifact_pack(
            deliver=deliver, template=template or "fleet-artifact-pack.odt"
        )
    else:
        result = await runner(deliver=deliver)
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
        "message": (f"{len(active)} scheduled flows; {len(OFFICE_FLOW_IDEAS)} roadmap ideas"),
    }


@mcp.tool(version="0.2.0")
async def coworker_bootstrap() -> dict[str, Any]:
    """Seed default coworker recurring tasks (pulse, inbox, day prep, docs, PDF).

    Idempotent - safe to call multiple times. Creates scheduled tasks in the
    pulse TODO list if they don't already exist.

    ## Return Format
    {"success": bool, "tasks_created": int, "message": str}
    """
    return ensure_coworker_tasks()
