"""Agent step executor — flowforge ``agent`` nodes run cline-mcp agent_run.

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
    """Bound context fed to the agent — long gather outputs are capped."""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


async def run_agent_step(
    workflow_name: str,
    node_name: str,
    task: str,
    prior_outputs: dict[str, Any],
) -> dict[str, Any]:
    """Execute one agent step via cline-mcp ``agent_run`` (ollama/muse-glimmer).

    Returns:
        {"success": bool, "output": str, "agent_id": str|None,
         "error": str|None, "prompt_chars": int}
    """
    context_parts = [f"Workflow: {workflow_name}", f"Current step: {node_name}"]
    for key, value in prior_outputs.items():
        try:
            rendered = json.dumps(value, ensure_ascii=False, default=str)[:6000]
        except Exception:
            rendered = str(value)[:6000]
        context_parts.append(f"## Output of step '{key}'\n{rendered}")
    prompt = f"{task}\n\nContext from prior steps:\n" + "\n\n".join(context_parts)

    url = f"{settings.cline_mcp_url}/api/v1/tools/call"
    payload = {
        "tool": "agent_run",
        "arguments": {
            "prompt": _truncate(prompt),
            "provider": settings.cline_mcp_provider,
            "model": settings.cline_mcp_model,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.cline_mcp_timeout_s) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"cline-mcp returned HTTP {e.response.status_code}: {e.response.text[:300]}",
            "prompt_chars": len(prompt),
        }
    except httpx.TransportError as e:
        return {
            "success": False,
            "error": (
                f"cline-mcp unreachable at {settings.cline_mcp_url} "
                f"({type(e).__name__}: {e}). Is cline-mcp running? "
                f"Start it with 'CLINE_MCP_HTTP_PORT="
                f"{settings.cline_mcp_url.rsplit(':', 1)[-1]}' and the cline-mcp start script."
            ),
            "prompt_chars": len(prompt),
        }

    if not isinstance(data, dict):
        return {
            "success": False,
            "error": f"Unexpected cline-mcp response: {data!r}",
            "prompt_chars": len(prompt),
        }

    output = data.get("outputText") or data.get("output") or data.get("text") or ""
    agent_id = data.get("agentId") or data.get("agent_id")
    success = bool(data.get("status") in (None, "completed", "success")) and not data.get("error")

    return {
        "success": bool(success and output),
        "output": str(output)[:30000],
        "agent_id": agent_id,
        "error": str(data.get("error") or "")[:500] or None,
        "prompt_chars": len(prompt),
    }
