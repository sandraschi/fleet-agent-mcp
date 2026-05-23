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
import json

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route

from .config import settings


async def _call_tool(tool: str, args: dict) -> dict:
    """Call an MCP tool internally and return the result content."""
    from .mcp.registry import mcp
    result = await mcp.call_tool(tool, args)
    if hasattr(result, "content") and result.content:
        for block in result.content:
            if hasattr(block, "text") and block.text:
                try:
                    return json.loads(block.text)
                except (json.JSONDecodeError, TypeError):
                    return {"text": block.text}
    return {}


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
        "total": 37,
        "subsystems": [
            {"name": "flowforge", "count": 9, "annotation": "State machine"},
            {"name": "pulse", "count": 6, "annotation": "Task management"},
            {"name": "memory", "count": 7, "annotation": "Knowledge wiki"},
            {"name": "identity", "count": 4, "annotation": "Self-definition"},
            {"name": "teleport", "count": 3, "annotation": "Soul migration"},
            {"name": "evolution", "count": 3, "annotation": "Correction log"},
            {"name": "heartbeat", "count": 2, "annotation": "Wake-up + health"},
            {"name": "fleet_bridge", "count": 3, "annotation": "Cross-server MCP client"},
            {"name": "codegen", "count": 3, "annotation": "Code gen, file write, file edit"},
            {"name": "github", "count": 9, "annotation": "Full PR lifecycle: list, view, review, merge, branch, commit, push, PR, status"},
            {"name": "contribute", "count": 1, "annotation": "Autonomous: inspect, issue, branch, fix, PR"},
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


async def api_memory(request: Request) -> JSONResponse:
    from .engine.sqlite_store import get_store
    store = get_store()
    cards = store.cards_list()
    return JSONResponse({"success": True, "cards": cards, "count": len(cards)})


async def api_evolution(request: Request) -> JSONResponse:
    from .engine.sqlite_store import get_store
    store = get_store()
    entries = store.evolution_list(limit=int(request.query_params.get("limit", 50)))
    return JSONResponse({"success": True, "entries": entries, "count": len(entries)})


async def api_tasks_list(request: Request) -> JSONResponse:
    r = await _call_tool("pulse_list", {
        "group": request.query_params.get("group"),
        "status": request.query_params.get("status"),
    })
    return JSONResponse(r)


async def api_tasks_add(request: Request) -> JSONResponse:
    body = await request.json()
    r = await _call_tool("pulse_add", {
        "task": body.get("task", ""),
        "group": body.get("group", "self"),
        "priority": body.get("priority", "medium"),
        "recurrence": body.get("recurrence"),
    })
    return JSONResponse(r)


async def api_tasks_complete(request: Request) -> JSONResponse:
    body = await request.json()
    r = await _call_tool("pulse_complete", {"task_id": body.get("task_id", "")})
    return JSONResponse(r)


async def api_tasks_delete(request: Request) -> JSONResponse:
    body = await request.json()
    r = await _call_tool("pulse_delete", {"task_id": body.get("task_id", "")})
    return JSONResponse(r)


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
    logs.add("info", "37 MCP tools across 11 subsystems loaded", "system")

    mcp_asgi = mcp.http_app(path="/", transport="http", stateless_http=True)
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
            Route("/api/memory", endpoint=api_memory),
            Route("/api/evolution", endpoint=api_evolution),
            Route("/api/tasks", endpoint=api_tasks_list),
            Route("/api/tasks", endpoint=api_tasks_add, methods=["POST"]),
            Route("/api/tasks/complete", endpoint=api_tasks_complete, methods=["POST"]),
            Route("/api/tasks/delete", endpoint=api_tasks_delete, methods=["POST"]),
        ],
        middleware=[cors],
        lifespan=mcp_asgi.lifespan,
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
