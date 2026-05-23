"""Portmanteau imports — FastMCP registers tools at import time.

All tool modules must be imported here for FastMCP discovery during server boot.
"""

from . import (
    codegen,
    evolution_log,
    fleet_bridge,
    flowforge,
    github,
    heartbeat,
    identity,
    memory,
    pulse,
    teleport,
)

__all__ = [
    "flowforge", "pulse", "memory", "identity", "teleport",
    "heartbeat", "evolution_log", "fleet_bridge", "codegen", "github",
]
