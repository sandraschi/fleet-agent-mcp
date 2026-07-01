
## [Unreleased] — 2026-07-01

### Added — Scripting System (CRUD + Editor + Debugger + MCP Calls + AI Generation)
- **Script CRUD** — `scripts` SQLite table + MCP tools: `script_create/get/update/delete/list` with REST API
- **Script execution** — `script_run` supports Python (`exec`), Shell/PowerShell (`subprocess`), and `mcp_call` (fleet server tool calls via `fleet_call_tool`)
- **MCP Call builder** — visual server dropdown (15 fleet servers), tool dropdown (loaded dynamically), parameter list with add/remove, live JSON preview
- **AI Analysis** — optional `llm_analyze` field on `mcp_call` scripts: after tool execution, Fritz's LLM interprets the result with a custom analysis prompt
- **AI Script Generation** — `script_generate` takes a natural language prompt → LLM plans the script → auto-populates name, description, language, and content (Python, shell, or `mcp_call` JSON)
- **Frontend Scripts page** (`/scripts`) — two-panel layout: script list sidebar + editor/viewer with run/debug panel (exit code, stdout, stderr, result)
- **AI Generate UI** — 12 clickable prompt idea pills + freeform text input, auto-populates all editor fields
- **`fleet_list_tools(server)`** — new MCP tool to discover tools on any registered fleet server via Streamable HTTP
- **REST endpoints**: `GET/POST /api/scripts`, `GET/PUT/DELETE /api/scripts/{id}`, `POST /api/scripts/{id}/run`, `POST /api/scripts/generate`, `POST /api/fleet/list-tools`

### Added — Task Enhancements
- **Schedule builder** — visual pill selector (Daily/Weekdays/Weekly/Monthly/Interval/Custom) with time picker, day-of-week toggles, day-of-month selector, human-readable preview
- **Expandable tasks** — click to expand: shows description + full schedule info + created date + status
- **Proper create form** — title, description, priority select, group select, schedule builder replacing the cryptic LLM chat interface
- **Task description** — `pulse_add` now accepts a `description` param, stored in `metadata.description`, displayed on expand
- **`metadata_json` parsing** — `todo_list`/`todo_get` now parse the JSON string to a dict automatically
- **Timestamps** — task creation date shown in locale format in expanded view

### Added — Tauri NSIS Production Hardening
- **`free_port`** — multi-layer kill (Stop-Process + taskkill + Get-NetTCPConnection) + 60s polling + re-kill at 5s
- **Env vars fixed** — `backend.rs` now sets `FLEET_AGENT_PORT`/`FLEET_AGENT_HOST` (matches `config.py`/`run_server.py`), `FLEET_AGENT_TAURI=1` on child process
- **`main.rs`** — async spawn via `tauri::async_runtime::spawn`, handles `ExitRequested`
- **`tauri.conf.json`** — `beforeBuildCommand`, `beforeDevCommand`, `devUrl`, `resources/.env.example` in bundle
- **`Cargo.toml`** — `tray-icon` feature
- **`build.ps1`** — API_BASE verification, venv PyInstaller (not `uv run`), pre-clean stale exe, >=5 MB size gate, frozen binary smoke test, `.env.example` bundling
- **`run_server.py`** — added `import uvicorn`, `FLEET_AGENT_TAURI` detection, default port 10996

### Added — LLM Settings Model Listing Fix
- **Key normalization** — `list_models()` now normalizes LM Studio `id` → `name`, falls back to `size_bytes`
- **Error handling** — `api_models` catches `KeyError` + `IndexError` (LM Studio crashed with 500)
- **Auto-fetch** — settings page now auto-fetches models on mount
- **Provider status** — green/red "Connected (N models)" / "Offline" badge in settings
- **Chat streaming** — `chat_completion_stream` now supports LM Studio/OpenAI (SSE format), not just Ollama

### Added — Coworker portmanteau
- **11 tools → 1** — `coworker_fleet_pulse` through `coworker_artifact_pack` consolidated into `coworker_execute(flow="...")`, plus `coworker_list_flows` and `coworker_bootstrap`

### Fixed — Critical Bugs
- **Path traversal** — `teleport_unpack` now validates resolved paths stay inside target dir
- **Duplicate except** — `github_merge_pr` removed unreachable second `except Exception`
- **Silent errors** — `github_list_prs` returns specific error messages instead of blanket "gh CLI not available"
- **Missing docstring** — `pipeline_liveness_check` now has full docstring + Field descriptions + annotations
- **Hardcoded counts** — `server.py` tool/subysystem counts now match reality (68 tools, 16 subsystems)
- **API_BASE** — points to backend port 10996 (was 10997 — worked in dev via Vite proxy, failed in NSIS)
- **Duplicate `_build_payload`** — removed shadowed first definition in `llm_client.py`
- **Dead code** — `workflow_status` removed redundant `is_terminal` assignment

### Added — SOTA Compliance
- `prefab-ui>=0.14.0` in `pyproject.toml`
- `.env.example` at repo root
- `GET /api/health` and `GET /api/v1/diagnostics` endpoints
- `llms.txt`, `llms-full.txt`, `glama.json`
- Playwright e2e tests (`webapp/e2e/fleet-audit.spec.ts`)
- Dashboard live KPIs from `/api/health` with exponential backoff + `data-testid`
- Chat: localStorage persistence, 5 personalities, 6 example prompts, export .txt, Tauri event listener
- Ctrl+scroll zoom (`useZoom`) in root layout
- `@tauri-apps/api` in package.json for Tauri backend-status events
# Changelog

## 0.2.1-pre (2026-06-07) — Intel Hub, AIWatcher ingest, home safety watch

### Added — Intel Reports Hub (port 11027)

- **`src/fleet_agent/intel_hub/`** — shared HTML report store (`~/.fleet-intel`), index UI, publish API
- MCP: `intel_reports_publish`, `intel_reports_list`, `aiwatcher_push_event`
- Auto-start via `start.ps1` and `just intel-hub`
- Docs: [docs/INTEL_REPORTS_HUB.md](docs/INTEL_REPORTS_HUB.md); MCD: [intel-reports-hub](https://github.com/sandraschi/mcp-central-docs/blob/main/patterns/intel-reports-hub.md)

### Added — Fritz → AIWatcher ingest

- **`coworker/aiwatcher_ingest.py`** — MCP `ingest_fleet_event` + REST `POST /api/fleet/ingest` fallback
- Auto after **Fleet Pulse** and **Office Day Prep**
- Env: `FLEET_AGENT_AIWATCHER_HTTP_BASE`, `FLEET_AGENT_AIWATCHER_API_KEY`

### Added — Urgent notifications

- **`coworker/urgent_notify.py`** — email + cursor inbox when thresholds trip
- Triggers: Fleet Pulse degradation, Day Prep hot AIWatcher items, Cursor spend warn/critical, **devices_watch** new critical incidents
- Settings: `urgent_email_enabled` (default true), `urgent_email_threshold` (8.0)

### Added — Devices home-safety watch

- **`coworker/devices_watch.py`** — polls devices-mcp `GET /api/fleet/priority` every 5m
- MCP: `coworker_devices_watch`; scheduler flow `devices_watch`
- On new critical: Intel Hub publish, urgent email/inbox, AIWatcher ingest; dedup in `~/.fleet-agent/devices_watch_state.json`
- **`devices`** added to `FLEET_SERVERS` (MCP `:10716`)

### Integration

- [aiwatcher-mcp](../aiwatcher-mcp) — digest job + `POST /api/digest/send` publish to hub via `intel_hub_client.py`
- [devices-mcp](../devices-mcp) — `fritz_priority.py`, `GET /api/fleet/priority` on backend `:10717`

### Tests

- `test_intel_hub.py`, `test_aiwatcher_ingest.py`, `test_urgent_notify.py`, `test_devices_watch.py` (+ existing coworker suite)

---

## 0.2.0-pre (2026-05-30) — Coworker / Poor Man's Viktor

Pilot implementation of scheduled office + fleet flows on owned MCP (no Viktor SaaS).

### Added — Coworker subsystem (9 MCP tools)

| Tool | Schedule (default, Europe/Vienna) |
|------|-----------------------------------|
| `coworker_fleet_pulse` | Daily `07:00` |
| `coworker_inbox_briefing` | Weekdays `wd:08:00` |
| `coworker_day_prep` | Weekdays `wd:08:30` |
| `coworker_docs_drift` | Sunday `sun:10:00` |
| `coworker_weekly_report_pdf` | Friday `fri:17:00` |
| `coworker_board_pack` | Monthly `d1:09:00` |
| `coworker_artifact_pack` | Sunday `sun:18:00` |
| `coworker_list_flows` | — |
| `coworker_bootstrap` | Seeds pulse tasks on boot |

- **`src/fleet_agent/coworker/`** — flow registry, Vienna TZ recurrence, SMTP delivery with PDF attachments
- **Monthly recurrence** — `d1:09:00`, `0 9 1 * *` (day-of-month)
- **`ensure_coworker_tasks()`** — idempotent scheduler seeding; auto-starts with server
- **Office fleet_bridge aliases** — `email`, `libreoffice`, `libreoffice-ext`, `notion`, `onenote` (19 servers total)

### Integration

- [libreoffice-mcp](../libreoffice-mcp) — MD→PDF, ODT template merge, board pack, artifact pack
- MCD: [projects/fritz-coworker](https://github.com/sandraschi/mcp-central-docs/blob/main/projects/fritz-coworker/README.md), [projects/libreoffice-mcp](https://github.com/sandraschi/mcp-central-docs/blob/main/projects/libreoffice-mcp/README.md)

### Tests

- 45 pytest tests (coworker recurrence, weekly PDF, board pack, artifact pack)

---

## 0.1.0 (2026-05-23) — Inception Day

First full day of Fritz. Built from scratch in one session.

### Added

- **40 MCP tools across 12 subsystems**: flowforge, pulse, memory, identity, teleport, evolution, heartbeat, fleet_bridge, codegen, github, contribute, notify
- **codegen subsystem**: `code_generate` (LLM creates files), `file_write` (exact content), `file_edit` (surgical string replace with .bak backup + auto-verify)
- **github subsystem**: 9 tools — branch, commit, push, PR, list, view, review (approve/request-changes), merge, status
- **contribute subsystem**: `fritz_contribute` — autonomous contribution pipeline: clone → ruff → file issue → branch → fix → commit → push → PR
- **notify subsystem**: `notify_email` (SMTP), `cron_start`/`cron_status` (heartbeat scheduler)
- **Background scheduler**: 60s loop, checks recurring tasks, fires on interval ("3600", "1h") or time-of-day ("09:00", "14:30")
- **Task executor**: scheduler routes tasks to fleet servers (arxiv → search_papers, speech → speech_say, yahboom → yahboom_patrol, etc.)
- **LLM task validation**: `pulse_add` checks feasibility via LLM, refuses impossible tasks with humor
- **File `file_edit`**: surgical replace with `.bak` backup + immediate verification
- **LM Studio / OpenAI support**: `llm_client.py` now supports both Ollama and OpenAI-compatible APIs
- **MCP transport**: fixed `lifespan` propagation, `stateless_http=True` for session-free operation
- **Fleet bridge**: 14 servers (arxiv, browser, pywinauto, speech, yahboom, robofang, opencode, git-github, docs, memory, discord, plex, calibre, fleet-agent)
- **Webapp pages**: Dashboard, Chat, **Tasks** (conversational creation with LLM), **Memory**, **Evolution**, Help, Tools, Settings, Logger, Status
- **$pid bug fix**: 10 files across 7 repos renamed `$pid` → `$targetPid`
- **Contribution etiquette**: new FOSS contribution standard for AI-assisted development

### Real PRs

- discord-mcp #2: `0.0.0.0` → `127.0.0.1` (S104 security)
- discord-mcp #4: bare `except: pass` → `logger.warning` (S110)
- fritz-test #2, #4, #5, #6, #7: pipeline test PRs (codegen + merge)
- edge-bookmark-mcp-server #5: Jinja2 `autoescape=True` (S701 XSS) — awaiting review
- GrandOrgue #2497: feature request `--load <path>` CLI flag
- GrandOrgue #2498: feature request `--json-status` CLI flag

### Infrastructure

- Tauri 2.0 native wrapper for grandorgue-mcp (NSIS + MSI installers ~17 MB)
- FastMCP 3.3.1 with streamable HTTP + stateless mode
- PowerShell SOTA guardrails enshrined
- FOSS contribution etiquette documented

### Added — 2026-07-01 (Session 2: Polish & Production)
- **Uptime tracking** — `time.monotonic()` with `_START_MONO` set at `build_app()` time, stored as module global, avoiding uv build cache timestamp poisoning
- **Memory page with FTS5 search** — search bar, tag-based filtering, title extraction from markdown, category badges. New endpoint `GET /api/memory/search?q=`
- **Script execution on tasks** — `script_id` param on `pulse_add`, script selector dropdown in task create form, Run Script button in expanded task view showing stdout/stderr/exit code
- **Starter seed data** — 5 memory cards (Architecture, Fleet Servers, Coworker Flows, Script System, PR Pipeline) and 3 example MCP Call scripts auto-seeded on every boot via `coworker/seed.py`
- **Contributions page** — `/contributions` route, sidebar entry, two-panel layout with status icons (open/merged/dry_run/failed), GitHub links, step-by-step execution log, dashboard KPI
- **Contributions persistence** — `fritz_contribute` now logs results to `contribution_log` SQLite table
- **Task description** — `pulse_add` accepts `description` param, stored in `metadata.description`, displayed on task expand
- **Schedule builder UI** — visual pill selector (Daily/Weekdays/Weekly/Monthly/Interval/Custom) with time picker, day-of-week toggles, day-of-month, human-readable preview
- **Tool parameter auto-population** — `fleet_list_tools` returns parameter schemas; frontend auto-fills param keys, types, descriptions, required markers when a tool is selected
- **LLM script generation** — 12 clickable prompt idea pills + freeform text, `script_generate` MCP tool, auto-populates all editor fields
- **Health endpoint** — live tool count from `local_provider._components` (69 tools), memory card count from direct SQL, exponential backoff retry
- **Chat page** — localStorage persistence (100 msg cap), 5 personalities, 6 example prompts, Export .txt, provider status indicator, Tauri `backend-status` event listener
- **Ctrl+Scroll zoom** — `useZoom()` hook in root layout, stepped levels persisted in localStorage

