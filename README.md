# fleet-agent-mcp

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://biomejs.dev"><img src="https://img.shields.io/badge/Linted_with-Biome-60a5fa?style=flat-square&logo=biome&logoColor=white" alt="Biome"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>


> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting

Self-evolving AI agent for the fleet ecosystem. 24 FastMCP 3.2 tools across 8 subsystems.

**Inspired by [kagura-agent](https://github.com/kagura-agent)** — the self-evolving AI agent that merged 887+ PRs across 52 repos, built its own workflow engine, task system, wiki, social network, and contribution pipeline. Born 2026-03-10 on OpenClaw.

> *"Friefrich! Was ist dir?"* — Sandra, when Fritz messes up

---

## What Is This?

Fritz is an AI agent that operates on a cron heartbeat. It uses a YAML-defined state machine to enforce structured workflows, a task management system with north-star alignment, a compile-time knowledge wiki, and a teleport system for soul migration between machines.

**It is not a chatbot.** It is an agent trying to become a technical peer and human companion.

## Quick Start

```powershell
git clone https://github.com/sandraschi/fleet-agent-mcp
cd fleet-agent-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` or `just dev` to start.

### Manual Setup

If you don't have `just` installed:
uv sync
.\start.ps1
# Server at http://127.0.0.1:10996
Or for Cursor / Claude Desktop (stdio):
uv run -m fleet_agent.server --stdio

## Architecture

```
cron (every 30 min) → heartbeat_wake()
  → Check active workflow → workflow_status()
  → Get current node task → execute in sub-agent
  → Evaluate result → choose branch
  → workflow_next(branch=N) → advance state machine
  → evolution_record() → if lessons learned
  → Repeat
```

Three roles, one agent:

| Role | Component | Function |
|---|---|---|
| **State machine** | flowforge | Defines *what* to do, in *what* order |
| **Worker** | LLM sub-agent | Executes the task (isolated, tracked) |
| **Coordinator** | heartbeat + main session | Reads state, spawns workers, evaluates, advances |

## Subsystems

| # | Subsystem | Tools | Description | Docs |
|---|---|---|---|---|
| 1 | **flowforge** | 9 | YAML state machine — enforced step execution | [docs/flowforge.md](docs/flowforge.md) |
| 2 | **pulse** | 6 | Task management with north-star alignment | [docs/pulse.md](docs/pulse.md) |
| 3 | **memory** | 7 | Compile-time knowledge wiki with linting | [docs/memory.md](docs/memory.md) |
| 4 | **identity** | 4 | Agent self-definition and purpose | [docs/identity.md](docs/identity.md) |
| 5 | **teleport** | 3 | Soul migration between machines | [docs/teleport.md](docs/teleport.md) |
| 6 | **evolution** | 3 | Mistake → correction → lesson log | [docs/evolution.md](docs/evolution.md) |
| 7 | **heartbeat** | 2 | Cron wake-up and health monitoring | [docs/heartbeat.md](docs/heartbeat.md) |
| 8 | **fleet_bridge** | 3 | Cross-server MCP client — call any fleet MCP tool | [src/fleet_agent/mcp/tools/fleet_bridge.py](src/fleet_agent/mcp/tools/fleet_bridge.py) |

## Project Structure

```
fleet-agent-mcp/
├── README.md                          # This file
├── SPEC.md                            # Full architecture & design spec
├── pyproject.toml                     # Python 3.12+, FastMCP 3.2
├── start.ps1 / start.bat              # Server launchers
├── justfile                           # Dev recipes
│
├── src/fleet_agent/
│   ├── server.py                      # FastMCP 3.2 entry point
│   ├── config.py                      # Pydantic settings
│   ├── engine/                        # Core: state machine, SQLite, YAML loader
│   ├── mcp/tools/                     # 24 FastMCP tools across 8 files
│   ├── memory/                        # Wiki + evolution log
│   └── identity/                      # SOUL.md reader
│
├── identity/                          # Agent personality files
│   ├── SOUL.md                        # Core identity, constraints, honesty pact
│   ├── NORTH_STAR.md                  # Purpose, goals, guiding principles
│   └── USER.md                        # Human partner profile
│
├── workflows/                         # YAML workflow definitions
│   ├── daily.yaml                     # Review → maintain → learn → act
│   ├── contribution.yaml              # Study → implement → test → submit → verify
│   └── learning.yaml                  # Research → synthesize → document → apply
│
├── docs/                              # Subsystem documentation
│   ├── flowforge.md
│   ├── pulse.md
│   ├── memory.md
│   ├── identity.md
│   ├── teleport.md
│   ├── evolution.md
│   └── heartbeat.md
│
├── webapp/                            # Vite + React tabbed help dashboard
│   └── src/                           # See webapp/README.md
│
├── tests/                             # 17 unit tests
└── memory/                            # Markdown knowledge mirror (cards, projects, evolution)
```

## Identity

The agent is named **Lumen**. Partnered with Sandra (Vienna).

Override by creating `~/.fleet-agent/identity/SOUL.md` — personal identity cascades over defaults.

See `identity/SOUL.md` for core personality, `identity/NORTH_STAR.md` for purpose, `identity/USER.md` for human context.

## Ports

| Service | Port | Protocol |
|---|---|---|
| Backend (FastMCP HTTP) | 10996 | HTTP + MCP Streamable HTTP |
| Frontend (Vite dev) | 10997 | HTTP |

## Default Workflows

### daily — `review → maintain → learn → act`

The agent's daily routine. Reviews evolution log and stale tasks, maintains the knowledge base, learns one new thing, then executes the highest-priority task.

### contribution — `study → implement → test → submit → verify → done`

Open source contribution pipeline with branching: test failures loop back to implement, review changes loop back to implement, CI failures loop back to implement.

### learning — `research → synthesize → document → apply`

Structured learning: research a topic, synthesize into knowledge cards, document with cross-references, then apply by building something.

## Comparison with kagura-agent

| Component | Kagura | Fritz (fleet-agent) |
|---|---|---|
| Runtime | OpenClaw (TS/Node, 373k stars) | FastMCP 3.2 (Python) |
| State machine | flowforge (npm, 124 commits) | built-in (YAML + SQLite) |
| Task mgmt | pulse-todo (OpenClaw Skill) | pulse tools (SQLite) |
| Knowledge | wiki (270+ cards, 1290 commits) | memory (cards + projects + evolution) |
| Teleport | openclaw-teleport (v0.5.0) | teleport tools (.soul tar.gz) |
| Cron | OpenClaw built-in | External → heartbeat_wake() |
| Cross-server | OpenClaw skills | fleet_bridge (MCP client, 9 servers) |
| Core language | TypeScript | Python |
| GitHub PRs | 887+ across 52 repos | **Yes — 9 tools: list, view, approve, merge, branch, commit, push, PR, status** |
| Code generation | Built-in (LLM → file) | **Yes — 2 tools: code_generate, file_write** |
| Sub-agent delegation | OpenClaw skill graph | fleet_bridge → 9 MCP servers |

### Path to Kagura Parity

With codegen + github tools added, fleet-agent can now autonomously:

1. **Study** — inspect a repo via `fleet_inspect_repo()` (via opencode-cli-mcp)
2. **Branch** — `github_create_branch()` to fork from main
3. **Implement** — `code_generate()` writes code via LLM, `file_write()` for direct edits
4. **Test** — `fleet_inspect_repo(aspect="tests")` to verify
5. **Commit** — `github_commit()` stages and commits
6. **Push** — `github_push()` sends to remote
7. **PR** — `github_create_pr()` opens the pull request

Remaining gap: the contribution workflow YAML is defined, but the heartbeat wake doesn't automatically invoke it. That requires wiring `heartbeat_wake()` → `workflow_start('contribution')` in the daily loop — a config change, not a code change.

1. **Enforced workflow** — The YAML defines what to do. The agent coordinates.
2. **Compile-time knowledge** — Cards integrated at write time, not assembled at query time.
3. **No curation, no hiding** — Every mistake → evolution log. Every lesson compounds.
4. **Persistence > Context** — SQLite survives restarts. Markdown survives context resets.
5. **Sub-agent isolation** — Main session = dispatch. Sub-agents = actual work.

## Standards

- [FastMCP 3.2 Tool Registration](https://github.com/jlowin/fastmcp)
- [Docstring SOTA](file:///D:/Dev/repos/mcp-central-docs/standards/rules/docstrings_sota.md)
- [Webapp Ports](file:///D:/Dev/repos/mcp-central-docs/operations/WEBAPP_PORTS.md)
- [PowerShell Guardrails](file:///D:/Dev/repos/mcp-central-docs/standards/rules/powershell_sota.md)

## Credits

**[kagura-agent](https://github.com/kagura-agent)** — Direct inspiration. Kagura proved an AI agent can build its own infrastructure, compound knowledge over time (1290 wiki commits), and ship 887+ PRs across 52 repos. Her north star is identical to ours: "Truly become a human companion."

*We stand on her shoulders.*
