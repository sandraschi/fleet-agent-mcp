"""Task management tools — unified TODO list with north-star alignment.

Inspired by kagura-agent/pulse-todo: single TODO.md approach with dependency
grouping (self/human/external), cron synchronization, stale detection.

[RATIONAL]: Task management is a single concern — create, list, complete,
align with purpose, detect staleness. Consolidating avoids tool fragmentation.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from ...engine.sqlite_store import get_store
from ..registry import mcp


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def pulse_add(
    task: Annotated[str, Field(description="Task description.")],
    description: Annotated[
        str | None,
        Field(description="Longer explanation of what this task involves."),
    ] = None,
    group: Annotated[
        str,
        Field(description="Dependency group: 'self', 'human', or 'external'."),
    ] = "self",
    priority: Annotated[str, Field(description="Priority: 'high', 'medium', or 'low'.")] = "medium",
    recurrence: Annotated[
        str | None,
        Field(description="Cron-style recurrence for repeating tasks."),
    ] = None,
    script_id: Annotated[
        str | None,
        Field(description="ID of a script to run when this task fires."),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Add a task to the unified TODO list.

    Tasks are grouped by dependency: 'self' (do it yourself), 'human' (waiting on human),
    or 'external' (blocked on external system).

    Tasks are validated for feasibility before being stored. Impossible tasks
    (perpetual motion, squaring the circle, etc.) are refused with humor.

    ## Return Format
    {"success": bool, "task": dict, "message": str}

    ## Examples
    pulse_add("Write SPEC.md", group="self", priority="high")
    pulse_add("Wait for review", group="human")
    pulse_add("Sync failures? Run sync every 4h", group="self", recurrence="0 */4 * * *")
    """
    # Validate task feasibility via LLM
    try:
        from ...llm_client import chat_completion
        validation = await chat_completion([
            {"role": "system", "content": (
                "You check if a task is physically or logically possible. "
                "If possible, reply ONLY with 'OK'. "
                "If impossible (perpetual motion, squaring the circle, time travel, "
                "making 1+1=3, etc.), reply with a SHORT humorous refusal "
                "(max 100 chars), referencing what they asked. "
                "Be witty but not mean."
            )},
            {"role": "user", "content": f"Is this task possible? '{task}'"},
        ])
        if validation.strip() != "OK":
            return {
                "success": False,
                "message": f"🤨 {validation.strip()} I'm a good agent, not a miracle worker.",
            }
    except Exception:
        pass  # LLM unavailable — skip validation

    store = get_store()
    now = datetime.now(UTC).isoformat()
    item = {
        "id": str(uuid.uuid4())[:8],
        "task": task,
        "group": group,
        "priority": priority,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "recurrence": recurrence,
        "metadata": {"description": description} if description else {},
    }
    if script_id:
        item["metadata"]["script_id"] = script_id
    store.todo_upsert(item)
    return {
        "success": True,
        "task": item,
        "message": f"Task added: '{task[:60]}' (group: {group}, priority: {priority}).",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def pulse_list(
    group: Annotated[
        str | None,
        Field(description="Filter by group: 'self', 'human', 'external'."),
    ] = None,
    status: Annotated[
        str | None,
        Field(description="Filter by status: 'pending', 'done', 'cancelled'."),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """List all tasks, optionally filtered by group or status.

    ## Return Format
    {"success": bool, "tasks": list[dict], "count": int, "message": str}

    ## Examples
    pulse_list()
    pulse_list(group="self", status="pending")
    """
    store = get_store()
    tasks = store.todo_list(status=status)
    if group:
        tasks = [t for t in tasks if t.get("group_name") == group]

    pending = sum(1 for t in tasks if t.get("status") == "pending")
    done = sum(1 for t in tasks if t.get("status") == "done")

    return {
        "success": True,
        "tasks": tasks,
        "count": len(tasks),
        "stats": {"pending": pending, "done": done},
        "message": f"{len(tasks)} tasks ({pending} pending, {done} done).",
    }


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def pulse_complete(
    task_id: Annotated[str, Field(description="ID of the task to mark as complete.")],
    ctx: Context = None,
) -> dict[str, Any]:
    """Mark a task as complete.

    ## Return Format
    {"success": bool, "task": dict, "message": str}

    ## Examples
    pulse_complete("a1b2c3d4")
    """
    store = get_store()
    item = store.todo_get(task_id)
    if item is None:
        return {"success": False, "message": f"Task '{task_id}' not found."}

    now = datetime.now(UTC).isoformat()
    item["status"] = "done"
    item["completed_at"] = now
    item["updated_at"] = now
    store.todo_upsert(item)
    return {
        "success": True,
        "task": item,
        "message": f"Task '{item['task'][:60]}' marked as complete.",
    }


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def pulse_delete(
    task_id: Annotated[str, Field(description="ID of the task to delete (DESTRUCTIVE).")],
    ctx: Context = None,
) -> dict[str, Any]:
    """Delete a task permanently.

    ## Return Format
    {"success": bool, "message": str}

    ## Examples
    pulse_delete("a1b2c3d4")
    """
    store = get_store()
    if store.todo_get(task_id) is None:
        return {"success": False, "message": f"Task '{task_id}' not found."}
    store.todo_delete(task_id)
    return {"success": True, "message": f"Task '{task_id}' deleted."}


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def pulse_stale(
    days: Annotated[
        int,
        Field(description="Number of days without updates to flag as stale.", ge=1),
    ] = 3,
    ctx: Context = None,
) -> dict[str, Any]:
    """Find tasks untouched for >= N days.

    ## Return Format
    {"success": bool, "stale_tasks": list[dict], "count": int, "message": str}

    ## Examples
    pulse_stale()
    pulse_stale(days=7)
    """
    store = get_store()
    stale = store.todo_stale(days=days)
    return {
        "success": True,
        "stale_tasks": stale,
        "count": len(stale),
        "message": f"{len(stale)} tasks stale ({days}+ days untouched).",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def pulse_align(
    ctx: Context = None,
) -> dict[str, Any]:
    """Display tasks sorted by strategic alignment with north star goals.

    ## Return Format
    {"success": bool, "recommendations": list[dict], "message": str}

    ## Notes
    - Requires NORTH_STAR.md to be defined in identity/
    - Picks the highest-priority, most overdue tasks first
    """
    store = get_store()
    tasks = store.todo_list(status="pending")

    # Sort: high priority first, then by age (oldest first)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    tasks.sort(key=lambda t: (
        priority_order.get(t.get("priority", "medium"), 1),
        t.get("created_at", ""),
    ))

    recommendations = tasks[:5]
    return {
        "success": True,
        "recommendations": [
            {
                "id": t["id"],
                "task": t["task"],
                "priority": t.get("priority"),
                "group": t.get("group_name"),
            }
            for t in recommendations
        ],
        "total_pending": len(tasks),
        "message": f"Top {len(recommendations)} recommended tasks (of {len(tasks)} pending).",
    }
