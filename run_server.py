"""PyInstaller entrypoint for fleet-agent-mcp HTTP sidecar."""

from __future__ import annotations

import _strptime  # noqa: F401 -- PyInstaller must bundle this eagerly
import os
import sys
import uvicorn
from pathlib import Path

if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
else:
    base = Path(__file__).resolve().parent
if str(base / "src") not in sys.path:
    sys.path.insert(0, str(base / "src"))

os.environ.setdefault("MCP_TRANSPORT", "http")
_tauri = os.environ.get("FLEET_AGENT_TAURI", "").lower() in ("1", "true", "yes")
if _tauri:
    os.environ.setdefault("FLEET_AGENT_LOG_LEVEL", "warning")

if __name__ == "__main__":
    import asyncio
    from fleet_agent.server import build_app
    from fleet_agent.mcp.tools.notify import start_scheduler
    from fleet_agent.coworker.pr_poll import pr_poll_loop

    app = build_app()

    host = os.environ.get("FLEET_AGENT_HOST", "127.0.0.1")
    port = int(os.environ.get("FLEET_AGENT_PORT", os.environ.get("MCP_PORT", "10996")))
    log_level = os.environ.get("FLEET_AGENT_LOG_LEVEL", "info")

    async def run():
        start_scheduler()
        asyncio.create_task(pr_poll_loop(interval=300))
        config = uvicorn.Config(app, host=host, port=port, log_level=log_level)
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(run())

