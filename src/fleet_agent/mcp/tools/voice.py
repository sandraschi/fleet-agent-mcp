"""Voice command bus — route spoken intents to fleet members."""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import Field

from ...voice_router import route_voice_intent
from ..registry import mcp


@mcp.tool(version="0.1.0")
async def route_voice_command(
    transcript: Annotated[
        str, Field(description="Full spoken command after wake word (STT text).")
    ],
    wake: Annotated[str, Field(description="Wake word model/id that fired.")] = "wakeywakey",
    source: Annotated[str, Field(description="Ingress component, usually speech-mcp.")] = "api",
) -> dict:
    """
    Route a voice transcript to the correct fleet MCP server (boomy, alexa, fritz, …).

    Prefer the speech-mcp always-on listener, which POSTs to /api/voice/intent automatically.
    Use this tool for manual tests or when STT was performed elsewhere.

    Example transcript: "boomy go on patrol and report what you found"
    """
    return await route_voice_intent(wake=wake, transcript=transcript, source=source)


logger = logging.getLogger("fleet_agent.tools.voice")


@mcp.tool(version="0.1.0")
async def fritz_voice_agent(
    prompt: Annotated[
        str, Field(description="Task for the Fritz agent (muse-glimmer via cline-mcp).")
    ],
    speak: Annotated[bool, Field(description="Speak the reply via speech-mcp TTS.")] = True,
) -> dict:
    """Voice-in / voice-out loop for Fritz (P5): transcript -> agent_run -> spoken reply.

    Wired as the `fritz` default handler in voice_command_bus.yaml: any spoken
    intent not matched by a keyword routes here. Runs the cline agent, then
    speaks a sanitized summary via speech-mcp `speech_say`.

    ## Return Format
    {"success": bool, "output": str, "spoken": bool}

    ## Examples
    fritz_voice_agent(prompt="give me the morning briefing")
    """
    from ...engine.agent_step import run_agent_step

    result = await run_agent_step(
        workflow_name="voice",
        node_name="voice_agent",
        task=prompt,
        prior_outputs={},
    )
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "agent run failed")}

    output = str(result.get("output", ""))[:2000]
    spoken = False
    if speak and output.strip():
        try:
            import httpx

            from ...config import settings

            resp = await httpx.AsyncClient(timeout=15).post(
                f"{settings.speech_mcp_url.rstrip('/')}/api/v1/tts",
                json={"text": output[:500], "provider": "windows"},
            )
            resp.raise_for_status()
            spoken = True
        except Exception as exc:
            logger.warning("fritz_voice_agent: speak failed: %s", exc)

    return {"success": True, "output": output, "spoken": spoken}
