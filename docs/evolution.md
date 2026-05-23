# Evolution Log — Learn From Every Mistake

Systematic recording of mistakes, corrections, and lessons. No curation, no hiding.

**Inspired by** kagura-agent: *"When I mess up, it's in the git history. When I learn something, it goes into my wiki. No curation, no hiding."*

## Concept

The evolution log is the agent's memory of errors and corrections. Every entry contains:

1. **Correction** — What went wrong and how it was fixed
2. **Lesson** — The rule to follow going forward (stated as an imperative)
3. **Context** — What was being attempted when the mistake happened

Over time, patterns emerge from repeated lessons — the agent learns what behaviors lead to failure.

## Tools

### `evolution_record(correction, lesson, context?)` — Log a correction
```python
evolution_record(
    correction="Used shell=True in subprocess — switched to create_subprocess_exec",
    lesson="NEVER use shell=True for subprocess calls",
    context="Building the state machine engine"
)
```

### `evolution_list(limit?)` — Browse recent entries
```python
evolution_list()        # Last 50
evolution_list(limit=10) # Last 10
```

### `evolution_stats()` — Statistics + duplicates
```python
evolution_stats()
# → {"stats": {"total_corrections": 47, "unique_lessons": 31},
#    "duplicate_lessons": [{"lesson": "ALWAYS test before commit", "count": 3}]}
```

Duplicate lessons indicate persistent patterns that need deeper attention.

## Entry Schema

```json
{
  "id": "a1b2c3d4",
  "correction": "Used shell=True — switched to create_subprocess_exec",
  "lesson": "NEVER use shell=True for subprocess calls",
  "context": "Building the state machine engine",
  "created_at": "2026-05-19T..."
}
```

## Lint

`evolution_stats()` detects duplicate lessons — the same lesson learned multiple times suggests a systemic issue rather than a one-off mistake.

## Best Practices

1. **Record immediately** — log corrections while the context is fresh
2. **State lessons as rules** — "ALWAYS X", "NEVER Y", "PREFER Z over W"
3. **Include context** — what were you trying to do?
4. **Review periodically** — the daily workflow checks evolution stats

## Persistence

Stored in `fleet-agent.db` → `evolution_log` table. Also mirrors to `memory/evolution/` as Markdown files.
