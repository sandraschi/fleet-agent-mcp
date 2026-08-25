"""Agent step executor - flowforge ``agent`` nodes run cline-mcp agent_run.

The brain tier is Muse Glimmer via Ollama through cline-mcp's REST tool-call
endpoint (``POST /api/v1/tools/call`` with ``agent_run``). The node task plus
the outputs of previous steps (``node_outputs``) form the prompt; the agent's
JSON/text output is stored on the instance for the next step or gate.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


def _truncate(text: str, limit: int = 12000) -> str:
    """Bound context fed to the agent - long gather outputs are capped."""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


async def _try_call_provider(
    prompt: str, provider: str, model: str
) -> dict[str, Any]:
    url = f"{settings.cline_mcp_url}/api/v1/tools/call"
    payload = {
        "tool": "agent_run",
        "arguments": {
            "prompt": _truncate(prompt),
            "provider": provider,
            "model": model,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=settings.cline_mcp_timeout_s) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                return {"success": False, "error": f"Unexpected response: {data!r}"}
            output = data.get("outputText") or data.get("output") or data.get("text") or ""
            agent_id = data.get("agentId") or data.get("agent_id")
            success = bool(data.get("status") in (None, "completed", "success")) and not data.get("error")
            if success and output:
                return {
                    "success": True,
                    "output": str(output)[:30000],
                    "agent_id": agent_id,
                    "provider": provider,
                    "model": model,
                }
            return {"success": False, "error": str(data.get("error") or "Empty response output")}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


async def run_agent_step(
    workflow_name: str,
    node_name: str,
    task: str,
    prior_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Execute one agent step via cline-mcp ``agent_run`` with multi-provider fallback cascade.

    Returns:
        {"success": bool, "output": str, "agent_id": str|None,
         "error": str|None, "prompt_chars": int, "provider": str}
    """
    context_parts = [f"Workflow: {workflow_name}", f"Current step: {node_name}"]
    for key, value in prior_outputs.items():
        try:
            rendered = json.dumps(value, ensure_ascii=False, default=str)[:6000]
        except Exception:
            rendered = str(value)[:6000]
        context_parts.append(f"## Output of step '{key}'\n{rendered}")
    prompt = f"{task}\n\nContext from prior steps:\n" + "\n\n".join(context_parts)

    candidates = [{"provider": settings.cline_mcp_provider, "model": settings.cline_mcp_model}]
    for fb in settings.llm_fallback_providers:
        if fb not in candidates:
            candidates.append(fb)

    last_error = ""
    for cand in candidates:
        provider = cand.get("provider", "ollama")
        model = cand.get("model", "muse-glimmer")
        res = await _try_call_provider(prompt, provider, model)
        if res.get("success"):
            res["prompt_chars"] = len(prompt)
            return res
        last_error = res.get("error", "Unknown error")
        logger.warning(
            "Agent step provider '%s' (%s) failed: %s - trying fallback...",
            provider,
            model,
            last_error,
        )

    return {
        "success": False,
        "error": f"All providers failed. Last error: {last_error}",
        "prompt_chars": len(prompt),
    }
