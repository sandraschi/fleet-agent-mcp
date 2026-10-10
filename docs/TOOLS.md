# TOOLS.md - fleet-agent-mcp tool reference

> Generated from the live FastMCP registry by
> `uv run python scripts/generate_tools_doc.py`. Do not hand-edit the
> tables below - re-run the generator after adding tools.

**104 tools** across **32** subsystems (portmanteau pattern:
one tool per workflow area, `operation` enum selects the action).
Every tool returns a dialogic dict with `success`, `message`, and domain fields.

## agent (2)

| Tool | What it does |
|---|---|
| `agent_poll` | Poll the hub inbox for unread addressed messages (fritz/boomy/alexa). |
| `agent_send` | Send an addressed message to another entity's hub inbox (point-to-point handoff). |

## agentic (3)

| Tool | What it does |
|---|---|
| `agentic_start` | Start the autonomous agent execution loop. |
| `agentic_status` | Check if the autonomous agent loop is running. |
| `agentic_stop` | Stop the autonomous agent execution loop. |

## aiwatcher (1)

| Tool | What it does |
|---|---|
| `aiwatcher_push_event` | Push a structured event from Fritz into AIWatcher. |

## check (1)

| Tool | What it does |
|---|---|
| `check_log_errors` | Scan recent logs for error/critical entries. Returns a summary. |

## code (1)

| Tool | What it does |
|---|---|
| `code_generate` | Generate code via LLM and write it to the repo. |

## coworker (3)

| Tool | What it does |
|---|---|
| `coworker_bootstrap` | Seed default coworker recurring tasks (pulse, inbox, day prep, docs, PDF). |
| `coworker_execute` | Run a scheduled coworker flow immediately. |
| `coworker_list_flows` | List wired coworker flows and future office flow ideas (incl. LibreOffice). |

## criteria (1)

| Tool | What it does |
|---|---|
| `criteria_lint` | Mechanically validate acceptance criteria before pipeline starts. |

## cron (2)

| Tool | What it does |
|---|---|
| `cron_start` | Start the background heartbeat scheduler (60s loop). |
| `cron_status` | Check if the heartbeat scheduler is running. |

## dev (1)

| Tool | What it does |
|---|---|
| `dev_ops` | Run dev-workflow commands from the voice command bus. |

## evolution (3)

| Tool | What it does |
|---|---|
| `evolution_list` | List recent evolution log entries - corrections and lessons. |
| `evolution_record` | Record a mistake, correction, and lesson in the evolution log. |
| `evolution_stats` | Get evolution log statistics - total corrections, unique lessons, patterns. |

## file (2)

| Tool | What it does |
|---|---|
| `file_edit` | Edit a file by replacing an exact string. Creates a .bak backup first. |
| `file_write` | Write a file to disk. Creates parent directories if needed. |

## fleet (6)

| Tool | What it does |
|---|---|
| `fleet_board` | Bulletin board over the hub. |
| `fleet_call_tool` | Call a tool on any fleet MCP server via HTTP bridge. |
| `fleet_discover` | Discover available fleet MCP servers and their tool surfaces. |
| `fleet_inspect_repo` | Inspect a fleet repo using opencode AI agent. |
| `fleet_list_tools` | List MCP tools available on a fleet server. |
| `fleet_refresh_from_hub` | Refresh the fleet server table from the mcp-federation-hub registry. |

## fritz (8)

| Tool | What it does |
|---|---|
| `fritz_act_on_finding` | File a friendly issue (or, for own repos, hand off to fritz_contribute |
| `fritz_analyze_repo` | Analyze a repo for contribution opportunities - read-only, never |
| `fritz_contribute` | Autonomous contribution: inspect repo, find issue, file issue, fix, commit, PR. |
| `fritz_discover_and_analyze` | Auto-crawler: find candidate repos via GitHub search, then run |
| `fritz_find_contributions` | Search GitHub for open-source contribution opportunities. |
| `fritz_shutdown` | Graceful self-termination - checkpoint state and exit the server process. |
| `fritz_surveil` | Fleet-domain triage: scan hub health/uptime/supervisor for precursors. |
| `fritz_voice_agent` | Voice-in / voice-out loop for Fritz (P5): transcript -> agent_run -> spoken reply. |

## gate (2)

| Tool | What it does |
|---|---|
| `gate_evaluate` | Compute a mechanical gate verdict from evaluation reports. |
| `gate_verify` | Full gate verification: independence + synthesize + oscillation + tier. |

## github (9)

| Tool | What it does |
|---|---|
| `github_commit` | Stage files and commit with a message. |
| `github_create_branch` | Create a new git branch and check it out. |
| `github_create_pr` | Create a pull request on GitHub. |
| `github_get_pr` | Get detailed PR info: title, body, files changed, status checks, diff. |
| `github_list_prs` | List pull requests with title, author, status, and mergeable state. |
| `github_merge_pr` | Merge a pull request. |
| `github_push` | Push commits to remote. |
| `github_review_pr` | Review a pull request: approve, request changes, or comment. |
| `github_status` | Check git status of a repo - branch, changes, ahead/behind. |

## gogetajob (6)

| Tool | What it does |
|---|---|
| `gogetajob_feed` | Browse available jobs from the gogetajob feed. |
| `gogetajob_scan` | Discover open issues from a repo via gogetajob. |
| `gogetajob_start` | Take a job - fork, clone, and create a branch via gogetajob. |
| `gogetajob_stats` | View overall contribution statistics from gogetajob. |
| `gogetajob_submit` | Push changes and create a PR via gogetajob. |
| `gogetajob_sync` | Sync PR/issue statuses via gogetajob. |

## heartbeat (2)

| Tool | What it does |
|---|---|
| `heartbeat_status` | Agent health check - uptime, active workflows, task count, memory stats. |
| `heartbeat_wake` | Agent wake-up routine - check state machine, get current task, suggest next action. |

## identity (4)

| Tool | What it does |
|---|---|
| `identity_north_star` | Read the agent's NORTH_STAR.md - purpose, long-term goals, guiding principles. |
| `identity_soul` | Read the agent's full SOUL.md - core identity, personality, and constraints. |
| `identity_user` | Read USER.md - information about the agent's human partner. |
| `identity_whoami` | Return the agent's self-introduction - name, human partner, and purpose preview. |

## import (1)

| Tool | What it does |
|---|---|
| `import_external_skill` | Import a standard SKILL.md file (OpenClaw, Anthropic skills, Hermes format) into a Fritz skill card. |

## intel (3)

| Tool | What it does |
|---|---|
| `intel_public_site_generate` | Regenerate the public funnel site (GitHub repos + diary + AIWatcher counts). |
| `intel_reports_list` | List published intel reports. |
| `intel_reports_publish` | Publish a report to the Intel Hub (iPad / Tailscale). |

## memory (7)

| Tool | What it does |
|---|---|
| `memory_card_create` | Create a knowledge card in the wiki. |
| `memory_card_search` | Search knowledge cards by full-text query. |
| `memory_card_update` | Update a knowledge card's content and/or tags. |
| `memory_cards_list` | List all knowledge cards. |
| `memory_lint` | Lint the knowledge base for issues: broken references, stale cards, untagged cards. |
| `memory_project_note` | Log a project observation or learning. |
| `memory_project_notes` | List project notes, optionally filtered by project. |

## notify (1)

| Tool | What it does |
|---|---|
| `notify_email` | Send an email via SMTP. Requires smtp config in /api/settings. |

## pipeline (1)

| Tool | What it does |
|---|---|
| `pipeline_liveness_check` | Probe arxiv-mcp + aiwatcher-mcp open-weight pipeline liveness. |

## pulse (6)

| Tool | What it does |
|---|---|
| `pulse_add` | Add a task to the unified TODO list. |
| `pulse_align` | Display tasks sorted by strategic alignment with north star goals. |
| `pulse_complete` | Mark a task as complete. |
| `pulse_delete` | Delete a task permanently. |
| `pulse_list` | List all tasks, optionally filtered by group or status. |
| `pulse_stale` | Find tasks untouched for >= N days. |

## query (1)

| Tool | What it does |
|---|---|
| `query_logs` | Query the in-memory log store. Filters by source, level, or keyword. |

## route (1)

| Tool | What it does |
|---|---|
| `route_voice_command` | Route a voice transcript to the correct fleet MCP server (boomy, alexa, fritz, …). |

## script (7)

| Tool | What it does |
|---|---|
| `script_create` | Create a new task script. |
| `script_delete` | Delete a script permanently. |
| `script_generate` | Use the LLM to generate a task script from a natural language prompt. |
| `script_get` | Get a script by ID. |
| `script_list` | List all registered scripts. |
| `script_run` | Run a script and return its output. |
| `script_update` | Update an existing script. |

## sfb (1)

| Tool | What it does |
|---|---|
| `sfb_post` | Crosspost one event to all three surfaces: hub board + Discord + vla diary. |

## suggestion (2)

| Tool | What it does |
|---|---|
| `suggestion_ack` | Acknowledge/remove a cron suggestion after it was acted on or declined. |
| `suggestion_list` | List proactive cron suggestions (P4): repeated manual runs that qualify for a schedule. |

## teleport (3)

| Tool | What it does |
|---|---|
| `teleport_inspect` | Inspect a .soul archive without unpacking - show manifest and file listing. |
| `teleport_pack` | Pack agent identity, memory, workflows, and config into a portable .soul archive. |
| `teleport_unpack` | Unpack a .soul archive - restore agent identity, memory, workflows, and database. |

## voice (1)

| Tool | What it does |
|---|---|
| `voice_assist` | Execute domestic voice intents - timers, Plex playback, media search. |

## workflow (12)

| Tool | What it does |
|---|---|
| `workflow_active` | List all active workflow instances. |
| `workflow_autodiscover` | Auto-discover and register all YAML workflows from ./workflows/ |
| `workflow_define` | Register a workflow from a YAML or JSON file. |
| `workflow_failure_record` | Record a failure for the current node on the active workflow instance (anti-spin guard). |
| `workflow_list` | List all registered workflows. |
| `workflow_log` | View execution history for the current workflow instance. |
| `workflow_next` | Complete current node and advance to the next step. |
| `workflow_nodes` | List all nodes in a registered workflow with their types and connections. |
| `workflow_reset` | Reset the current workflow instance back to its start node. |
| `workflow_start` | Start a new workflow instance. |
| `workflow_status` | Get current workflow instance status - node, type, task, branches, gate state. |
| `workflow_unblock` | Unblock the active workflow instance and reset its failure counter. |

