"""Fritz console - minimal live surface for agent runs + comm bus (P5).

Serves a single dark HTML page on :10997 (the spec'd Fritz webapp port):
- Runs: recent workflow instances + execution log from fleet-agent.db
- Board: hub #dev-worklog / #handoffs posts (proxied with FLEET_AGENT_FLEET_HUB_TOKEN)
- Inbox: hub inbox poll for a chosen entity

Starlette + uvicorn (already fleet-agent deps). Run: python -m fleet_agent.console
"""

from __future__ import annotations

import logging
import sqlite3

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from .config import settings

logger = logging.getLogger("fleet_agent.console")

_HTML = """<!doctype html>
<html lang="en" class="dark">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fritz Console</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         background:#09090b; color:#e4e4e7; }
  header { display:flex; align-items:center; gap:12px; padding:14px 22px; border-bottom:1px solid #27272a;
           background:#0f0f12; }
  header h1 { font-size:16px; margin:0; color:#f4f4f5; }
  header span { color:#71717a; font-size:12px; }
  main { display:grid; grid-template-columns: 1fr 1fr; gap:14px; padding:16px 22px; }
  section { border:1px solid #27272a; border-radius:12px; background:#0f0f12; padding:14px; }
  section h2 { font-size:13px; color:#f59e0b; margin:0 0 10px; display:flex; justify-content:space-between; }
  .card { border:1px solid #27272a; border-radius:8px; padding:10px; margin-bottom:8px; background:#0a0a0f; }
  .meta { font-size:11px; color:#71717a; }
  .title { font-size:13px; color:#f4f4f5; margin:4px 0; }
  .body { font-size:12px; color:#a1a1aa; white-space:pre-wrap; word-break:break-word; }
  .ok { color:#22c55e; } .warn { color:#f59e0b; } .err { color:#ef4444; }
  button, input, select { background:#18181b; color:#e4e4e7; border:1px solid #3f3f46; border-radius:6px;
          padding:5px 10px; font-size:12px; }
  button { cursor:pointer; } button:hover { background:#27272a; }
  .full { grid-column: 1 / -1; }
</style>
</head>
<body>
<header>
  <h1>Fritz Console</h1><span>live agent runs + comm bus · :10997</span>
  <span style="margin-left:auto" id="clock"></span>
</header>
<main>
  <section class="full">
    <h2>Live Agent Runs <button onclick="loadRuns()">refresh</button></h2>
    <div id="runs">loading…</div>
  </section>
  <section>
    <h2>Board #dev-worklog <button onclick="loadBoard('dev-worklog')">refresh</button></h2>
    <div id="board"></div>
  </section>
  <section>
    <h2>Agent Inbox
      <span><input id="entity" value="fritz" style="width:80px">
      <button onclick="loadInbox()">poll</button></span>
    </h2>
    <div id="inbox">loading…</div>
  </section>
</main>
<script>
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function j(url, opts) { const r = await fetch(url, opts); return r.json(); }
function card(title, meta, body, cls) {
  return `<div class="card"><div class="meta">${esc(meta)}</div>` +
         (title ? `<div class="title">${esc(title)}</div>` : '') +
         `<div class="body ${cls || ''}">${esc(body)}</div></div>`;
}
async function loadRuns() {
  const d = document.getElementById('runs');
  try {
    const data = await j('/api/runs');
    d.innerHTML = data.runs.length
      ? data.runs.map(r => card(r.workflow_name, `${r.status} · ${r.started_at}`, r.node_outputs || r.current_node)).join('')
      : '<div class="card body">no runs yet</div>';
  } catch (e) { d.innerHTML = card('error', '', String(e)); }
}
async function loadBoard(channel) {
  const d = document.getElementById('board');
  try {
    const data = await j('/api/board?channel=' + channel);
    d.innerHTML = data.posts.length
      ? data.posts.map(p => card(p.title, `#${p.id} · ${p.author} · ${p.created_at}`, p.body)).join('')
      : '<div class="card body">no posts</div>';
  } catch (e) { d.innerHTML = card('error', '', String(e)); }
}
async function loadInbox() {
  const d = document.getElementById('inbox');
  try {
    const data = await j('/api/inbox?entity=' + encodeURIComponent(document.getElementById('entity').value));
    d.innerHTML = data.messages.length
      ? data.messages.map(m => card(m.subject, `${m.from_entity} → ${m.to_entity} · ${m.created_at}`, m.body)).join('')
      : '<div class="card body">no unread messages</div>';
  } catch (e) { d.innerHTML = card('error', '', String(e)); }
}
setInterval(() => { document.getElementById('clock').textContent = new Date().toLocaleString(); }, 1000);
loadRuns(); loadBoard('dev-worklog'); loadInbox();
setInterval(loadRuns, 15000);
</script>
</body></html>
"""


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


async def page(request) -> HTMLResponse:
    return HTMLResponse(_HTML)


async def api_runs(request) -> JSONResponse:
    conn = _db()
    try:
        rows = conn.execute(
            "SELECT workflow_name, current_node, started_at, updated_at, node_outputs_json"
            " FROM instances WHERE archived=0 ORDER BY started_at DESC LIMIT 12"
        ).fetchall()
        runs = []
        for r in rows:
            runs.append(
                {
                    "workflow_name": r["workflow_name"],
                    "current_node": r["current_node"],
                    "started_at": r["started_at"],
                    "status": "active",
                    "node_outputs": (r["node_outputs_json"] or "")[:200],
                }
            )
        return JSONResponse({"runs": runs})
    finally:
        conn.close()


async def _hub_get(path: str, params: dict | None = None) -> dict:
    headers = (
        {"Authorization": f"Bearer {settings.fleet_hub_token}"} if settings.fleet_hub_token else {}
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.fleet_hub_url.rstrip('/')}{path}", params=params, headers=headers
        )
        resp.raise_for_status()
        return resp.json()


async def api_board(request) -> JSONResponse:
    channel = request.query_params.get("channel", "dev-worklog")
    try:
        data = await _hub_get("/api/v1/board/posts", {"channel": channel, "limit": 15})
        return JSONResponse({"posts": data.get("posts", [])})
    except Exception as exc:
        return JSONResponse({"posts": [], "error": str(exc)})


async def api_inbox(request) -> JSONResponse:
    entity = request.query_params.get("entity", "fritz")
    try:
        data = await _hub_get("/api/v1/inbox/poll", {"entity": entity, "mark_read": False})
        return JSONResponse({"messages": data.get("messages", [])})
    except Exception as exc:
        return JSONResponse({"messages": [], "error": str(exc)})


app = Starlette(
    routes=[
        Route("/", page),
        Route("/api/runs", api_runs),
        Route("/api/board", api_board),
        Route("/api/inbox", api_inbox),
    ]
)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    port = int(settings.port) + 1  # 10996 -> 10997
    logger.info("Fritz console on :%d", port)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
