# Changelog

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
