"""Route SpeechIntent payloads to fleet MCP members."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .voice_registry import load_registry, resolve_entity

logger = logging.getLogger("fleet_agent.voice_router")


def _format_args(template: dict[str, Any], *, remainder: str, transcript: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in template.items():
        if isinstance(value, str):
            out[key] = value.format(remainder=remainder, transcript=transcript)
        else:
            out[key] = value
    return out


def _pick_handler(
    entity_id: str,
    remainder: str,
    transcript: str,
    registry: dict[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    handlers = (registry.get("handlers") or {}).get(entity_id)
    if not isinstance(handlers, list):
        return None
    lower = remainder.lower()
    for entry in handlers:
        if not isinstance(entry, dict):
            continue
        if "default" in entry:
            continue
        keywords = entry.get("keywords") or []
        if any(str(k).lower() in lower for k in keywords):
            tool = str(entry.get("tool", ""))
            args = _format_args(entry.get("args") or {}, remainder=remainder, transcript=transcript)
            return tool, args
    for entry in handlers:
        if isinstance(entry, dict) and "default" in entry:
            spec = entry["default"]
            if isinstance(spec, dict):
                tool = str(spec.get("tool", ""))
                args = _format_args(
                    spec.get("args") or {},
                    remainder=remainder,
                    transcript=transcript,
                )
                return tool, args
    return None


async def route_voice_intent(
    *,
    wake: str,
    transcript: str,
    source: str = "speech-mcp",
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Match entity + handler, call fleet MCP tool, return structured result."""
    from .mcp.tools.fleet_bridge import FLEET_SERVERS, fleet_call_tool

    registry = load_registry()
    text = transcript.strip()
    if not text:
        return {
            "success": False,
            "message": "Empty transcript",
            "wake": wake,
            "source": source,
        }

    entity_id, remainder = resolve_entity(text, registry)
    if not entity_id:
        return {
            "success": False,
            "message": "No fleet entity matched (say boomy, alexa, or fritz first)",
            "transcript": text,
            "wake": wake,
            "known_entities": list((registry.get("entities") or {}).keys()),
        }

    entity_spec = (registry.get("entities") or {}).get(entity_id) or {}
    server = str(entity_spec.get("server", entity_id))
    if server not in FLEET_SERVERS:
        return {
            "success": False,
            "message": f"Entity '{entity_id}' maps to unknown server '{server}'",
            "entity": entity_id,
        }

    picked = _pick_handler(entity_id, remainder, text, registry)
    if not picked:
        return {
            "success": False,
            "message": f"No handler for entity '{entity_id}'",
            "entity": entity_id,
            "remainder": remainder,
        }

    tool, args = picked
    logger.info(
        "Voice route: %s -> %s/%s args=%s",
        text[:80],
        server,
        tool,
        list(args.keys()),
    )
    result = await fleet_call_tool(server=server, tool=tool, arguments=args)
    ts = timestamp or datetime.now(UTC).isoformat()
    return {
        "success": bool(result.get("success")),
        "wake": wake,
        "transcript": text,
        "entity": entity_id,
        "server": server,
        "tool": tool,
        "arguments": args,
        "timestamp": ts,
        "source": source,
        "message": result.get("message", "Delegated"),
        "data": result.get("data", result),
    }
