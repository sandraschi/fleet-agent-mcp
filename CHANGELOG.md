
# Changelog

## [0.2.5] - 2026-09-08

### Added - Real cline-mcp session integration for flowforge "agent" nodes
- Full re-audit of the tool surface found `agentic.py` (`agentic_start`/`stop`/`status` - manual control of the main loop) had never been imported into `mcp/tools/__init__.py`, so those 3 tools existed with `@mcp.tool` decorators but were never actually registered. Fixed - tool count 100 → 103. Rewrote `SPEC.md` §5 completely (all 24 modules, 103 tools - the previous version covered 7 modules and was internally inconsistent even within those).
- Investigated whether Fritz actually spawns/controls/supervises sub-agents: it didn't. The flowforge "agent" node path (`agent_step.py`) called cline-mcp's one-shot `agent_run` only - no session tracking, no abort path, no cost accounting - and cline-mcp itself wasn't even running. Full writeup: new `docs/AGENT_ARCHITECTURE_AND_SAFETY.md`.
- **Built the fix**: `agent_step.py` rewritten to use cline-mcp's real session API (`POST /api/v1/agents/sessions`, `GET .../{id}`, `DELETE .../{id}`) instead of one-shot `agent_run`. Multi-tick model - starting a session and waiting for it are separate agentic-loop ticks, not one blocking call. A session running past the configured wait budget (`cline_mcp_timeout_s`, default 300s) gets a real abort (`DELETE`), not just a timeout. Failed/aborted/timed-out sessions now call `sm.failure_record()` (the pre-existing anti-spin guard) instead of silently advancing the workflow - repeated agent-step failures now visibly block the instance like every other node type already does.
- Real token/cost accounting recovered from cline-mcp's session output (`inputTokens`/`outputTokens`/`totalCost`, nested in the session's JSON output field) and logged per agent step.
- **Real bug found by testing the abort path directly**: cline-mcp's outer session `status` reads `"completed"` even for an aborted run (the SDK resolves rather than rejects on abort) - the real outcome is nested at `output.status` (`"aborted"` vs `"completed"`). Without checking that inner field, an abort would have been misread as a successful completion with empty output. Fixed.
- Verified end-to-end against a live cline-mcp instance (had to start it manually - it isn't NSSM-managed, a real remaining gap noted in the safety doc): full happy path (started → running ×N ticks → completed with real token/cost data), the abort-detection fix, session-not-found handling (cline-mcp doesn't persist sessions to disk, so a restart loses them), and terminal-node archival on completion.

## [0.2.4] - 2026-09-08

### Fixed - VRAM/stuck-loop incident (production)
- **Root cause**: a leftover `gate-test` workflow instance had been oscillating gate<->review since 2026-08-30 - `get_active_instance()` picks whatever non-archived instance was touched most recently with no completion/stall check, and each oscillation hop refreshed its own `updated_at`, so it permanently won that query. Result: `_handle_task_tick()` (the real todo-queue processor) hadn't run in over a week, and an LLM call fired on every single agentic-loop tick indefinitely, pinning the 4090's VRAM.
- **Root cause of the root cause**: the test suite had zero DB isolation - `SqliteStore()`/`StateMachine()` defaulted straight to the live production DB, no `conftest.py` existed. `test_state_machine.py`'s own `"gate-test"` gate<->review fixture was what got stuck live, since every local `pytest` run wrote real instances into `~/.fleet-agent/fleet-agent.db` and the running NSSM service ticked them for real.
- **`agentic_loop.py`**: new `_reap_if_stalled()` - force-archives any workflow instance older than 6h or with >50 history entries, checked every tick before `_handle_workflow_tick()`. Tunable via `settings.json` (`workflow_instance_max_age_hours`, `workflow_instance_max_history`). Also now calls `store.log_event(..., "blocked", reason)` on reap so it's visible to `workflow_health_watch`.
- **`tests/conftest.py`** (new file): autouse fixture redirects the SQLite store + state machine to a per-test temp DB. Verified: prod DB row count identical before/after a full test-suite run.
- Archived 275 stray non-production instances that had accumulated in the live DB since 2026-08-15 from unisolated test runs.

### Added - PC/service supervision (coworker watches)
- `gpu_vram_watch` (15m) - `nvidia-smi` + `ollama /api/ps`, escalates if VRAM stays pinned high.
- `workflow_health_watch` (30m) - early warning before the stall reaper's 6h ceiling fires.
- `task_backlog_watch` (6h) - alerts on an old/oversized pending-task backlog (the exact signal that would have caught the incident above days earlier).
- `disk_watch` (6h) - free space on `C:\`/`D:\` (immediately found `C:\` at 4.4% free).
- `coworker_execute` MCP tool's flow list now derives from `_COWORKER_RUNNERS.keys()` (single source of truth) instead of a hand-maintained `Literal` that had already drifted stale before this release (missing `scribe_watch`/`surveillance_watch`/`check_email`).

### Removed
- `activity_pulse` coworker flow (6h self-status ping to Fleet Hub) - nothing consumed it.

### Added - Contribution pipeline hardening
- `fritz_contribute()` own-repo push mode - repos owned by the authenticated `gh` user skip the fork step entirely and push directly to origin (`_own_gh_user()`).
- `gogetajob_submit()` now logs to `contribution_log` so gogetajob-driven work shows on the webapp Contributions page (previously silent).
- **Root-caused and fixed a real `gemma4:12b` timeout**: its verbose "thinking" reasoning trace pushed a real (~2000 char) fix-generation prompt past the 120s timeout, even though nothing in the codebase reads the thinking output. `llm_client.py`'s `_build_payload()` now sends `"think": false` on every Ollama request - same prompt now returns in ~2s. Confirmed harmless for non-reasoning models too.
- Extended the no-LLM fallback safety net beyond rule `S701` (previously the only rule with a fallback): `_ruff_mechanical_fix()` lets ruff apply its own `--fix` for F401/UP006 (no LLM needed), `_generic_bare_except_fix()` covers S110/E722 generically (narrows to `except Exception:`).
- `_sh()` (shared helper) now surfaces real stderr/exit-code detail on command failure instead of silently returning an empty string (kept `allow_nonzero=True` at the 4 ruff/biome call sites, where nonzero exit means "found something," not failure).
- Fixed silent clone failures in `fritz_contribute()` and `fritz_analyze_repo()` - a failed `git clone` now returns a clear error instead of continuing against a nonexistent directory.
- Landed two real, fully-automated dogfood PRs end-to-end (own repo + a purpose-built 16-bug test fixture) - no merges, per policy.

### Added - job_finder.py (new module) - real analysis replacing gogetajob's label-only classification
- `fritz_analyze_repo` - read-only: local-LLM issue tractability analysis (title+body+comments, not just labels), an age+maintainer-engagement signal gogetajob fetches but never uses, and a proactive ruff/biome scan for repos that aren't lint-instrumented (so real problems were never filed as issues at all).
- `fritz_discover_and_analyze` - gh-search-based repo crawler (topic/stars/language/activity-recency), same query shape as gogetajob's `discover`, narrow defaults (3 repos) for a reviewable single crawl.
- `fritz_act_on_finding` - explicit, separate acting step. Issue-filing always allowed; PR-attempts refused on repos we don't own. Includes a duplicate-issue courtesy check and a friendly, non-preachy issue-body generator.
- New `analysis_log` SQLite table - every decision (attempted or skipped) logged with reasoning, for postmortem review independent of `contribution_log`'s acted-on-only outcomes.
- Absolute Windows paths were leaking into filed issue titles/bodies and getting mangled (backslash escapes silently eaten) - fixed with a repo-relative path helper.
- `fritz_act_on_finding` previously always returned `success: true` regardless of whether the issue was actually filed - fixed to gate on the real outcome.

### Added - Webapp
- Tasks page: search, status/group/priority/recurring filters, sort, CSV export (was an unfiltered flat list of 100+ items).
- Automaton page: fixed a stats bug showing literal "?" (`/api/status` returns `{health: {tasks, memory_cards}}`, page was reading `/api/health`'s different shape); added search/sort/pagination to the Schedule board table.
- Sidebar: collapse toggle moved from a bottom text button to a top-header chevron (standard convention).
- Contributions/PRs page: new "Find Work" panel - Target-a-repo and Auto-crawler modes, wired to `fritz_analyze_repo`/`fritz_discover_and_analyze`/`fritz_act_on_finding` via new `/api/repo-analysis*` and `/api/analysis-log` routes.
- Evolution log: was fully built but had zero entries - now auto-logs on 3x task-failure exhaustion; seeded a real first entry from the VRAM incident itself.
- Scripts: added 5 (git-status-all-repos, stale-branch-report, gpu/vram-snapshot, contribution-opportunity-scan, evolution-log-digest).

## [0.2.3] - 2026-08-29

### Added - SFB surveillance hardening (harness-driven posting + attribution)
- **Involuntary lifecycle posting** - new `autopost_workflow_event` in `coworker/crosspost.py`, called by the flowforge engine (not by agents): `workflow_start` posts start, `workflow_next` posts completion (with gate verdict) to #sfb-work, `workflow_failure_record` posts BLOCKED instances to #sfb-alerts. Best effort, never raises into the engine. task_id = `wf:<name>:<started_at>` (unique per instance, so restarts are not muted by the 2-per-task budget).
- **Per-agent attribution** - `sfb_post` gains an `agent` parameter; Discord messages now carry a `[agent]` prefix (defaults to Fritz). VERIFIED live 2026-08-29: `[claude-desktop]` post in #sfb-thoughts, board id 20, diary 20260829T082231Z-c847f6.
- Wrapped four pre-existing E501 lines in `flowforge.py` (ruff gate was red).

## [0.2.2] — 2026-08-25

### Added — Hermes Agent Borrowings & Anti-Spin Hardening
- **Flowforge Anti-Spin Guard** — `failure_limit: 2` (default) auto-blocks workflow instances on repeated node execution failures to prevent token spin-loops. Added `workflow_failure_record` and `workflow_unblock` FastMCP tools, `heartbeat_wake` block detection, and `speechops` TTS / urgent report alerts.
- **External `SKILL.md` Importer** — `import_external_skill` FastMCP tool parses standard YAML frontmatter (`name`, `description`, `tags`) and Markdown content from OpenClaw, Anthropic, or Hermes skill files into `card_type: skill` cards.
- **Prompt Cache Alignment** — dynamic memory cards and prior node outputs injected into turn history immediately preceding execution, preserving static system prompt KV-caching.
- **Multi-Provider Fallback Cascade Engine** — `llm_fallback_providers` configuration in `Settings`; `run_agent_step` automatically cascades from primary cloud LLM to local Ollama models (`muse-glimmer` / `llama3`) on network or API failures.

## [0.2.1] — 2026-08-17

### Added — Voice Command Bus: dev commands + receivers (2026-08-17)
- **`dev_ops`** portmanteau — `start_webapp` (Fleet Starts Launcher 10791, direct-spawn fallback), `gpu_status` (nvidia-smi), `invokeai_kick`/`invokeai_status` (11154 REST), `list_webapps`, `opencode_send` (most-recent opencode session via opencode-cli-mcp)
- **`voice_assist`** portmanteau — clause chains ("set timer twenty minutes, then play desguello"): timers → speech-mcp (announces expiry), playback/search/controls → plex-mcp, book search/open → calibre-mcp (spoken verbs stripped), timer cancel
- **VLC playback** — `_plex_play` searches Plex via REST and plays the **direct part stream** (`/library/parts/.../file.mp4`, `200 video/mp4`) in VLC — no Plex client needed; HLS transcode endpoint (start.m3u8) returns 400 and is not used. `FLEET_VLC_PATH` override, auto-detect common install paths, Plex client fallback retained
- **Receiver entities** in `voice_command_bus.yaml` — opencode, dreame (new FLEET_SERVERS entry, 10894), calibre, plexy; `router.default_entity: fritz` enables bare commands
- **Router**: in-process calls for fleet-agent tools; `_bridge_summary` reads real payloads (markdown/JSON) for spoken replies; fixed `default:` YAML handler blocks (were parsed as null)
- Env: `FLEET_STARTS_UI_URL`, `FLEET_STARTS_DIR`, `FLEET_DEV_INVOKEAI_URL`

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

