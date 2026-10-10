# CONFIGURATION.md - fleet-agent-mcp

All knobs for Fritz (backend + launcher). Code sources are named so you can verify.

## Environment variables (`FLEET_AGENT_` prefix, see `src/fleet_agent/config.py`)

| Variable | Default | What it does |
|---|---|---|
| `FLEET_AGENT_HOST` | `127.0.0.1` | HTTP bind address (`--host` overrides) |
| `FLEET_AGENT_PORT` | `10996` | HTTP port (`--port` overrides; `MCP_PORT` is the fallback) |
| `FLEET_AGENT_TRANSPORT` | `http` | `http` serves REST + `/mcp`; anything else starts stdio (with daemon probe) |
| `FLEET_AGENT_AGENT_NAME` | `Fritz` | Agent name shown in `/api/whoami` and the webapp |
| `FLEET_AGENT_HUMAN_NAME` | `Sandra` | Human partner name |
| `FLEET_AGENT_HEARTBEAT_ENABLED` | `false` | Cron wake-up loop |
| `FLEET_AGENT_HEARTBEAT_INTERVAL_MINUTES` | `30` | Wake-up cadence |
| `FLEET_AGENT_FLEET_HUB_URL` | `http://127.0.0.1:10857` | Federation hub for board/inbox proxy (`/api/inbox` polls it) |
| `FLEET_AGENT_FLEET_HUB_TOKEN` | _(empty)_ | Bearer token for hub board/inbox (empty = no auth header) |
| `FLEET_AGENT_MCP_API_URL` | `http://127.0.0.1:10996/mcp` | Daemon URL the stdio entry probes before falling back to local stdio |
| `FLEET_AGENT_DISCORD_MCP_URL` | `http://127.0.0.1:10756` | discord-mcp REST for SFB crossposts |
| `FLEET_AGENT_SPEECH_MCP_URL` | `http://127.0.0.1:10909` | speech-mcp REST for TTS |
| `FLEET_AGENT_VLA_NOTEBOOKS_DB` | `D:/Dev/repos/vla-mcp/data/notebooks/notebooks.sqlite3` | VLA diary source |

Copy `.env.example` to `.env` and uncomment what you need. Never commit `.env`.

## CLI flags (`python -m fleet_agent [--help]`)

`--http` / `--stdio` / `--acp` (ACP agent server) / `--agentic` (CodeMode
transform) / `--port` / `--host`. No flags + `transport=http` = HTTP mode.
`python -m fleet_agent_mcp` is an equivalent alias entry point.

## State locations

| Path | Content |
|---|---|
| `~/.fleet-agent/fleet-agent.db` | SQLite: workflows, todos, memory cards, scripts, contributions, evolution |
| `~/.fleet-agent/cards|projects|evolution|artifacts` | Created by `settings.ensure_dirs()` |
| `workflows/` | YAML workflows auto-discovered at startup |
| `identity/` | `SOUL.md`, `USER.md`, `NORTH_STAR.md` (read by identity tools) |
| `memory/` | Project observation notes |

## Launcher (`fleet-start.config.ps1`, consumed by `start.ps1`)

Backend 10996 (`module-serve`: `python -m fleet_agent --http --port 10996`),
frontend 10997 (vite), health path `/api/whoami`.
`.\start.ps1 -BackendOnly` skips the webapp; `-FrontendOnly` skips the backend;
`-NoBrowser` suppresses auto-open. Do not run a second backend while one owns
10996 - the bind fails (see TROUBLESHOOTING.md).

## Webapp settings (persisted via `GET/PUT /api/settings`)

LLM provider, base URL, and model (Settings page). The Chat page also reads
`/api/models`. Keys stay server-side; the frontend never calls providers directly.

## Ports (fleet registry)

10996 backend (REST + `/mcp`), 10997 webapp (vite dev), 11027 Intel Reports Hub.
