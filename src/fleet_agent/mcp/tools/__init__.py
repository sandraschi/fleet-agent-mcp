"""Portmanteau imports - FastMCP registers tools at import time.

All tool modules must be imported here for FastMCP discovery during server boot.
"""

from . import (
    agentic,
    assist,
    board,
    codegen,
    contribute,
    coworker,
    dev,
    evolution_log,
    fleet_bridge,
    flowforge,
    gate,  # noqa: F401  # import registers tools
    github,
    heartbeat,
    identity,
    intel_hub,
    job_finder,
    log_tools,  # noqa: F401  # import registers tools
    memory,
    notify,
    pulse,
    scripts,
    surveil,
    teleport,
    voice,
)

__all__ = [
    "agentic",
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
    "job_finder",
    "notify",
    "coworker",
    "board",
    "surveil",
    "intel_hub",
    "voice",
    "scripts",
    "dev",
    "assist",
]
