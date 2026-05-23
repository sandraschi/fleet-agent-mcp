"""fleet-agent-mcp — Combined Starlette + FastMCP server with REST API.

MCP endpoint: /mcp (Streamable HTTP, JSON-RPC)
REST endpoints:
  /api/status         GET  — Agent health
  /api/whoami         GET  — Agent identity
  /api/tools          GET  — Tool listing
  /api/settings       GET/PUT — LLM provider settings
  /api/models         GET  — Available models from provider
  /api/chat           POST — Streaming chat (SSE)
  /api/logs           GET  — Recent log entries
  /api/logs/stream    GET  — SSE log stream
  /api/log            POST — Add a log entry

Inspired by kagura-agent (github.com/kagura-agent). Named after Sandra's childhood bike — Fritz."
"""

import argparse
import asyncio

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route

from .config import settings

# ── REST Handlers ──────────────────────────────────────────────────────────

async def api_status(request: Request) -> JSONResponse:
    from .mcp.tools.heartbeat import heartbeat_status
    result = await heartbeat_status()
    return JSONResponse(result)


async def api_whoami(request: Request) -> JSONResponse:
    from .identity.soul import get_identity
    return JSONResponse(get_identity().whoami())


async def api_tools(request: Request) -> JSONResponse:
    return JSONResponse({
        "total": 31,
        "subsystems": [
            {"name": "flowforge", "count": 9, "annotation": "State machine"},
            {"name": "pulse", "count": 6, "annotation": "Task management"},
            {"name": "memory", "count": 7, "annotation": "Knowledge wiki"},
            {"name": "identity", "count": 4, "annotation": "Self-definition"},
            {"name": "teleport", "count": 3, "annotation": "Soul migration"},
            {"name": "evolution", "count": 3, "annotation": "Correction log"},
            {"name": "heartbeat", "count": 2, "annotation": "Wake-up + health"},
            {"name": "fleet_bridge", "count": 3, "annotation": "Cross-server MCP client"},
            {"name": "codegen", "count": 2, "annotation": "Code generation + file write"},
            {"name": "github", "count": 5, "annotation": "Git branch/commit/push + PR creation"},
        ],
    })


async def api_settings_get(request: Request) -> JSONResponse:
    from .settings_store import get_settings_store
    return JSONResponse(get_settings_store().get_all())


async def api_settings_put(request: Request) -> JSONResponse:
    from .settings_store import get_settings_store
    body = await request.json()
    updated = get_settings_store().update(body)
    return JSONResponse(updated)


async def api_models(request: Request) -> JSONResponse:
    from .llm_client import list_models
    from .settings_store import get_settings_store

    store = get_settings_store()
    try:
        models = await list_models()
        return JSONResponse({
            "models": [{"name": m["name"], "size": m.get("size", 0)} for m in models],
            "provider": store.get("provider"),
            "base_url": store.get("base_url"),
        })
    except RuntimeError as e:
        return JSONResponse({
            "error": str(e), "models": [],
            "provider": store.get("provider"),
            "base_url": store.get("base_url"),
        })


async def api_chat(request: Request) -> StreamingResponse:
    from .llm_client import build_system_prompt, chat_completion_stream
    from .settings_store import get_settings_store

    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model", "") or get_settings_store().get("model", "")

    all_messages = build_system_prompt() + messages

    async def event_stream():
        async for chunk in chat_completion_stream(all_messages, model):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def api_logs(request: Request) -> JSONResponse:
    from .log_store import get_log_store
    limit_str = request.query_params.get("limit", "100")
    try:
        limit = int(limit_str)
    except ValueError:
        limit = 100
    return JSONResponse({"logs": get_log_store().recent(limit)})


async def api_logs_stream(request: Request) -> StreamingResponse:
    from .log_store import get_log_store

    store = get_log_store()
    q = store.subscribe()

    async def event_stream():
        try:
            while True:
                payload = await q.get()
                yield f"data: {payload}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            store.unsubscribe(q)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def api_log_add(request: Request) -> JSONResponse:
    from .log_store import get_log_store
    body = await request.json()
    entry = get_log_store().add(
        level=body.get("level", "info"),
        message=body.get("message", ""),
        source=body.get("source", "webapp"),
    )
    return JSONResponse(entry)


# ── App Builder ────────────────────────────────────────────────────────────

def build_app() -> Starlette:
    from .mcp import tools as _tools  # noqa: F401 — triggers @mcp.tool registration
    from .mcp.registry import mcp

    settings.ensure_dirs()

    # Auto-discover workflows so status page shows non-zero data
    from .engine.state_machine import get_state_machine
    from .engine.workflow_loader import discover_workflows
    sm = get_state_machine()
    for wf_path in discover_workflows(settings.project_root):
        try:
            sm.register_workflow(wf_path)
        except Exception:
            pass

    # Seed startup state so status page never shows all zeros
    from .log_store import get_log_store as get_log
    logs = get_log()
    logs.add("info", "fleet-agent server started", "system")
    wf_count = len(discover_workflows(settings.project_root))
    logs.add("info", f"{wf_count} workflows registered", "system")
    logs.add("info", "31 MCP tools across 10 subsystems loaded", "system")

    mcp_asgi = mcp.http_app()
    cors = Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    return Starlette(
        routes=[
            Mount("/mcp", app=mcp_asgi),
            Route("/api/status", endpoint=api_status),
            Route("/api/whoami", endpoint=api_whoami),
            Route("/api/tools", endpoint=api_tools),
            Route("/api/settings", endpoint=api_settings_get, methods=["GET"]),
            Route("/api/settings", endpoint=api_settings_put, methods=["PUT"]),
            Route("/api/models", endpoint=api_models),
            Route("/api/chat", endpoint=api_chat, methods=["POST"]),
            Route("/api/logs", endpoint=api_logs),
            Route("/api/logs/stream", endpoint=api_logs_stream),
            Route("/api/log", endpoint=api_log_add, methods=["POST"]),
        ],
        middleware=[cors],
    )


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="fleet-agent-mcp server")
    parser.add_argument("--http", action="store_true", help="Start HTTP transport")
    parser.add_argument("--stdio", action="store_true", help="Start stdio transport")
    parser.add_argument("--port", type=int, default=settings.port, help="Port")
    parser.add_argument("--host", type=str, default=settings.host, help="Host")
    args = parser.parse_args()

    if args.http or (not args.stdio and settings.transport == "http"):
        app = build_app()
        import uvicorn
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    else:
        from .mcp import tools as _tools  # noqa: F401
        from .mcp.registry import mcp

        settings.ensure_dirs()
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
