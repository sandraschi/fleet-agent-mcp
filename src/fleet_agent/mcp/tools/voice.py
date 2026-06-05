"""Voice command bus — route spoken intents to fleet members."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ..registry import mcp
from ...voice_router import route_voice_intent


@mcp.tool(version="0.1.0")
async def route_voice_command(
    transcript: Annotated[str, Field(description="Full spoken command after wake word (STT text).")],
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
