"""Agentic loop control tools — start, stop, status for the autonomous execution loop."""

from __future__ import annotations

from typing import Any

from ...engine.agentic_loop import start_agentic_loop, stop_agentic_loop
from ..registry import mcp


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def agentic_start() -> dict[str, Any]:
    """Start the autonomous agent execution loop.

    The loop runs every 30s: checks for active workflows, executes pending
    tasks, and does periodic maintenance. Starts automatically on server boot.

    ## Return Format
    {"success": bool, "message": str}
    """
    from ...engine.agentic_loop import _AGENTIC_TASK

    if _AGENTIC_TASK is not None and not _AGENTIC_TASK.done():
        return {"success": True, "message": "Agentic loop already running"}
    start_agentic_loop()
    return {"success": True, "message": "Agentic loop started"}


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def agentic_stop() -> dict[str, Any]:
    """Stop the autonomous agent execution loop.

    ## Return Format
    {"success": bool, "message": str}
    """
    from ...engine.agentic_loop import _AGENTIC_TASK

    if _AGENTIC_TASK is None or _AGENTIC_TASK.done():
        return {"success": True, "message": "Agentic loop not running"}
    stop_agentic_loop()
    return {"success": True, "message": "Agentic loop stopped"}


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def agentic_status() -> dict[str, Any]:
    """Check if the autonomous agent loop is running.

    ## Return Format
    {"success": bool, "running": bool, "message": str}
    """
    from ...engine.agentic_loop import _AGENTIC_TASK, _get_interval

    running = _AGENTIC_TASK is not None and not _AGENTIC_TASK.done()
    interval = _get_interval()
    status_str = "running" if running else "stopped"
    return {
        "success": True,
        "running": running,
        "interval_s": interval,
        "message": f"Agentic loop {status_str} (interval: {interval}s)",
    }
