# Heartbeat — Wake-Up & Health

Cron-based agent wake-up routine and health monitoring.

**Inspired by** kagura-agent's cron heartbeat: every 30 minutes, the agent wakes, checks its state machine, executes the current task, and advances.

## Concept

Heartbeat is the agent's pulse. On each wake-up:

1. Check for active workflow → if yes, return current task + branches
2. If no workflow, check pending tasks → return highest priority
3. If idle, suggest maintenance (lint knowledge base, check stale tasks, discover workflows)

The heartbeat returns the *next action* — it's up to the caller (cron + LLM) to execute it.

## Tools

### `heartbeat_wake()` — What should I do right now?
```python
heartbeat_wake()
# → {"mode": "workflow", "current_node": "test", "task": "Run tests...",
#    "action": "Execute the current task, then call workflow_next() to advance."}
```

Modes:
- **workflow** — Active workflow exists. Execute current node task.
- **task** — No workflow. Execute highest-priority pending task.
- **idle** — Nothing to do. Suggestions for maintenance.

### `heartbeat_status()` — Health check
```python
heartbeat_status()
# → {"health": {"uptime_seconds": 3600, "active_workflow": "daily",
#    "tasks": {"pending": 5, "done": 12}, "memory_cards": 23,
#    "evolution_entries": 47}}
```

Health metrics:
- Agent name, uptime
- Active workflow + current node
- Task counts (pending / done / total)
- Memory card count
- Evolution entries
- Workflows registered
- Heartbeat configuration

## Cron Integration

Set up a cron job (Windows Task Scheduler or system cron) to call `heartbeat_wake()` every 30 minutes:

```powershell
# Example: Windows Task Scheduler action
uv run -m fleet_agent.mcp.tools.heartbeat --wake
```

Or integrate directly into an MCP client that calls `heartbeat_wake()` on a timer.

## Configuration

```bash
# .env
FLEET_AGENT_HEARTBEAT_ENABLED=true
FLEET_AGENT_HEARTBEAT_INTERVAL_MINUTES=30
```

## Suggested Actions (idle mode)

When nothing is pending, heartbeat suggests:
1. `workflow_autodiscover()` — register workflows
2. `memory_lint()` — check knowledge base health
3. `pulse_stale()` — find forgotten tasks
4. `workflow_start('daily')` — begin a daily routine
