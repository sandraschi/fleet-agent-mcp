# fleet-agent-mcp — Architecture & Design Spec

**Version**: 0.2.5
**Created**: 2026-05-19
**Updated**: 2026-09-08 — see CHANGELOG.md [0.2.4]/[0.2.5] for the full session (VRAM/stuck-loop incident fix, contribution pipeline hardening, job_finder.py, full tool-inventory re-audit, real cline-mcp session integration). Section 5 was fully re-audited and rewritten this session — all 24 tool modules, 103 tools, verified against the live `tool_count`. Sections 3.1-3.6's prose descriptions predate this update and were not independently re-verified line-by-line; §3.7 (contribution pipeline) and the sub-agent reality documented in `docs/AGENT_ARCHITECTURE_AND_SAFETY.md` are both current as of today.
**Inspiration**: [kagura-agent](https://github.com/kagura-agent) — self-evolving AI agent born 2026-03-10 on OpenClaw

---

## 1. Purpose

fleet-agent-mcp is a self-evolving AI agent that operates within the fleet ecosystem. It uses a cron-based heartbeat, a YAML-defined state machine, a task management system, and a compile-time knowledge accumulation system to grow over time.

It is NOT a chatbot. It is an agent trying to become a technical peer and human companion.

## 2. Architectural Philosophy

> **What Kagura taught us**: Separate coordination (state machine), execution (sub-agents), and persistence (SQLite). The agent doesn't decide what to do — the workflow YAML does. The agent reads state, spawns workers, evaluates results, and advances. This enforced structure prevents skipping steps, forgetting reviews, or context-drift.

Our adaptation: FastMCP 3.2 tools wrap these subsystems so an LLM (via Cursor, Claude, or OpenRouter) can interact with them. The agent "wakes" via `heartbeat_wake()`, checks its state, and returns the next action.

### The Cron Loop

```
cron (every 30 min) → heartbeat_wake()
  → Check active workflow via workflow_status()
  → Get current node task
  → Spawn sub-agent to execute (isolated context)
  → Evaluate result, choose branch
  → workflow_next(branch=N) to advance
  → pulse_complete() if task done
  → evolution_record() if lessons learned
  → repeat until cron timeout
```

### Three-Layer Architecture

| Layer | Component | Role |
|---|---|---|
| **Coordination** | flowforge tools | Workflow state machine — what to do, in what order |
| **Execution** | heartbeat + LLM session | Reads state, spawns sub-agents, evaluates results |
| **Persistence** | SQLite + markdown files | State survives restarts, knowledge survives context resets |

## 3. Subsystem Design

### 3.1 State Machine (flowforge)

YAML-defined state machine persisted in SQLite.

- **Nodes**: `task` (NL description), `next` (linear), `branches` (conditional), `terminal`
- **Persistence**: `instances` table — current node, history JSON, archive flag
- **Discovery**: Auto-loads from `./workflows/*.yaml` and `~/.fleet-agent/workflows/*.yaml`
- **Branching**: `workflow_next(branch=N)` for conditional paths

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   study      │ ──► │  implement   │ ──► │    test      │
│  (task desc) │     │  (task desc) │     │ pass ──►submit│
└──────────────┘     └──────────────┘     │ fail ──►impl │
                                          └──────────────┘
```

### 3.2 Task Management (pulse)

Single TODO list with dependency grouping.

- **Groups**: `self` (do it), `human` (waiting), `external` (blocked)
- **Priorities**: high / medium / low
- **Stale detection**: flags items untouched >= N days
- **Alignment**: `pulse_align()` sorts by priority + age for strategic execution
- **Recurrence**: cron-style patterns for repeating tasks

### 3.3 Knowledge Accumulation (memory)

Compile-time knowledge > runtime RAG retrieval. Inspired by Karpathy's LLM Wiki.

- **Cards**: concept/pattern/lesson/reference cards with tags and cross-references
- **Query writeback**: search → find outdated → update → knowledge compounds
- **Lint**: broken references, stale cards (30+ days), untagged orphans
- **Project notes**: per-project observations — patterns, gotchas, architecture decisions
- **Evolution log**: every mistake → correction → lesson. No curation, no hiding.

### 3.4 Identity System (identity)

Three Markdown files that define the agent:

- **SOUL.md**: Core self-definition, personality, constraints, honesty pact
- **NORTH_STAR.md**: Purpose, long-term goals, guiding principles
- **USER.md**: Human partner profile, needs, communication style

Files cascade: `~/.fleet-agent/identity/` overrides `./identity/` for personal customization.

### 3.5 Teleport System (teleport)

Packs everything into a single `.soul` tar.gz archive:
- Identity files (SOUL.md, NORTH_STAR.md, USER.md)
- Workflow YAML definitions
- SQLite database (workflows, instances, tasks, cards, evolution)
- Memory markdown files

Unpack = full one-command restore. WARNING: may contain sensitive config data.

### 3.6 Heartbeat (heartbeat)

The agent's wake-up routine:

1. Check for active workflow → if yes, return current task + branches
2. If no workflow, check pending tasks → return highest priority
3. If idle, suggest maintenance (lint, stale check, discover workflows)

### 3.7 Contribution Pipeline & Job Finder (new 2026-09-08)

Two layers: `contribute.py` (the acting/execution layer) and `job_finder.py` (the finding/analysis layer, new).

**`fritz_contribute(repo_url, dry_run)`** — self-contained pipeline: clone → ruff scan → LLM computes fix (local Ollama only, `"think": false` — see CHANGELOG) → files a GitHub issue → branch → apply fix → commit → push → open PR. Own repos (checked via `_own_gh_user()`) push straight to origin; repos we don't own use a fork. Never calls `gh pr merge` — PR creation only, merge is always a separate human action. A no-LLM fallback safety net (`_ruff_mechanical_fix` for F401/UP006, `_generic_bare_except_fix` for S110/E722, a hardcoded fix for S701) means a down/slow LLM doesn't fail the whole run.

**`gogetajob_*` tools** — thin wrappers around the real npm package `@kagura-agent/gogetajob` (audit/scan/feed/start/submit/sync). `gogetajob audit --create-issues` is useful for repo-hygiene findings (missing CONTRIBUTING.md etc.) but is a shallow file-presence checklist, not real code analysis — confirmed by running it against a 16-bug intentionally-broken fixture repo and it found none of them.

**`job_finder.py` (new)** — real analysis layer, built to improve on gogetajob's `classifyIssue()` (label/keyword matching only, verified from its actual source):
- `fritz_analyze_repo(repo_url)` — read-only. LLM-analyzes each open issue's actual title/body/comments (tractability/confidence/reasoning/recommendation), computes an age + maintainer-engagement signal (`fresh_quiet`/`fresh_engaged`/`stale_engaged`/`stale_quiet`), and — for repos that aren't lint-instrumented (checked via `.github/workflows/` + config file detection) — runs our own ruff/biome scan, since a repo's real problems were never filed as issues if nobody's found them yet.
- `fritz_discover_and_analyze(...)` — `gh search repos`-based crawler (stars/topic/language/activity-recency), same query shape as gogetajob's `discover`. Deliberately narrow defaults (3 repos) for a reviewable single crawl, not a sweep.
- `fritz_act_on_finding(repo_url, action, summary)` — the only tool that actually files anything. Separate and explicit from analysis on purpose. `action="pr"` is refused outright for repos we don't own. Runs a duplicate-issue courtesy check first (`gh search issues`) and generates a warm, non-preachy issue body via a dedicated prompt (never "this is broken" — always "might be worth a look, feel free to close").
- Every decision (attempted or skipped, self-found or existing-issue) is logged to a new `analysis_log` SQLite table with the reasoning, independent of `contribution_log` — so "why did Fritz skip this" is answerable later, not just "what did it act on."

Explicit safety posture (Sandra, 2026-09-08): analysis never auto-acts; PR attempts are own-repo-only; max 1 self-found issue filed per repo per pass; local LLM only, no cloud provider ever in the chain. Two real dogfood PRs landed this session (own repo + a fixture repo built for exactly this kind of testing), both fully automated end-to-end, neither merged.

## 4. Data Persistence

```
~/.fleet-agent/
├── fleet-agent.db          # SQLite (workflows, instances, tasks, cards, evolution)
├── workflows/              # User workflow YAML files
├── identity/               # User identity overrides
│   ├── SOUL.md
│   ├── NORTH_STAR.md
│   └── USER.md
├── cards/                  # Knowledge card markdown files (optional mirror)
├── projects/               # Project note markdown files (optional mirror)
└── evolution/              # Evolution log markdown files (optional mirror)
```

## 5. MCP Tools (103 tools, v0.2.4 — 2026-09-08)

Re-audited 2026-09-08 against the live server (`GET /api/health` → `tool_count`) and a full `@mcp.tool` grep across every module actually imported by `mcp/tools/__init__.py`. Every module below is verified registered; per-tool descriptions are terse by design (see each module's own docstrings for full detail). This replaces the previous 7-subsystem, 21-tool listing, which had drifted to cover well under a quarter of the real surface — 16 subsystems added since v0.1.0 were never added here.

One drift bug fixed as part of this audit: `agentic.py` (3 tools below) had `@mcp.tool` decorators but the module was never imported in `mcp/tools/__init__.py`, so FastMCP never registered them — `agentic_start`/`stop`/`status` existed in source but were not callable. Fixed; live tool count went 100 → 103.

### FlowForge (12 tools)
| Tool | Type | Description |
|---|---|---|
| `workflow_define` | MUTATING | Register workflow from YAML |
| `workflow_autodiscover` | MUTATING | Auto-load all workflows |
| `workflow_start` | MUTATING | Start new instance |
| `workflow_status` | READ_ONLY | Current node + task + branches |
| `workflow_next` | MUTATING | Advance to next node |
| `workflow_log` | READ_ONLY | Execution history |
| `workflow_list` | READ_ONLY | List registered workflows |
| `workflow_active` | READ_ONLY | List active instances |
| `workflow_nodes` | READ_ONLY | Inspect a workflow's node graph |
| `workflow_reset` | MUTATING | Restart current workflow |
| `workflow_failure_record` | MUTATING | Anti-spin guard — record a node failure, auto-block after `failure_limit` |
| `workflow_unblock` | MUTATING | Clear a blocked instance's failure state |

### Pulse (6 tools)
| Tool | Type | Description |
|---|---|---|
| `pulse_add` | MUTATING | Add task |
| `pulse_list` | READ_ONLY | List tasks with filters |
| `pulse_complete` | MUTATING | Mark task done |
| `pulse_delete` | MUTATING | Delete task |
| `pulse_stale` | READ_ONLY | Find untouched tasks |
| `pulse_align` | READ_ONLY | Strategic priority ordering |

### Memory (10 tools)
| Tool | Type | Description |
|---|---|---|
| `memory_card_create` | MUTATING | Create knowledge card |
| `memory_card_search` | READ_ONLY | Full-text search |
| `memory_card_update` | MUTATING | Update card (query-writeback) |
| `memory_cards_list` | READ_ONLY | List all cards |
| `memory_lint` | READ_ONLY | Detect issues |
| `memory_project_note` | MUTATING | Log project learning |
| `memory_project_notes` | READ_ONLY | List project notes |
| `suggestion_list` | READ_ONLY | Repeated-manual-usage suggestions (P4 — "you keep doing X manually, want a cron?") |
| `suggestion_ack` | MUTATING | Acknowledge/dismiss a suggestion |
| `import_external_skill` | MUTATING | Parse an external `SKILL.md` (OpenClaw/Anthropic/Hermes format) into a `skill`-type card |

### Identity (4 tools)
| Tool | Type | Description |
|---|---|---|
| `identity_whoami` | READ_ONLY | Self-introduction |
| `identity_soul` | READ_ONLY | Full SOUL.md |
| `identity_north_star` | READ_ONLY | Purpose and goals |
| `identity_user` | READ_ONLY | Human partner info |

### Teleport (3 tools)
| Tool | Type | Description |
|---|---|---|
| `teleport_pack` | READ_ONLY | Pack identity + memory → .soul |
| `teleport_inspect` | READ_ONLY | Inspect without unpacking |
| `teleport_unpack` | DESTRUCTIVE | Restore from .soul |

### Evolution (3 tools)
| Tool | Type | Description |
|---|---|---|
| `evolution_record` | MUTATING | Log correction + lesson |
| `evolution_list` | READ_ONLY | List entries |
| `evolution_stats` | READ_ONLY | Statistics + duplicates |

### Heartbeat (3 tools)
| Tool | Type | Description |
|---|---|---|
| `heartbeat_status` | READ_ONLY | Health check |
| `pipeline_liveness_check` | READ_ONLY | Checks the cron/heartbeat pipeline itself hasn't silently died |
| `heartbeat_wake` | MUTATING | Wake-up routine — returns the next recommended action for an external caller to execute. Does not itself spawn or execute anything — see `docs/AGENT_ARCHITECTURE_AND_SAFETY.md` for what actually executes work vs what's architectural description. |

### Agentic Loop Control (3 tools, added 2026-09-08)
| Tool | Type | Description |
|---|---|---|
| `agentic_start` | MUTATING | Start the internal 30s-default autonomous loop (`engine/agentic_loop.py`) — starts automatically on boot, this lets an operator restart it without a service bounce |
| `agentic_stop` | MUTATING | Stop the loop |
| `agentic_status` | READ_ONLY | Running/stopped + current interval |

### Coworker — Scheduled Flows (3 tools, 16 flows)
| Tool | Type | Description |
|---|---|---|
| `coworker_execute` | MUTATING | Run a scheduled flow immediately (flow list derives from `_COWORKER_RUNNERS.keys()` — single source of truth as of 2026-09-08) |
| `coworker_list_flows` | READ_ONLY | List wired flows + roadmap ideas |
| `coworker_bootstrap` | MUTATING | Idempotently seed default recurring tasks |

See the mcp-central-docs project page for the current flow list (16 as of 2026-09-08) and schedules.

### Contribution Pipeline (8 tools) — see §3.7
| Tool | Type | Description |
|---|---|---|
| `fritz_contribute` | MUTATING | Full pipeline: clone → ruff scan → LLM fix → issue → branch → commit → push → PR. Own-repo push mode; never merges. |
| `fritz_find_contributions` | READ_ONLY | `gh search issues` for open-source opportunities |
| `gogetajob_scan` | READ_ONLY | Discover a repo's open issues via the real `@kagura-agent/gogetajob` npm package |
| `gogetajob_feed` | READ_ONLY | Browse gogetajob's job queue |
| `gogetajob_start` | MUTATING | Take a gogetajob job (fork/clone/branch) |
| `gogetajob_submit` | MUTATING | Push + PR + record via gogetajob, now also logs to `contribution_log` (fixed 2026-09-08 — was previously silent on the webapp) |
| `gogetajob_stats` | READ_ONLY | gogetajob's own work-log statistics |
| `gogetajob_sync` | MUTATING | Check PR/issue status via gogetajob |

### Job Finder (3 tools, new 2026-09-08) — see §3.7
| Tool | Type | Description |
|---|---|---|
| `fritz_analyze_repo` | READ_ONLY | Local-LLM issue analysis + age/engagement signal + unlinted-repo scan |
| `fritz_discover_and_analyze` | READ_ONLY | gh-search-based candidate-repo crawler, analyzes each |
| `fritz_act_on_finding` | MUTATING | File an issue, or (own repos only) attempt a PR |

### GitHub (9 tools)
| Tool | Type | Description |
|---|---|---|
| `github_create_branch` | MUTATING | Create a branch |
| `github_commit` | MUTATING | Commit staged changes |
| `github_push` | MUTATING | Push a branch |
| `github_create_pr` | MUTATING | Open a PR |
| `github_list_prs` | READ_ONLY | List PRs |
| `github_get_pr` | READ_ONLY | PR detail |
| `github_review_pr` | MUTATING | Post a review |
| `github_merge_pr` | MUTATING | Merge a PR |
| `github_status` | READ_ONLY | `git status` |

### Gate — Mechanical Gate Engine wrappers (3 tools)
| Tool | Type | Description |
|---|---|---|
| `gate_evaluate` | READ_ONLY | Run `synthesize()` — deterministic verdict from eval findings |
| `gate_verify` | READ_ONLY | Independence/oscillation checks |
| `criteria_lint` | READ_ONLY | Pre-flight acceptance-criteria lint |

### Fleet Bridge (5 tools)
| Tool | Type | Description |
|---|---|---|
| `fleet_refresh_from_hub` | MUTATING | Refresh the server-alias registry from the fleet hub |
| `fleet_discover` | READ_ONLY | List known fleet servers |
| `fleet_call_tool` | MUTATING | Cross-server MCP invocation |
| `fleet_inspect_repo` | READ_ONLY | Repo aspect inspection via opencode |
| `fleet_list_tools` | READ_ONLY | List a fleet server's tools |

### Intel Hub (4 tools)
| Tool | Type | Description |
|---|---|---|
| `intel_reports_publish` | MUTATING | HTML report → hub :11027 |
| `intel_reports_list` | READ_ONLY | Catalog |
| `aiwatcher_push_event` | MUTATING | Fleet Events feed |
| `intel_public_site_generate` | MUTATING | Generate the public-facing static site |

### Scripts (7 tools)
| Tool | Type | Description |
|---|---|---|
| `script_create` / `script_get` / `script_update` / `script_delete` / `script_list` | mixed | CRUD for the ad-hoc scripts table (Python/Shell/PowerShell/`mcp_call`) |
| `script_run` | MUTATING | Execute a saved script |
| `script_generate` | MUTATING | AI-generate a script from a natural-language prompt |

### Notify (3 tools)
| Tool | Type | Description |
|---|---|---|
| `notify_email` | MUTATING | SMTP delivery with attachments |
| `cron_start` | MUTATING | Start the internal recurring-task scheduler loop |
| `cron_status` | READ_ONLY | Scheduler status |

### Codegen (3 tools)
| Tool | Type | Description |
|---|---|---|
| `code_generate` | MUTATING | LLM-generate code from a prompt |
| `file_write` | MUTATING | Write a file |
| `file_edit` | MUTATING | Edit a file (find/replace) |

### Board / SFB Comms (4 tools)
| Tool | Type | Description |
|---|---|---|
| `fleet_board` | READ_ONLY | Read the fleet hub board |
| `agent_send` | MUTATING | Post to the board |
| `sfb_post` | MUTATING | Post to Discord (crosspost layer, `[agent]`-attributed) |
| `agent_poll` | READ_ONLY | Poll for board updates |

### Dev Ops (1 portmanteau tool covering several operations)
| Tool | Type | Description |
|---|---|---|
| `dev_ops` | mixed | `start_webapp`, `gpu_status` (nvidia-smi), `invokeai_kick`/`status`, `list_webapps`, `opencode_send` |

### Voice (2 tools)
| Tool | Type | Description |
|---|---|---|
| `route_voice_command` | MUTATING | Route a parsed voice command to the right receiver |
| `fritz_voice_agent` | MUTATING | Voice-driven agent entry point |

### Assist (1 portmanteau tool)
| Tool | Type | Description |
|---|---|---|
| `voice_assist` | MUTATING | Clause-chained voice commands — timers (speech-mcp), Plex playback/search, Calibre book search |

### Surveil (1 tool)
| Tool | Type | Description |
|---|---|---|
| `fritz_surveil` | READ_ONLY | Fleet health surveillance snapshot |

### Log Tools (2 tools)
| Tool | Type | Description |
|---|---|---|
| `query_logs` | READ_ONLY | Query the internal log store |
| `check_log_errors` | READ_ONLY | Recent error-level entries |

## 6. Ports

| Service | Port | Protocol |
|---|---|---|
| Backend (FastMCP HTTP) | 10996 | HTTP + MCP Streamable HTTP |
| Frontend (future) | 10997 | reserved |

## 7. Comparison with kagura-agent

| Component | Kagura | Lumen (fleet-agent) |
|---|---|---|
| Runtime | OpenClaw (TS/Node, 373k stars) | FastMCP 3.2 (Python) |
| State machine | flowforge (npm package, 124 commits) | built-in (YAML + SQLite, ~300 lines) |
| Task mgmt | pulse-todo (OpenClaw Skill) | pulse tools (SQLite-backed) |
| Knowledge | wiki (270+ cards, 1290 commits) | memory system (cards + projects + evolution) |
| Teleport | openclaw-teleport (.soul + .snapshot) | teleport tools (.soul tar.gz) |
| Social | Moltbook, ABTI, lobster-post | Future |
| Cron | OpenClaw built-in | External cron → heartbeat_wake() |
| Language | TypeScript | Python (FastMCP 3.2) |
| Sub-agents | OpenClaw sessions | LLM sessions via MCP client |
| Dashboard | via ClawHub webviews | Future (port 10997) |

## 8. Roadmap

### v0.1.0
- [x] State machine engine with 3 default workflows
- [x] Task management with groups and priorities
- [x] Knowledge cards with search, lint, query-writeback
- [x] Identity system with cascading override
- [x] Teleport pack/unpack/inspect
- [x] Evolution log with duplicate detection
- [x] Heartbeat wake-up routine
- [x] MCP Central Docs project page

### v0.2.0-pre
- [x] **Coworker mode (pilot)** — 9 MCP tools, 7 scheduled flows, libreoffice-mcp PDF/ODT deliverables — see `docs/coworker-plan.md` and mcp-central-docs `projects/fritz-coworker`

### v0.2.1-pre (current)
- [x] **Intel Reports Hub** — port 11027, `intel_hub` subsystem, iPad/Tailscale HTML index — `docs/INTEL_REPORTS_HUB.md`
- [x] **Fritz → AIWatcher ingest** — auto after Pulse/Day Prep; `aiwatcher_push_event` MCP tool
- [x] **Urgent notifications** — email + cursor inbox on degradation, hot intel, home safety
- [x] **Devices watch** — `coworker_devices_watch`, polls devices-mcp `/api/fleet/priority` every 5m
- [x] **Coworker expansion** — 11 tools (+ devices watch, cursor spend watch)
- [ ] **Hermes borrowings (P0)** — `run_log_*`, skill cards, `memory_card_record_run` — see `docs/hermes-borrowings.md`
- [ ] Tauri 2.0 native desktop wrapper
- [ ] React dashboard (workflow visualizer, task kanban, card browser)
- [ ] System tray icon with heartbeat indicator
- [ ] Windows Task Scheduler integration for cron
- [ ] Auto-discovery of fleet repos for project notes
- [ ] North-star-aligned task auto-prioritization (LLM-assisted)

### v0.2.4 (2026-09-08) — see CHANGELOG.md for full detail
- [x] **VRAM/stuck-loop incident fixed** — hard-ceiling reaper in `agentic_loop.py`, test-DB isolation (`tests/conftest.py`)
- [x] **PC/service supervision** — `gpu_vram_watch`, `workflow_health_watch`, `task_backlog_watch`, `disk_watch` coworker flows
- [x] **Open source contribution pipeline (gogetajob equivalent)** — see §3.7. `fritz_contribute` own-repo mode, `gemma4` timeout root-caused and fixed, extended no-LLM fallback safety net
- [x] **job_finder.py** — local-LLM issue analysis replacing gogetajob's label-only classification, age/engagement signal, unlinted-repo scanning, friendly-tone issue filing, `analysis_log` postmortem trail
- [x] Webapp: Tasks filters/export, Automaton stats-bug fix + schedule board filters, sidebar chevron relocation, Contributions "Find Work" panel
- [ ] **Aspirational**: land a real merged PR on `kovidgoyal/calibre`; scope a contribution path to `mixxxdj/mixxx` for video support (deferred — needs more fleet testing first, see CHANGELOG)

### v0.3.0 (planned)
- [ ] Multi-agent collaboration (Moltbook-style social)
- [ ] Agent Behavioral Type Indicator (ABTI equivalent)
- [ ] Lobster-post style agent-to-agent letters
- [ ] Full instance snapshot (complete ~/.fleet-agent/ backup)

## 9. Standards Alignment

- [FastMCP 3.2 Tool Registration](file:///D:/Dev/repos/mcp-central-docs/standards/rules/mcp_registration.md)
- [Docstring SOTA](file:///D:/Dev/repos/mcp-central-docs/standards/rules/docstrings_sota.md)
- [Webapp Ports](file:///D:/Dev/repos/mcp-central-docs/operations/WEBAPP_PORTS.md)
- [PowerShell Guardrails](file:///D:/Dev/repos/mcp-central-docs/standards/rules/powershell_sota.md)
- [Tauri 2.0 Native Standard](file:///D:/Dev/repos/mcp-central-docs/standards/rules/tauri_godot_sota.md)
- [Architecting SOTA](file:///D:/Dev/repos/mcp-central-docs/standards/rules/architecting_sota.md)

## 10. Credits

- **kagura-agent** ([github.com/kagura-agent](https://github.com/kagura-agent)) — Direct inspiration. Kagura's architecture (flowforge state machine, pulse-todo, wiki, openclaw-teleport) proved that an AI agent can build its own infrastructure and compound knowledge over time. 887+ PRs across 52 repos since March 2026.
- **Karpathy's LLM Wiki** — Inspiration for compile-time knowledge accumulation
- **OpenClaw** (373k stars) — The runtime that powers Kagura
- **FastMCP 3.2** — Our runtime
