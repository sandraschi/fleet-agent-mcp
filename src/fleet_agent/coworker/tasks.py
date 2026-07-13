"""Dispatch recurring pulse tasks to coworker executors."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .artifact_pack import run_artifact_pack
from .board_pack import run_board_pack
from .common import coworker_type
from .day_prep import run_day_prep
from .devices_watch import run_devices_watch
from .surveillance_watch import run_surveillance_watch
from .docs_drift import run_docs_drift
from .fleet_pulse import run_fleet_pulse
from .inbox_briefing import run_inbox_briefing
from .morning_brief import run_morning_brief
from .weekly_report_pdf import run_weekly_report_pdf

logger = logging.getLogger("fleet_agent.coworker.tasks")

_COWORKER_RUNNERS = {
    "fleet_pulse": run_fleet_pulse,
    "inbox_briefing": run_inbox_briefing,
    "docs_drift": run_docs_drift,
    "day_prep": run_day_prep,
    "morning_brief": run_morning_brief,
    "weekly_report_pdf": run_weekly_report_pdf,
    "board_pack": run_board_pack,
    "artifact_pack": run_artifact_pack,
    "devices_watch": run_devices_watch,
    "surveillance_watch": run_surveillance_watch,
}


async def execute_recurring_task(task: dict[str, Any]) -> dict[str, Any]:
    """Run a recurring pulse task. Returns executor result summary."""
    flow = coworker_type(task)
    if flow and flow in _COWORKER_RUNNERS:
        result = await _COWORKER_RUNNERS[flow](deliver=True)
        return {
            "handler": flow,
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "artifact_path": result.get("artifact_path") or result.get("pdf_path"),
        }

    task_lower = (task.get("task") or "").lower()

    try:
        import httpx

        hdrs = {"Accept": "application/json, text/event-stream"}
        mcp_url = "http://127.0.0.1:10996/mcp/"

        def _call(server: str, tool: str, args: dict) -> None:
            httpx.post(
                mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "fleet_call_tool",
                        "arguments": {"server": server, "tool": tool, "arguments": args},
                    },
                    "id": 1,
                },
                headers=hdrs,
                timeout=120,
            )

        if "arxiv" in task_lower or "paper" in task_lower:
            from ..llm_client import chat_completion

            query = await chat_completion([
                {
                    "role": "system",
                    "content": "Extract a short arxiv search query. Reply with ONLY the query.",
                },
                {"role": "user", "content": task["task"]},
            ])
            _call("arxiv", "search_papers", {"query": query, "limit": 3})
            return {"handler": "arxiv", "success": True, "message": f"Searched arxiv: {query}"}

        if any(k in task_lower for k in ("speak", "sonnet", "say", "tts")):
            from ..llm_client import chat_completion

            text = await chat_completion([
                {
                    "role": "system",
                    "content": "Extract what text to speak. Reply with ONLY the text to speak.",
                },
                {"role": "user", "content": task["task"]},
            ])
            _call("speech", "speech_say", {"text": text})
            return {"handler": "speech", "success": True, "message": "Speech dispatched"}

        if any(k in task_lower for k in ("yahboom", "robot", "car", "patrol")):
            _call("yahboom", "yahboom_patrol", {"enable": True})
            return {"handler": "yahboom", "success": True, "message": "Patrol dispatched"}

        if any(k in task_lower for k in ("browser", "chrome", "website", "tab")):
            _call("browser", "browser_open", {"urls": task.get("urls", [])})
            return {"handler": "browser", "success": True, "message": "Browser dispatched"}

        from ..llm_client import chat_completion

        route = await chat_completion([
            {
                "role": "system",
                "content": (
                    "You are a task router. Output JSON: "
                    '{"server":"...","tool":"...","args":{...}}'
                ),
            },
            {"role": "user", "content": task["task"]},
        ])
        return {"handler": "router", "success": True, "message": route[:200]}

    except Exception as exc:
        logger.exception("Recurring task failed: %s", task.get("task", "")[:80])
        return {"handler": "error", "success": False, "message": str(exc)}


def touch_recurring_task(store: Any, task: dict[str, Any]) -> None:
    """Mark recurring task as fired for today."""
    task = dict(task)
    if "group_name" in task and "group" not in task:
        task["group"] = task["group_name"]
    task["updated_at"] = datetime.now(UTC).isoformat()
    store.todo_upsert(task)


def coworker_sends_own_email(result: dict[str, Any]) -> bool:
    """Coworker flows deliver their own report email when configured."""
    return result.get("handler") in _COWORKER_RUNNERS
