"""Heartbeat tools — agent wake-up routine, health check, and stats.

Inspired by kagura-agent's cron-based heartbeat: every N minutes, the agent
wakes, checks its state machine, executes the current task, and advances.
"""

import time
from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from ...config import settings
from ...engine.sqlite_store import get_store
from ...engine.state_machine import get_state_machine
from ..registry import mcp

_START_TIME = time.time()


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def heartbeat_status(
    ctx: Context = None,
) -> dict[str, Any]:
    """Agent health check — uptime, active workflows, task count, memory stats.

    ## Return Format
    {"success": bool, "health": dict, "message": str}

    ## Examples
    heartbeat_status()
    """
    sm = get_state_machine()
    store = get_store()

    uptime_seconds = int(time.time() - _START_TIME)
    instance = sm.status()

    tasks = store.todo_list()
    pending = sum(1 for t in tasks if t.get("status") == "pending")
    done = sum(1 for t in tasks if t.get("status") == "done")

    cards = store.cards_list()
    total_corrections = len(store.evolution_list(limit=10000))

    return {
        "success": True,
        "health": {
            "agent_name": settings.agent_name,
            "uptime_seconds": uptime_seconds,
            "uptime_human": f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m",
            "active_workflow": instance.workflow_name if instance else None,
            "current_node": instance.current_node if instance else None,
            "tasks": {"pending": pending, "done": done, "total": len(tasks)},
            "memory_cards": len(cards),
            "evolution_entries": total_corrections,
            "workflows_registered": len(sm.list_workflows()),
            "heartbeat_interval_minutes": settings.heartbeat_interval_minutes,
            "heartbeat_enabled": settings.heartbeat_enabled,
        },
        "message": (
            f"Agent '{settings.agent_name}' is healthy "
            f"(uptime: {uptime_seconds // 3600}h "
            f"{(uptime_seconds % 3600) // 60}m)."
        ),
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def pipeline_liveness_check(
    stale_hours: Annotated[
        int,
        Field(description="Max hours since last feed poll before flagging stale.", ge=1),
    ] = 48,
    ctx: Context = None,
) -> dict[str, Any]:
    """Probe arxiv-mcp + aiwatcher-mcp open-weight pipeline liveness.

    Checks the code-hunt + aiwatcher arXiv ingestion pipeline for stale feeds
    and unreachable upstream servers. Returns healthy/degraded with per-service
    details and critical alert count.

    ## Return Format
    {"success": bool, "healthy": bool, "critical_count": int,
     "services": dict, "message": str}

    ## Examples
    pipeline_liveness_check()
    pipeline_liveness_check(stale_hours=24)
    """
    from ...coworker.pipeline_liveness import check_pipeline_liveness

    result = await check_pipeline_liveness(stale_hours=stale_hours)
    n = result.get("critical_count", 0)
    return {
        **result,
        "message": (
            "Pipeline healthy."
            if result.get("healthy")
            else f"Pipeline degraded: {n} critical alert(s)."
        ),
    }


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def heartbeat_wake(
    ctx: Context = None,
) -> dict[str, Any]:
    """Agent wake-up routine — check state machine, get current task, suggest next action.

    This is the core heartbeat: called by cron or manually, it returns what
    the agent should do right now based on active workflows and pending tasks.

    ## Return Format
    {"success": bool, "action": dict, "message": str}

    ## Notes
    - Checks active workflow first (state machine has priority)
    - If no active workflow, checks pending tasks
    - Returns the next recommended action for a sub-agent to execute
    """
    sm = get_state_machine()
    store = get_store()

    # Check for active workflow
    instance = sm.status()
    if instance is not None:
        task = sm.get_current_task()
        branches = sm.get_current_branches()
        return {
            "success": True,
            "mode": "workflow",
            "workflow": instance.workflow_name,
            "current_node": instance.current_node,
            "task": task,
            "branches": branches,
            "steps_completed": len(instance.history),
            "action": "Execute the current task, then call workflow_next() to advance.",
            "message": f"Active workflow: {instance.workflow_name} -> {instance.current_node}.",
        }

    # No active workflow — check pending tasks
    tasks = store.todo_list(status="pending")
    if tasks:
        priority_order = {"high": 0, "medium": 1, "low": 2}
        tasks.sort(key=lambda t: (
            priority_order.get(t.get("priority", "medium"), 1),
            t.get("created_at", ""),
        ))
        next_task = tasks[0]
        return {
            "success": True,
            "mode": "task",
            "next_task": {
                "id": next_task["id"],
                "task": next_task["task"],
                "priority": next_task.get("priority"),
                "group": next_task.get("group_name"),
            },
            "total_pending": len(tasks),
            "action": f"Execute highest-priority task: '{next_task['task'][:80]}'",
            "message": (
                f"No active workflow. {len(tasks)} pending tasks. "
                f"Top: '{next_task['task'][:80]}'."
            ),
        }

    # Nothing to do
    return {
        "success": True,
        "mode": "idle",
            "action": (
                "Run memory_lint() to clean up knowledge base, "
                "or pulse_stale() to find forgotten tasks."
            ),
        "suggestions": [
            "workflow_autodiscover() to register workflows",
            "memory_lint() to check knowledge base health",
            "pulse_stale() to find forgotten tasks",
            "workflow_start('daily') to begin a daily routine",
            "workflow_start('morning_brief') for WF-001 (ViLife + glance + aiwatcher)",
        ],
        "message": "No active workflow or pending tasks. Agent is idle.",
    }
