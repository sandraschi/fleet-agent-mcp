"""Fritz's provenance-marked entries in the fleet session log.

Invokes mcp-central-docs' shared appender script as a subprocess (fleet
convention for cross-repo scripts - never import across repo boundaries).
Best-effort: a session-log write must never block or break a workflow tick.
See mcp-central-docs/operations/session-log/README.md for the convention.
"""
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_UV = r"C:\Users\sandr\.local\bin\uv.exe"
_APPENDER = Path(r"D:\Dev\repos\mcp-central-docs\scripts\session-log-append.py")


def log_workflow_completed(workflow_name: str, current_node: str) -> None:
    """Log a completed workflow run. Best-effort - swallows all errors."""
    if not _APPENDER.exists():
        return
    title = f"Workflow completed: {workflow_name}"
    body = (
        f"- Reached terminal node `{current_node}`.\n"
        f"- Autonomous run, no human involved - see fleet-agent-mcp's own "
        f"evolution log (`evolution_list()`) for any lessons recorded."
    )
    try:
        subprocess.run(
            [
                _UV, "run", "python", str(_APPENDER),
                "--agent", "Fritz",
                "--category", "heartbeat",
                "--title", title,
                "--body", body,
                "--sink", "main",
            ],
            cwd=str(_APPENDER.parent.parent),
            capture_output=True,
            timeout=15,
            check=False,
        )
    except Exception:
        logger.debug("session-log append failed (non-fatal)", exc_info=True)
