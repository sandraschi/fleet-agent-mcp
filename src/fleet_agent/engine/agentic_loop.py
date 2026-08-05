"""Autonomous agent loop — picks up pending tasks and executes them.

This is the core loop that makes Fritz an autonomous agent rather than a
passive tool provider. It runs every AGENTIC_INTERVAL seconds and:

1. Checks for active workflow instances and advances them
2. Picks up ALL pending non-recurring tasks and executes them
3. Runs periodic maintenance (stale task detection, memory lint)
4. Logs every tick to the internal log store for observability
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("fleet_agent.engine.agentic_loop")

_AGENTIC_TASK: asyncio.Task | None = None


def _get_interval() -> int:
    try:
        from ..settings_store import get_settings_store

        return int(get_settings_store().get("agentic_loop_interval", 30))
    except Exception:
        return 30


async def _execute_nonrecurring_task(task: dict[str, Any]) -> dict[str, Any]:
    """Execute a non-recurring task and mark it done.

    For coworker-labelled tasks: dispatches to the registered runner.
    For script-linked tasks: runs the script.
    For arbitrary tasks: uses LLM routing then dispatches the generated plan.
    """
    from ..coworker.common import coworker_type
    from ..coworker.tasks import execute_recurring_task

    # Delegate to the same runner chain as the scheduler for coworker tasks
    flow = coworker_type(task)
    if flow:
        return await execute_recurring_task(task)

    # Script-linked tasks
    meta = task.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            meta = {}
    script_id = meta.get("script_id")
    if script_id:
        try:
            from ..mcp.tools.scripts import script_run

            return await script_run(script_id=script_id, args=meta.get("args"))
        except Exception as exc:
            return {"success": False, "message": f"Script failed: {exc}"}

    # LLM route and dispatch
    try:
        from ..llm_client import chat_completion
        from ..mcp.tools.fleet_bridge import fleet_call_tool

        route_json = await chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a task router for an MCP agent fleet. "
                        "Given a task description, respond with EXACTLY this JSON (no markdown, no extra text):\n"
                        '{"server":"<mcp-server-name>","tool":"<tool-name>","args":{...}}\n\n'
                        "Available servers and their tools:\n"
                        "- fleet-agent (this server): coworker_execute, pulse_list, script_run, memory_note, workflow_start\n"
                        "- arxiv: search_papers, get_paper_details, fetch_full_text\n"
                        "- email-mcp: list_emails, search_emails, send_email\n"
                        "- speech: speech_say\n"
                        "- yahboom: yahboom_patrol\n"
                        "- browser: browser_open\n\n"
                        "If you cannot map the task, respond with: "
                        '{"server":"fleet-agent","tool":"memory_note","args":'
                        '{"title":"Unroutable task","content":"<task>"}}'
                    ),
                },
                {"role": "user", "content": task["task"]},
            ]
        )

        route = json.loads(route_json.strip().removeprefix("```json").removesuffix("```").strip())
        server = route.get("server", "")
        tool = route.get("tool", "")
        args = route.get("args", {})

        result = await fleet_call_tool(server=server, tool=tool, arguments=args)
        return {
            "success": result.get("success", False),
            "handler": "router",
            "message": f"Dispatched {server}/{tool}",
        }

    except json.JSONDecodeError:
        return {"success": False, "message": f"LLM returned invalid JSON: {route_json[:200]}"}
    except Exception as exc:
        logger.exception("Task routing failed: %s", task.get("task", "")[:80])
        return {"success": False, "message": str(exc)}


async def _handle_workflow_tick() -> None:
    """Check for active workflow and advance it with LLM evaluation on gate nodes."""
    from ..engine.sqlite_store import get_store
    from ..log_store import get_log_store
    from ..mcp.tools.flowforge import workflow_next, workflow_status

    logs = get_log_store()
    get_store()

    status = await workflow_status()
    if not status.get("active"):
        return

    node_type = status.get("node_type", "build")
    current_node = status.get("current_node", "?")
    workflow_name = status.get("workflow", "?")

    logs.add("info", f"Workflow tick: {workflow_name} -> {current_node} ({node_type})", "agentic")

    if node_type in ("review", "gate"):
        try:
            from ..llm_client import chat_completion

            task_desc = status.get("task", "")
            criteria = status.get("branches_map", {})
            branches_str = ", ".join(criteria.keys()) if criteria else "PASS, FAIL, ITERATE"
            eval_prompt = (
                f"Review work in workflow '{workflow_name}' at node '{current_node}'.\n"
                f"Task: {task_desc}\n"
                f"Verdicts: {branches_str}\n"
                f"Reply one word."
            )
            verdict = await chat_completion(
                [
                    {
                        "role": "system",
                        "content": "Reviewer. Reply one word: PASS, FAIL, ITERATE, or BLOCKED.",
                    },
                    {"role": "user", "content": eval_prompt},
                ]
            )
            verdict = verdict.strip().upper()
            if verdict not in ("PASS", "FAIL", "ITERATE", "BLOCKED"):
                log.warning(
                    "Gate '%s': LLM returned invalid verdict '%s' — defaulting to PASS",
                    current_node,
                    verdict,
                )
                verdict = "PASS"
        except Exception as exc:
            log.error("Gate '%s': LLM call failed — defaulting to PASS: %s", current_node, exc)
            verdict = "PASS"

        logs.add("info", f"Gate '{current_node}': verdict={verdict}", "agentic")
        result = await workflow_next(verdict=verdict)
        if result.get("completed"):
            logs.add("info", f"Workflow '{workflow_name}' completed", "agentic")
    elif node_type in ("build", "execute", "discussion"):
        result = await workflow_next()
        if result.get("completed"):
            logs.add("info", f"Workflow '{workflow_name}' completed", "agentic")
        else:
            logs.add("info", f"Exec node '{current_node}' advanced", "agentic")


async def _handle_task_tick() -> None:
    """Find and execute ALL pending non-recurring tasks."""
    from ..engine.sqlite_store import get_store
    from ..log_store import get_log_store

    store = get_store()
    logs = get_log_store()

    tasks = store.todo_list(status="pending")
    priority_order = {"high": 0, "medium": 1, "low": 2}
    tasks.sort(
        key=lambda t: (
            priority_order.get(t.get("priority", "medium"), 1),
            t.get("created_at", ""),
        )
    )

    executed = 0
    for task in tasks:
        if task.get("recurrence"):
            continue
        executed += 1

        meta = task.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}
        attempt = meta.get("attempt", 0) + 1

        logs.add(
            "info",
            f"Executing task: {task['task'][:100]} (id={task['id']}, attempt={attempt})",
            "agentic",
        )
        result = await _execute_nonrecurring_task(task)
        if result.get("success"):
            store.todo_upsert(
                {
                    **task,
                    "status": "done",
                    "completed_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            logs.add("info", f"Task done: {task['task'][:100]}", "agentic")
        else:
            meta["attempt"] = attempt
            if attempt >= 3:
                store.todo_upsert(
                    {
                        **task,
                        "status": "failed",
                        "updated_at": datetime.now(UTC).isoformat(),
                        "metadata": meta,
                    }
                )
                logs.add(
                    "warning",
                    f"Task failed after {attempt} attempts: {task['task'][:100]} — {result.get('message', '')[:120]}",
                    "agentic",
                )
            else:
                store.todo_upsert(
                    {
                        **task,
                        "updated_at": datetime.now(UTC).isoformat(),
                        "metadata": meta,
                    }
                )
                logs.add(
                    "warning",
                    f"Task failed (attempt {attempt}/3): {task['task'][:100]} — {result.get('message', '')[:120]}",
                    "agentic",
                )

    if executed:
        logs.add("info", f"Executed {executed} task(s) this tick", "agentic")


async def _maintenance_tick() -> None:
    """Periodic maintenance tasks."""
    from ..engine.sqlite_store import get_store
    from ..log_store import get_log_store

    store = get_store()
    logs = get_log_store()

    tasks = store.todo_list(status="pending")
    stale = store.todo_stale(days=3)
    if stale:
        for t in stale[:3]:
            logs.add(
                "warning",
                f"Stale task: {t['task'][:80]} (updated {t.get('updated_at', '?')})",
                "agentic",
            )

    pending_count = sum(1 for t in tasks if t.get("status") == "pending")
    logs.add("info", f"Maintenance: {pending_count} pending, {len(stale)} stale", "agentic")


async def _agentic_loop() -> None:
    """Main autonomous agent loop."""
    from ..log_store import get_log_store

    logs = get_log_store()
    logs.add("info", "Agentic loop started", "agentic")

    tick = 0
    while True:
        try:
            tick += 1

            from ..engine.state_machine import get_state_machine

            sm = get_state_machine()
            instance = sm.status()

            if instance is not None:
                logs.add(
                    "info",
                    f"Workflow active: {instance.workflow_name} @ {instance.current_node}",
                    "agentic",
                )
                await _handle_workflow_tick()
            else:
                await _handle_task_tick()

            if tick % 20 == 0:
                await _maintenance_tick()

        except asyncio.CancelledError:
            logs.add("info", "Agentic loop cancelled", "agentic")
            raise
        except Exception:
            logger.exception("Agentic loop tick error")
            logs.add("error", f"Agentic loop tick {tick} failed", "agentic")

        await asyncio.sleep(_get_interval())


def start_agentic_loop() -> None:
    """Start the autonomous agent loop as a background task."""
    global _AGENTIC_TASK
    if _AGENTIC_TASK is not None and not _AGENTIC_TASK.done():
        return
    _AGENTIC_TASK = asyncio.create_task(_agentic_loop())


def stop_agentic_loop() -> None:
    """Cancel the agentic loop."""
    global _AGENTIC_TASK
    if _AGENTIC_TASK is not None and not _AGENTIC_TASK.done():
        _AGENTIC_TASK.cancel()
        _AGENTIC_TASK = None
