# TROUBLESHOOTING.md - fleet-agent-mcp

Symptoms first, causes second. All paths are repo-root-relative unless noted.

## Port 10996 already in use (`[Errno 10048]` / bind failure)

A live backend already owns the port (steady-state Fritz instance, or a
previous `start.ps1` window). Do **not** kill what you did not start - if it
is an NSSM-managed service, restart via `sc.exe stop/start`, never taskkill.

- Check: `Invoke-WebRequest http://127.0.0.1:10996/api/health -UseBasicParsing`
  (`{"status":"ok",...}` = healthy owner).
- Find the owner: `Get-NetTCPConnection -LocalPort 10996 -State Listen`.
- To run a scratch backend alongside, use another port:
  `uv run python -m fleet_agent --http --port 13996`, then probe
  `http://127.0.0.1:13996/api/health`. Shut it down with
  `POST /api/shutdown`.

## MCPB pack fails at pollution check (`.bak` under `mcpb/`)

The pack pipeline rejects backup files under `mcpb/`. Batch-edit `.bak`
safety copies must never live there - keep them at the edited file's side
(root/src, gitignored) and delete them after the push, or before packing:
`Get-ChildItem mcpb -Filter *.bak* | Remove-Item`.

## MCPB pack fails at import isolation / AST check

You probably edited `src/` without updating the staged copy - but the pack
script wipes and re-copies `src/fleet_agent` itself, so a Stage-1-fresh
failure means the breakage is in `src/` proper: run
`uv run ruff check src/` and `uv run pytest tests/ -q` first.

## `python -m fleet_agent_mcp` says "No module named"

The shipped package dir is `fleet_agent`; `fleet_agent_mcp` is an alias shim
(`src/fleet_agent_mcp.py`, wheel `force-include` in `pyproject.toml`). After
pulling, re-sync the editable install once:
`uv sync`, then retry. (Stale-editable guard:
`mcp-central-docs/scripts/check-editable-install.ps1`.)

## Claude Desktop starts the bundle but gets HTTP, not tools

The bundle manifest must launch stdio:
`uv run --directory ${__dirname} python -m fleet_agent --stdio`.
`run_server.py` is the HTTP/PyInstaller sidecar - it must never be the
`mcp_config` entry (audit flags this as SIDECAR). Re-run
`mcp-central-docs/scripts/audit-mcpb-bundles.ps1 -Repo fleet-agent-mcp`.

## Webapp shows "Offline" but `curl /api/health` is 200

The frontend calls same-origin `/api/...` through the vite proxy; only Tauri
builds use the absolute `http://127.0.0.1:10996` URL (`__TAURI__` gate in
`webapp/src/lib/api.ts` and `webapp/src/store/connection.ts`). A browser tab
on a LAN/Tailscale hostname with a hardcoded localhost URL fails CORS while
curl succeeds. Do not "fix" this by widening CORS - fix the URL.

## CORS errors in a real browser tab

Allowed origins are explicit (`server.py: build_app()`): the vite dev port,
`tauri://localhost`, `http(s)://tauri.localhost`, plus a regex for
localhost/127.0.0.1/goliath/Tailscale hosts. `allow_origins=["*"]` is banned
(it was removed 2026-10-09) - add the concrete origin instead.

## Inbox page says "Hub unreachable"

`/api/inbox` proxies `FLEET_AGENT_FLEET_HUB_URL` (`/api/v1/inbox/poll`).
The page renders the empty state plus the hub error string - that is the
designed hub-down path, not a frontend bug. Start (or fix the URL of) the hub
at 10857 and refresh.

## Skills page is empty

No memory card is tagged/categorized `skill` yet. Import one with the
`import_external_skill` MCP tool or tag a card `skill` - the page reads live
`GET /api/skills` data, no mocks.

## `just mcpb-pack` errors about `-RepoRoot`

`scripts/mcpb-pack.ps1` is a thin shim over the central
`fleet-mcpb-pack.ps1` and passes `-RepoRoot` itself. If you bypassed the shim,
call the central script with `-RepoRoot <repo root>` explicitly.

## Tests pass locally but CI is red on Biome

Run the exact CI sequence: `bun run biome:ci` (no `--write`) and
`bun run typecheck` from `webapp/`. `bun run check` applies safe fixes and
masks remaining errors with a nonzero exit - always follow with `biome:ci`.
Line endings must be LF (`.gitattributes`); CRLF files trip the formatter.

## Frontend type error after editing `Message`/store shapes

`bun run typecheck` (`tsc --noEmit`) is the gate. Chat history persisted in
`localStorage` predates current shapes - loaders backfill (`loadMessages`
assigns missing ids); do not break that migration path when changing fields.
