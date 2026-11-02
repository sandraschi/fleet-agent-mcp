# fleet-agent-mcp — Agent Guide

## Overview

Self-evolving AI agent (Fritz) — state machine, task management, coworker workflows, fleet_bridge. Inspired by kagura-agent.

**Voice Command Bus:** `POST /api/voice/intent` and tool `route_voice_command`. Registry: `config/voice_command_bus.yaml` or `FLEET_VOICE_REGISTRY` → mcp-central-docs. Dev-workflow commands (`fritz gpu status`, `fritz start webapp X`, `fritz kick invokeai`) route in-process to `dev_ops` (`mcp/tools/dev.py`).

**Intel Reports Hub (11027):** `docs/INTEL_REPORTS_HUB.md` — Pulse/Day Prep/devices watch publish HTML; `aiwatcher_push_event` ingests to AIWatcher; urgent email on degradation.

## Standards

- FastMCP 3.2+ portmanteau tool pattern — tools use `operation` enum param
- Responses: structured dicts with `success`, `message`, domain-specific fields
- Dual transport: stdio (Claude Desktop) + HTTP (`MCP_TRANSPORT=http`)
- See [mcp-central-docs](https://github.com/sandraschi/mcp-central-docs) for fleet-wide coding standards

## Key Files

- `README.md` — full documentation
- `workflows/morning_brief.yaml` — WF-001 intel → ViLife → MemOps
- `pyproject.toml` — build config and entry points

## Daemon & transports (read before launching anything)

- **Ports**: backend 10996 (REST + `/mcp`), webapp 10997 (vite), Intel Hub 11027.
- **Do not start a second backend on 10996.** A steady-state Fritz instance
  normally owns it; a second bind fails with `Errno 10048`. Check
  `GET /api/health` first; scratch backends go on another port
  (`--port 13996`) and shut down via `POST /api/shutdown`.
- **Transports**: `--http` serves; `--stdio` probes `FLEET_AGENT_MCP_API_URL`
  (`http://127.0.0.1:10996/mcp`) for a live daemon and proxies to it,
  otherwise runs the registry in-process. Claude Desktop bundle entry:
  `python -m fleet_agent --stdio` (`fleet_agent_mcp` is an alias).
- **State**: `~/.fleet-agent/fleet-agent.db` (single writer assumed).
- **No NSSM service ships with this repo**; if one is registered externally,
  restart it with `sc.exe stop/start`, never by killing the child process.

## Quick Ref

```powershell
uv run pytest tests/ -q
```

Install docs: follow `mcp-central-docs/standards/AGENT_INSTALL_REFERENCE.md`

## Multi-agent working rules (several agents and IDEs)

Several agents (Claude Code, OpenCode, Cursor, Windsurf and others) work on this repo from
different IDEs, sometimes at the same time. These rules exist because that went wrong once:
one agent ran a commit-all and swept another agent's half-finished manifest edits into a
release and a pushed tag, leaving the pushed tree unbuildable.

Fleet standard with the full reasoning: `mcp-central-docs/standards/MULTI_AGENT_CONCURRENCY.md`.

### Before you start

1. Run `git status` and `git log -5 --format="%h %ad %s" --date=iso`. If the tree is dirty and
   you did not make those changes, someone else is working here. Leave their files alone:
   do not reset, clean, stash or revert them.
2. Prefer your own branch (`agent/<tool>-<topic>`) or a worktree
   (`git worktree add ..\<repo>-<topic> -b agent/<tool>-<topic>`). Merge to the default branch
   only when the work is finished and checked.

### Committing

- Never `git add -A`, `git add .`, `git commit -a` or `git commit -am`. Name your paths:
  `git add <path> ...` then `git commit -m "..." -- <path> ...`.
- Before committing run `git diff --cached --stat` and check every file is yours.
- A manifest (`Cargo.toml`, `package.json`, `pyproject.toml`) and the files it points at go in the
  same commit. Never commit a manifest that names something not in the commit.
- Do not tag or release from a dirty tree, or from a `WIP-Auto` commit made by the nightly sweep.
  Before tagging, a clean clone of the exact commit must build and pass tests.
- Do not move or delete a published tag; add a new one. Do not force-push a shared branch.
- Do not push another agent's commits you did not read.

### Hooks

`.githooks/pre-commit` rejects a commit whose Cargo manifests name workspace members or path
dependencies that are not tracked. Enable it once per clone:

    git config core.hooksPath .githooks

Do not bypass it with `--no-verify`. If it blocks you, the commit really is broken.

### Leave a trail

- Commit messages say what and why. Agent commits end with the tool's own trailer.
- Long-running work: note it in the repo's worklog or plan file so the next agent sees it.
- At the end of a session, say what you left uncommitted and whose it appears to be.
