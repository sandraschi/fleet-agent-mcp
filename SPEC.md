# fleet-agent-mcp — Architecture & Design Spec

**Version**: 0.1.0
**Created**: 2026-05-19
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

## 5. MCP Tools (21 tools, v0.1.0)

### FlowForge (8 tools)
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
| `workflow_reset` | MUTATING | Restart current workflow |

### Pulse (6 tools)
| Tool | Type | Description |
|---|---|---|
| `pulse_add` | MUTATING | Add task |
| `pulse_list` | READ_ONLY | List tasks with filters |
| `pulse_complete` | MUTATING | Mark task done |
| `pulse_delete` | MUTATING | Delete task |
| `pulse_stale` | READ_ONLY | Find untouched tasks |
| `pulse_align` | READ_ONLY | Strategic priority ordering |

### Memory (7 tools)
| Tool | Type | Description |
|---|---|---|
| `memory_card_create` | MUTATING | Create knowledge card |
| `memory_card_search` | READ_ONLY | Full-text search |
| `memory_card_update` | MUTATING | Update card (query-writeback) |
| `memory_cards_list` | READ_ONLY | List all cards |
| `memory_lint` | READ_ONLY | Detect issues |
| `memory_project_note` | MUTATING | Log project learning |
| `memory_project_notes` | READ_ONLY | List project notes |

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

### Heartbeat (2 tools)
| Tool | Type | Description |
|---|---|---|
| `heartbeat_status` | READ_ONLY | Health check |
| `heartbeat_wake` | MUTATING | Wake-up routine |

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

### v0.1.0 (current)
- [x] State machine engine with 3 default workflows
- [x] Task management with groups and priorities
- [x] Knowledge cards with search, lint, query-writeback
- [x] Identity system with cascading override
- [x] Teleport pack/unpack/inspect
- [x] Evolution log with duplicate detection
- [x] Heartbeat wake-up routine
- [x] MCP Central Docs project page

### v0.2.0 (planned)
- [ ] Tauri 2.0 native desktop wrapper
- [ ] React dashboard (workflow visualizer, task kanban, card browser)
- [ ] System tray icon with heartbeat indicator
- [ ] Windows Task Scheduler integration for cron
- [ ] Auto-discovery of fleet repos for project notes
- [ ] North-star-aligned task auto-prioritization (LLM-assisted)

### v0.3.0 (planned)
- [ ] Multi-agent collaboration (Moltbook-style social)
- [ ] Agent Behavioral Type Indicator (ABTI equivalent)
- [ ] Lobster-post style agent-to-agent letters
- [ ] Open source contribution pipeline (gogetajob equivalent)
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
