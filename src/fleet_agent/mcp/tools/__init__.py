"""Portmanteau imports — FastMCP registers tools at import time.

All tool modules must be imported here for FastMCP discovery during server boot.
"""

from . import (
    board,
    codegen,
    contribute,
    coworker,
    evolution_log,
    fleet_bridge,
    flowforge,
    gate,  # noqa: F401  # import registers tools
    github,
    heartbeat,
    identity,
    intel_hub,
    log_tools,  # noqa: F401  # import registers tools
    memory,
    notify,
    pulse,
    scripts,
    teleport,
    voice,
)

__all__ = [
    "flowforge",
    "pulse",
    "memory",
    "identity",
    "teleport",
    "heartbeat",
    "evolution_log",
    "fleet_bridge",
    "codegen",
    "github",
    "contribute",
    "notify",
    "coworker",
    "board",
    "intel_hub",
    "voice",
    "scripts",
]
