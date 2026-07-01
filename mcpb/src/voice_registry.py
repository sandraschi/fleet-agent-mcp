"""Load fleet voice entity/handler registry from YAML."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_REGISTRY = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "mcp-central-docs"
    / "config"
    / "voice_command_bus.yaml"
)

# When fleet-agent-mcp is not sibling to mcp-central-docs, use env or bundled copy.
_BUNDLED = Path(__file__).resolve().parent.parent.parent / "config" / "voice_command_bus.yaml"


def registry_path() -> Path:
    raw = os.environ.get("FLEET_VOICE_REGISTRY", "").strip()
    if raw:
        return Path(raw).expanduser()
    if _DEFAULT_REGISTRY.is_file():
        return _DEFAULT_REGISTRY
    return _BUNDLED


def load_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.is_file():
        return {"entities": {}, "handlers": {}, "wake_words": {}}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def resolve_entity(transcript: str, registry: dict[str, Any]) -> tuple[str | None, str]:
    """Return (entity_id, remainder) after stripping the first matching alias."""
    text = transcript.strip()
    lower = text.lower()
    entities: dict[str, Any] = registry.get("entities") or {}
    best: tuple[str | None, str, int] | None = None
    for entity_id, spec in entities.items():
        if not isinstance(spec, dict):
            continue
        for alias in spec.get("aliases") or [entity_id]:
            alias_l = str(alias).lower().strip()
            if not alias_l:
                continue
            idx = lower.find(alias_l)
            if idx < 0:
                continue
            end = idx + len(alias_l)
            remainder = (text[:idx] + text[end:]).strip(" ,.!?")
            if best is None or idx < best[2]:
                best = (entity_id, remainder, idx)
    if best is None:
        return None, text
    return best[0], best[1]
