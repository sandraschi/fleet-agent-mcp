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
