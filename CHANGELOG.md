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
