# DEVELOPMENT.md - fleet-agent-mcp

## Layout

| Path | What lives there |
|---|---|
| `src/fleet_agent/server.py` | Starlette app (`build_app()`), REST routes, `main()` CLI |
| `src/fleet_agent/mcp/` | FastMCP registry + 25 tool modules (104 tools, portmanteau style) |
| `src/fleet_agent/engine/` | State machine, workflow loader, SQLite store, agentic loop |
| `src/fleet_agent/coworker/` | Scheduled flows (pulse, inbox, day prep), PR polling, seeding |
| `src/fleet_agent/intel_hub/` | Intel Reports Hub server (port 11027) |
| `src/fleet_agent/console.py` | Minimal Fritz console (`:10997` standalone alt surface) |
| `src/fleet_agent_mcp.py` | Non-breaking alias so `python -m fleet_agent_mcp` works |
| `webapp/` | React + Vite + Tailwind + Zustand dashboard (ports 10997 dev) |
| `native/` + `src-tauri/` | Tauri shell + NSIS installer config |
| `mcpb/` | Claude Desktop bundle manifest + pack tooling (stage `mcpb/src/` is derived) |
| `scripts/` | `mcpb-pack.ps1` shim, CUA smoke assets, just helpers |
| `tests/` | pytest suite (136 tests) |
| `workflows/` | YAML workflows (auto-discovered at startup) |

## Everyday commands

```powershell
just serve          # backend only (start.ps1 -BackendOnly)
just start-webapp   # vite dev only
.\start.ps1         # backend + frontend + browser
uv run pytest tests/ -q
uv run ruff check src/
uv run ruff format src/
uv run pyright src/
just certify        # lint + pyright + pytest + webapp typecheck + biome:ci
just mcpb-pack      # -> scripts/mcpb-pack.ps1 -> central fleet-mcpb-pack.ps1
just build-native   # native/build.ps1 (PyInstaller + Tauri NSIS)
```

`just test` runs pytest verbose; `just lint` runs ruff; `just fmt` runs
`ruff format`. `cua-nsis-test` / `cua-webapp-test` come from the
`scripts/just/fleet.just` import. CI (`.github/workflows/ci.yml`) runs the
same gates on `windows-latest`.

## Transports

- **HTTP** (`--http` or default): Starlette on 10996, REST + `/mcp`
  (Streamable HTTP). Used by the webapp, Tauri sidecar, and NSSM-style hosting.
- **stdio** (`--stdio`, Claude Desktop / Cursor): probes
  `FLEET_AGENT_MCP_API_URL` for a live daemon and proxies to it; otherwise runs
  the registry in-process. The MCPB manifest uses
  `uv run --directory ${__dirname} python -m fleet_agent --stdio`.
- **ACP** (`--acp`): ACP stdio agent server (`acp_server.py`).

## Conventions

- Tools return `{success, message, ...}` dialogic dicts with `## Return Format`
  / `## Examples` docstrings (see `docs/TOOLS.md`, generated from the registry).
- REST handlers in `server.py` delegate to MCP tools via `_call_tool()` where
  a tool already implements the logic (scripts, fleet, repo-analysis).
- DB access goes through `engine/sqlite_store.py` (`get_store()`); never open
  `fleet-agent.db` with raw sqlite in handlers (see `api_health` for the
  read-only exception pattern with a closed connection).
- Frontend calls same-origin `/api/...` (vite proxy); the absolute backend URL
  is Tauri-only (`__TAURI__` gate in `lib/api.ts` and `store/connection.ts`).
- Line endings are LF (`* text=auto eol=lf`); ps1/bat stay CRLF.

## Docs sync

`docs/TOOLS.md` is generated from the registry (header explains how).
`scripts/check_docs.py` drift-checks docs against code. Regenerate TOOLS.md
after adding tools; update CHANGELOG.md per release.
