"""PyInstaller entrypoint for fleet-agent-mcp HTTP sidecar."""

from __future__ import annotations

import contextlib
import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
else:
    base = Path(__file__).resolve().parent
if str(base / "src") not in sys.path:
    sys.path.insert(0, str(base / "src"))

os.environ.setdefault("MCP_TRANSPORT", "http")

_LOG_DIR = base / "logs"


def setup_logging() -> None:
    """File logging to logs/server.log - a long-runner that writes nowhere
    is undebuggable (2026-08-05 outage: crash produced zero traces)."""
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            _LOG_DIR / "server.log",
            maxBytes=10_485_760,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(handler)
    except OSError as exc:
        logging.getLogger(__name__).warning("file logging unavailable: %s", exc)


if __name__ == "__main__":
    try:
        setup_logging()
        import uvicorn
        from fleet_agent.server import build_app

        app = build_app()

        # Start background loops (agentic + scheduler) on server startup.
        # run_server.py bypasses main() where these are normally started.
        # Wrap the existing lifespan to also start the loops.
        _orig_lifespan = app.router.lifespan_context

        @contextlib.asynccontextmanager
        async def _lifespan_with_loops(app):
            from fleet_agent.engine.agentic_loop import start_agentic_loop
            from fleet_agent.mcp.tools.notify import start_scheduler

            async with _orig_lifespan(app):
                start_scheduler()
                start_agentic_loop()
                yield

        app.router.lifespan_context = _lifespan_with_loops
        host = os.environ.get("FLEET_AGENT_HOST", "127.0.0.1")
        port = int(os.environ.get("FLEET_AGENT_PORT", os.environ.get("MCP_PORT", "10996")))
        log_level = os.environ.get("FLEET_AGENT_LOG_LEVEL", "info")
        uvicorn.run(app, host=host, port=port, log_level=log_level)
    except BaseException:
        # Never die silently: import crashes and startup failures MUST leave
        # a trace on disk (2026-08-05: ModuleNotFoundError, zero logs anywhere).
        try:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(_LOG_DIR / "crash.log", "a", encoding="utf-8") as f:
                f.write(
                    f"\n[{datetime.now(timezone.utc).isoformat()}] startup crash:\n"
                    f"{traceback.format_exc()}\n"
                )
        except OSError:
            pass
        raise
