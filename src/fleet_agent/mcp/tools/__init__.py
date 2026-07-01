"""Portmanteau imports — FastMCP registers tools at import time.

All tool modules must be imported here for FastMCP discovery during server boot.
"""

from . import (
    codegen,
    contribute,
    coworker,
    evolution_log,
    fleet_bridge,
    flowforge,
    github,
    heartbeat,
    identity,
    intel_hub,
    memory,
    notify,
    pulse,
    scripts,
    teleport,
    voice,
)

__all__ = [
    "flowforge", "pulse", "memory", "identity", "teleport",
    "heartbeat", "evolution_log", "fleet_bridge", "codegen", "github", "contribute", "notify",
    "coworker",
    "intel_hub",
    "voice",
    "scripts",
]
