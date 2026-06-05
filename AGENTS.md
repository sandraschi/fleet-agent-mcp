# fleet-agent-mcp — Agent Guide

## Overview

Self-evolving AI agent (Fritz) — state machine, task management, coworker workflows, fleet_bridge. Inspired by kagura-agent.

**Voice Command Bus:** `POST /api/voice/intent` and tool `route_voice_command`. Registry: `config/voice_command_bus.yaml` or `FLEET_VOICE_REGISTRY` → mcp-central-docs.

## Standards

- FastMCP 3.2+ portmanteau tool pattern — tools use `operation` enum param
- Responses: structured dicts with `success`, `message`, domain-specific fields
- Dual transport: stdio (Claude Desktop) + HTTP (`MCP_TRANSPORT=http`)
- See [mcp-central-docs](https://github.com/sandraschi/mcp-central-docs) for fleet-wide coding standards

## Key Files

- `README.md` — full documentation
- `workflows/morning_brief.yaml` — WF-001 intel → ViLife → MemOps
- `pyproject.toml` — build config and entry points

## Quick Ref

```powershell
uv run pytest tests/ -q
```

Install docs: follow `mcp-central-docs/standards/AGENT_INSTALL_REFERENCE.md`
