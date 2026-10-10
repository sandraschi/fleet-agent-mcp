# ONBOARDING.md - fleet-agent-mcp (Fritz)

First-timer path from zero to a working Fritz. Nothing here costs money and no
online account is needed - everything runs locally (optional integrations are
marked as such).

## What you get

Fritz is a self-evolving fleet conductor: YAML workflows executed
step-by-step, a SQLite-backed task list with north-star alignment, a knowledge
wiki (memory cards), an evolution log of lessons learned, and 104 MCP tools.
Two surfaces: this repo's **webapp dashboard** (human UI) and the **MCP
server** (Claude Desktop / Cursor / Chat page backend).

## 5-minute start (source)

```powershell
git clone https://github.com/sandraschi/fleet-agent-mcp
cd fleet-agent-mcp
just bootstrap   # uv sync + pre-commit hook
.\start.ps1      # backend :10996 + webapp :10997 + browser
```

Open `http://127.0.0.1:10997/`. The sidebar health dot turns green when
`GET /api/health` answers. If port 10996 is already owned by a live instance,
the backend will not bind twice - see TROUBLESHOOTING.md (use the running one
or start a scratch copy on another port).

## 1-minute start (Claude Desktop add-on, Windows)

```powershell
irm https://github.com/sandraschi/fleet-agent-mcp/releases/latest/download/install.ps1 | iex
```

Then fully restart Claude Desktop (tray icon > Quit). Fritz appears under
Settings > Extensions. This uses the stdio entry
(`python -m fleet_agent --stdio`); the HTTP sidecar (`run_server.py`) is only
for hosted/bundled mode.

## Tour (what to click first)

1. **Dashboard** - KPIs + subsystem cards. If numbers look stale, the backend
   restarted (counts seed at startup).
2. **Tasks** - the pulse list. Add one task; complete it.
3. **Chat** - pick the Fritz personality, send "List all registered
   workflows". The `skills: N` chip shows how many learned skills were
   injected into the system prompt.
4. **Inbox** - hub mentions for entity `fritz`. Empty + "Hub unreachable" on a
   fresh box is normal (no hub at 10857 yet).
5. **Skills** - empty until you import one via the `import_external_skill`
   tool or tag a memory card `skill`.
6. **Settings** - LLM provider (Ollama `:11434` auto-detected when running).

## Where your data lives

`~/.fleet-agent/fleet-agent.db` (workflows, tasks, cards, scripts,
contributions, evolution) plus `workflows/` and `identity/` in the repo.
Delete the db to factory-reset (the server re-seeds bootstrap content).

## Optional integrations (all off by default)

- **Federation hub** (`FLEET_AGENT_FLEET_HUB_URL`, board/inbox proxy).
- **Voice Command Bus** (`POST /api/voice/intent`, speech-mcp posts here).
- **SFB crosspost** (discord-mcp URL + channel map in `config.py`).
- **Intel Reports Hub** (`intel_hub/`, port 11027 separately).

## Sanity checklist

- [ ] `Invoke-WebRequest http://127.0.0.1:10996/api/health` returns `status: ok`
- [ ] Webapp health dot green, Dashboard shows 104 tools
- [ ] `uv run pytest tests/ -q` -> 136 passed
- [ ] Chat answers via the configured provider; `skills: 0` on a fresh box

Stuck? See TROUBLESHOOTING.md, then `docs/assess-reports/` for the latest
repo health audit.
