"""Agent step executor - flowforge ``agent`` nodes run via cline-mcp's real
session API, not a one-shot fire-and-forget call.

Why this exists (2026-09-08): the previous version called cline-mcp's
``agent_run`` (one-shot, blocks until done or the HTTP timeout fires) with
no session tracking, no abort path, and no cost/token accounting - despite
cline-mcp itself genuinely offering ``agent_session_start/status/stop``
(real abortable sessions - confirmed from its own source, not assumed) and
returning real token usage + cost data in a completed session's output.
See ``docs/AGENT_ARCHITECTURE_AND_SAFETY.md`` for the full audit that found
this gap.

Multi-tick model: starting a session and waiting for it to finish are two
separate agentic-loop ticks, not one blocking call. A real agent run can
legitimately take minutes; blocking the whole agentic loop (and every other
task behind it) for that long doesn't scale, and gives no way to abort a
run that's gone wrong mid-flight.

- Tick where node_outputs has no session for this node: start one, record
  its session_id, do NOT advance the workflow this tick.
- Tick where a session is already running: poll status.
  - completed -> extract output + real usage/cost, advance.
  - failed/stopped -> record via sm.failure_record() (the existing anti-spin
    guard), NOT a silent advance - a broken agent step should show up as a
    real failure, not vanish. failure_record()'s own failure_limit still
    blocks the instance visibly after repeated failures, same as any other
    node type.
  - still running, under the wait budget -> no-op this tick, just report age.
  - still running, over the wait budget -> agent_session_stop() (the real
    abort), then record as a failure.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


def _truncate(text: str, limit: int = 12000) -> str:
    """Bound context fed to the agent - long gather outputs are capped."""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def _extract_usage(output_raw: str | None) -> dict[str, Any]:
    """A completed session's ``output`` field is a JSON string (the Cline
    SDK's full run result) with real token/cost data nested under ``usage``.
    Parse defensively - it's a truncated string (4000 chars) so a very long
    run's JSON can be cut mid-structure.
    """
    if not output_raw:
        return {}
    try:
        parsed = json.loads(output_raw)
    except json.JSONDecodeError:
        return {"output_text": output_raw[:2000]}
    usage = parsed.get("usage", {})
    return {
        "inner_status": parsed.get("status"),
        "output_text": str(parsed.get("outputText", ""))[:8000],
        "input_tokens": usage.get("inputTokens"),
        "output_tokens": usage.get("outputTokens"),
        "cache_read_tokens": usage.get("cacheReadTokens"),
        "total_cost": usage.get("totalCost"),
        "iterations": parsed.get("iterations"),
    }


async def _cline_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{settings.cline_mcp_url}{path}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


async def start_agent_session(prompt: str, provider: str, model: str) -> dict[str, Any]:
    """POST /api/v1/agents/sessions - returns {session_id, status} or {error}."""
    return await _cline_request(
        "POST",
        "/api/v1/agents/sessions",
        json={"prompt": _truncate(prompt), "provider": provider, "model": model},
    )


async def get_agent_session_status(session_id: str) -> dict[str, Any]:
    """GET /api/v1/agents/sessions/{id} - {id, status, prompt, startedAt, lastEvent?, output?}."""
    return await _cline_request("GET", f"/api/v1/agents/sessions/{session_id}")


async def stop_agent_session(session_id: str) -> dict[str, Any]:
    """DELETE /api/v1/agents/sessions/{id} - the real abort path."""
    return await _cline_request("DELETE", f"/api/v1/agents/sessions/{session_id}")


def _build_prompt(workflow_name: str, node_name: str, task: str, prior_outputs: dict[str, Any]) -> str:
    context_parts = [f"Workflow: {workflow_name}", f"Current step: {node_name}"]
    for key, value in prior_outputs.items():
        if key == node_name:
            continue  # this node's own (in-progress) session record, not useful context
        try:
            rendered = json.dumps(value, ensure_ascii=False, default=str)[:6000]
        except Exception:
            rendered = str(value)[:6000]
        context_parts.append(f"## Output of step '{key}'\n{rendered}")
    return f"{task}\n\nContext from prior steps:\n" + "\n\n".join(context_parts)


async def tick_agent_step(
    workflow_name: str,
    node_name: str,
    task: str,
    prior_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Advance one flowforge ``agent`` node by one agentic-loop tick.

    Returns one of:
      {"phase": "started", "session_id": str}
      {"phase": "running", "session_id": str, "age_seconds": float}
      {"phase": "completed", "session_id": str, ...usage fields...}
      {"phase": "failed", "session_id": str|None, "error": str}
      {"phase": "timeout", "session_id": str, "error": str}
    """
    existing = prior_outputs.get(node_name) or {}
    session_id = existing.get("session_id")

    if not session_id:
        prompt = _build_prompt(workflow_name, node_name, task, prior_outputs)
        result = await start_agent_session(prompt, settings.cline_mcp_provider, settings.cline_mcp_model)
        if result.get("error") or not result.get("session_id"):
            return {"phase": "failed", "session_id": None, "error": result.get("error", "no session_id returned")}
        return {
            "phase": "started",
            "session_id": result["session_id"],
            "started_at": datetime.now(UTC).isoformat(),
        }

    status = await get_agent_session_status(session_id)
    if status.get("error"):
        return {"phase": "failed", "session_id": session_id, "error": status["error"]}

    cline_status = status.get("status", "unknown")

    if cline_status == "completed":
        usage = _extract_usage(status.get("output"))
        # cline-mcp's outer session status goes "completed" even when the run
        # was aborted mid-flight - agent.run() resolves rather than rejects
        # on abort in this SDK version. The real outcome is nested at
        # output.status ("aborted" vs "completed") - confirmed by directly
        # aborting a real session and observing this exact mismatch. Treat
        # an aborted inner status as a failure, not a silent success with
        # empty output.
        if usage.get("inner_status") == "aborted":
            return {
                "phase": "failed",
                "session_id": session_id,
                "error": "session was aborted mid-run (cline-mcp reports outer status "
                "'completed' for aborted runs too - checked inner output.status)",
            }
        return {"phase": "completed", "session_id": session_id, **usage}

    if cline_status in ("failed", "stopped"):
        return {
            "phase": "failed",
            "session_id": session_id,
            "error": status.get("lastEvent", f"session {cline_status}"),
        }

    # still running - check the wait budget
    try:
        started = datetime.fromisoformat(existing.get("started_at", "").replace("Z", "+00:00"))
        age_seconds = (datetime.now(UTC) - started).total_seconds()
    except (ValueError, AttributeError):
        age_seconds = 0.0

    if age_seconds > settings.cline_mcp_timeout_s:
        await stop_agent_session(session_id)
        return {
            "phase": "timeout",
            "session_id": session_id,
            "error": f"exceeded {settings.cline_mcp_timeout_s}s wait budget - aborted",
        }

    return {
        "phase": "running",
        "session_id": session_id,
        "started_at": existing.get("started_at"),
        "age_seconds": round(age_seconds, 1),
        "last_event": status.get("lastEvent"),
    }
