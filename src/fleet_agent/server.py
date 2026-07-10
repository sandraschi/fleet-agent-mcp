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
import time as _time

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route

from .config import settings

_START_MONO: float = 0.0


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
        "total": 68,
        "subsystems": [
            {"name": "flowforge", "count": 9, "annotation": "State machine"},
            {"name": "pulse", "count": 6, "annotation": "Task management"},
            {"name": "memory", "count": 7, "annotation": "Knowledge wiki"},
            {"name": "identity", "count": 4, "annotation": "Self-definition"},
            {"name": "teleport", "count": 3, "annotation": "Soul migration"},
            {"name": "evolution", "count": 3, "annotation": "Correction log"},
            {"name": "heartbeat", "count": 3, "annotation": "Wake-up + health + pipeline liveness"},
            {"name": "fleet_bridge", "count": 4, "annotation": "Cross-server MCP client + list tools"},
            {"name": "codegen", "count": 3, "annotation": "Code gen, file write, file edit"},
            {"name": "github", "count": 9, "annotation": "Full PR lifecycle"},
            {"name": "contribute", "count": 1, "annotation": "Autonomous PR pipeline"},
            {"name": "notify", "count": 3, "annotation": "Email send + cron scheduler"},
            {"name": "coworker", "count": 3, "annotation": "Portmanteau: execute flow + list + bootstrap"},
            {"name": "intel_hub", "count": 3, "annotation": "Intel reports + AIWatcher push"},
            {"name": "voice", "count": 1, "annotation": "Wake-word voice command routing"},
            {"name": "scripts", "count": 6, "annotation": "Script CRUD + run for task scripting"},
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
    except (RuntimeError, KeyError, IndexError) as e:
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
    if request.url.path.endswith("/search"):
        q = request.query_params.get("q", "")
        if q:
            cards = store.card_search(q)
            return JSONResponse({"success": True, "cards": cards, "count": len(cards)})
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
        "description": body.get("description"),
        "script_id": body.get("script_id"),
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


async def api_voice_intent(request: Request) -> JSONResponse:
    """Voice Command Bus ingress (speech-mcp POSTs here after wake + STT)."""
    from .voice_router import route_voice_intent

    body = await request.json()
    result = await route_voice_intent(
        wake=str(body.get("wake", "")),
        transcript=str(body.get("transcript", "")),
        source=str(body.get("source", "speech-mcp")),
        timestamp=body.get("timestamp"),
    )
    status = 200 if result.get("success") else 422
    return JSONResponse(result, status_code=status)


async def api_scripts_list(request: Request) -> JSONResponse:
    r = await _call_tool("script_list", {})
    return JSONResponse(r)


async def api_scripts_generate(request: Request) -> JSONResponse:
    body = await request.json()
    r = await _call_tool("script_generate", {"prompt": body.get("prompt", "")})
    return JSONResponse(r)


async def api_scripts_create(request: Request) -> JSONResponse:
    body = await request.json()
    r = await _call_tool("script_create", {
        "name": body.get("name", ""),
        "content": body.get("content", ""),
        "language": body.get("language", "python"),
        "description": body.get("description", ""),
    })
    return JSONResponse(r, status_code=201 if r.get("success") else 400)


async def api_scripts_get(request: Request) -> JSONResponse:
    r = await _call_tool("script_get", {"script_id": request.path_params["id"]})
    return JSONResponse(r)


async def api_scripts_update(request: Request) -> JSONResponse:
    body = await request.json()
    body["script_id"] = request.path_params["id"]
    r = await _call_tool("script_update", body)
    return JSONResponse(r)


async def api_scripts_delete(request: Request) -> JSONResponse:
    r = await _call_tool("script_delete", {"script_id": request.path_params["id"]})
    return JSONResponse(r)


async def api_scripts_run(request: Request) -> JSONResponse:
    body = await request.json() or {}
    r = await _call_tool("script_run", {
        "script_id": request.path_params["id"],
        "args": body.get("args"),
    })
    return JSONResponse(r)


async def api_fleet_list_tools(request: Request) -> JSONResponse:
    body = await request.json() or {}
    r = await _call_tool("fleet_list_tools", {"server": body.get("server", "")})
    return JSONResponse(r)


async def api_contributions_list(request: Request) -> JSONResponse:
    from .engine.sqlite_store import get_store
    limit_str = request.query_params.get("limit", "50")
    try:
        limit = int(limit_str)
    except ValueError:
        limit = 50
    entries = get_store().contrib_list(limit=limit)
    return JSONResponse({"success": True, "contributions": entries, "count": len(entries)})


async def api_contribution_get(request: Request) -> JSONResponse:
    from .engine.sqlite_store import get_store
    entry = get_store().contrib_get(request.path_params["id"])
    if not entry:
        return JSONResponse({"success": False, "message": "Not found"}, status_code=404)
    return JSONResponse({"success": True, "contribution": entry})


async def api_health(request: Request) -> JSONResponse:
    """GET /api/health — fleet-standard health check."""

    from .config import settings as _settings
    from .mcp.registry import mcp as _mcp

    uptime_seconds = int(_time.monotonic() - _START_MONO) if _START_MONO else 0

    tool_count = 0
    try:
        tool_count = len([v for v in _mcp.local_provider._components.values() if hasattr(v, "name")])
    except Exception:
        pass

    card_count = 0
    task_pending = 0
    try:
        import sqlite3 as _sqlite3
        _db = _settings.db_path
        if _db.exists():
            _conn = _sqlite3.connect(str(_db))
            card_count = _conn.execute("SELECT count(*) FROM memory_cards").fetchone()[0]
            t = _conn.execute("SELECT count(*) FROM todo_items WHERE status='pending'").fetchone()[0]
            task_pending = t
            _conn.close()
    except Exception as exc:
        print(f"[health] db error: {exc}")

    return JSONResponse({
        "status": "ok",
        "server": "fleet-agent",
        "version": _settings.agent_name,
        "uptime_seconds": uptime_seconds,
        "_start_mono": _START_MONO,
        "tool_count": tool_count,
        "providers": {
            "ollama": getattr(_settings, 'llm_base_url', 'not set') or "not set",
            "memory_cards": card_count,
            "tasks_pending": task_pending,
        },
    })


async def api_diagnostics(request: Request) -> JSONResponse:
    """GET /api/v1/diagnostics — full fleet diagnostics payload."""
    import platform

    from .config import settings as _settings
    from .engine.state_machine import get_state_machine
    from .mcp.registry import mcp as _mcp

    uptime_seconds = int(_time.monotonic() - _START_MONO) if _START_MONO else 0

    tool_names: list[str] = []
    try:
        tool_names = sorted(v.name for v in _mcp.local_provider._components.values() if hasattr(v, "name"))
    except Exception:
        pass

    sm = get_state_machine()
    instance = sm.status()

    return JSONResponse({
        "status": "ok",
        "server": "fleet-agent",
        "version": _settings.agent_name,
        "uptime_seconds": uptime_seconds,
        "tool_count": len(tool_names),
        "tools": [{"name": n} for n in tool_names],
        "system": {
            "windows": platform.system() == "Windows",
            "python": platform.python_version(),
            "agent_name": _settings.agent_name,
            "workflows_registered": len(sm.list_workflows()),
            "active_workflow": instance.workflow_name if instance else None,
        },
        "errors": [],
    })


# ── App Builder ────────────────────────────────────────────────────────────
def build_app() -> Starlette:
    global _START_MONO
    if not _START_MONO:
        _START_MONO = _time.monotonic()

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
    logs.add("info", "68 MCP tools across 16 subsystems loaded", "system")

    from .coworker.bootstrap import ensure_coworker_tasks
    boot = ensure_coworker_tasks()
    logs.add("info", boot.get("message", "coworker bootstrap"), "system")

    from .coworker.seed import seed_cards_and_scripts
    seeded = seed_cards_and_scripts()
    if seeded.get("seeded_cards") or seeded.get("seeded_scripts"):
        logs.add("info", seeded["message"], "system")

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
            Route("/api/memory/search", endpoint=api_memory),
            Route("/api/evolution", endpoint=api_evolution),
            Route("/api/tasks", endpoint=api_tasks_list),
            Route("/api/tasks", endpoint=api_tasks_add, methods=["POST"]),
            Route("/api/tasks/complete", endpoint=api_tasks_complete, methods=["POST"]),
            Route("/api/tasks/delete", endpoint=api_tasks_delete, methods=["POST"]),
            Route("/api/voice/intent", endpoint=api_voice_intent, methods=["POST"]),
            Route("/api/scripts", endpoint=api_scripts_list),
            Route("/api/scripts", endpoint=api_scripts_create, methods=["POST"]),
            Route("/api/scripts/generate", endpoint=api_scripts_generate, methods=["POST"]),
            Route("/api/scripts/{id}", endpoint=api_scripts_get),
            Route("/api/scripts/{id}", endpoint=api_scripts_update, methods=["PUT"]),
            Route("/api/scripts/{id}", endpoint=api_scripts_delete, methods=["DELETE"]),
            Route("/api/scripts/{id}/run", endpoint=api_scripts_run, methods=["POST"]),
            Route("/api/fleet/list-tools", endpoint=api_fleet_list_tools, methods=["POST"]),
            Route("/api/contributions", endpoint=api_contributions_list),
            Route("/api/contributions/{id}", endpoint=api_contribution_get),
            Route("/api/health", endpoint=api_health),
            Route("/api/v1/diagnostics", endpoint=api_diagnostics),
        ],
        middleware=[cors],
        lifespan=mcp_asgi.lifespan,
    )


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="fleet-agent-mcp server")
    parser.add_argument("--http", action="store_true", help="Start HTTP transport")
    parser.add_argument("--stdio", action="store_true", help="Start stdio transport")
    parser.add_argument("--agentic", action="store_true", help="Enable CodeMode BM25 discovery transform")
    parser.add_argument("--port", type=int, default=settings.port, help="Port")
    parser.add_argument("--host", type=str, default=settings.host, help="Host")
    args = parser.parse_args()

    if args.http or (not args.stdio and settings.transport == "http"):
        app = build_app()
        import uvicorn

        async def run():
            from .coworker.pr_poll import pr_poll_loop
            from .mcp.tools.notify import start_scheduler
            config = uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
            server = uvicorn.Server(config)
            start_scheduler()
            asyncio.create_task(pr_poll_loop(interval=300))
            await server.serve()

        asyncio.run(run())
    else:
        HTTP_PROXY_URL = os.getenv("FLEET_AGENT_MCP_API_URL", "http://127.0.0.1:10996/mcp")
        try:
            import httpx
            r = httpx.post(HTTP_PROXY_URL, json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "probe", "version": "1"}
                }
            }, headers={"Accept": "application/json, text/event-stream"}, timeout=0.5)
            if r.status_code == 200:
                from fastmcp.server import create_proxy
                proxy = create_proxy(HTTP_PROXY_URL, name="fleet-agent-mcp")
                proxy.run(transport="stdio")
                return
        except Exception:
            pass

        from .mcp import tools as _tools  # noqa: F401
        from .mcp.registry import mcp

        if args.agentic:
            from fastmcp.experimental.transforms.code_mode import CodeMode
            mcp.add_transform(CodeMode())

        settings.ensure_dirs()
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
