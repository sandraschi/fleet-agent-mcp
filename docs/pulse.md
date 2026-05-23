# Pulse — Task Management

Unified task management with north-star alignment.

**Inspired by** [kagura-agent/pulse-todo](https://github.com/kagura-agent/pulse-todo) — OpenClaw AgentSkill with single TODO.md approach.

## Concept

Pulse maintains a single TODO list as the source of truth for all pending work. Tasks are grouped by dependency type and prioritized strategically.

### Dependency Groups

| Group | Meaning | Example |
|---|---|---|
| `self` | You do it yourself | "Write SPEC.md" |
| `human` | Waiting on human partner | "Review PR #42" |
| `external` | Blocked on external system | "Deploy to production" |

### Priorities

- **high** — Must do now. North-star aligned.
- **medium** — Should do soon.
- **low** — Nice to have.

## Tools

### `pulse_add(task, group?, priority?, recurrence?)` — Add a task
```python
pulse_add("Write SPEC.md", group="self", priority="high")
pulse_add("Wait for review", group="human")
pulse_add("Sync failures? Run every 4h", group="self", recurrence="0 */4 * * *")
```

### `pulse_list(group?, status?)` — List tasks
```python
pulse_list()                        # All tasks
pulse_list(group="self")            # Only self-assigned
pulse_list(status="pending")        # Only pending
```

### `pulse_complete(task_id)` — Mark done
```python
pulse_complete("a1b2c3d4")
```

### `pulse_delete(task_id)` — Remove permanently
```python
pulse_delete("a1b2c3d4")
```

### `pulse_stale(days?)` — Find forgotten tasks
```python
pulse_stale()       # 3+ days untouched (default)
pulse_stale(days=7) # 7+ days untouched
```

### `pulse_align()` — Strategic priority ordering
```python
pulse_align()
# → Top 5 tasks sorted by priority then age
```
Aligns tasks with north-star goals. Highest priority + oldest first.

## Persistence

Tasks stored in `fleet-agent.db` → `todo_items` table.

## Recurrence

Supports cron-style recurrence patterns:
```
"0 */4 * * *"   # Every 4 hours
"0 9 * * *"     # Every day at 9 AM
"0 0 * * 1"     # Every Monday at midnight
```
