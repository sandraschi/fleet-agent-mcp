# FlowForge — State Machine

YAML-defined, enforced workflow engine. Prevents agents from skipping steps.

**Inspired by** [kagura-agent/flowforge](https://github.com/kagura-agent/flowforge) — 124 commits, npm package.

## Concept

FlowForge is a finite state machine persisted in SQLite. Workflows are defined as YAML files and auto-discovered from `./workflows/` and `~/.fleet-agent/workflows/`.

The agent doesn't decide *what* to do — the workflow YAML does. The agent reads state, spawns workers, evaluates results, and advances.

## Workflow YAML Format

```yaml
name: my-workflow
description: Example workflow
start: plan

nodes:
  plan:
    task: Plan the implementation          # NL description
    next: execute                           # Linear progression

  execute:
    task: Execute the plan
    next: test

  test:
    task: Run tests and verify
    branches:                               # Conditional branching
      - condition: tests pass
        next: submit
      - condition: tests fail
        next: execute

  submit:
    task: Create pull request
    next: verify

  verify:
    task: Monitor PR feedback
    terminal: true                          # End of workflow
```

### Node Fields

| Field | Required | Description |
|---|---|---|
| `task` | yes | Natural language description of what to do |
| `next` | no | Name of next node (linear flow) |
| `branches` | no | Array of `{condition, next}` for branching |
| `terminal` | no | `true` if this is the final node |

## Tools

### `workflow_define(yaml_path)` — Register a workflow
```python
workflow_define("workflows/daily.yaml")
```

### `workflow_autodiscover()` — Auto-register all workflows
```python
workflow_autodiscover()
```
Scans `./workflows/*.yaml`, `./workflows/*.yml`, `~/.fleet-agent/workflows/*.yaml`.

### `workflow_start(name)` — Start a new instance
```python
workflow_start("daily")
# → {"current_node": "review", "task": "Run heartbeat_wake()..."}
```

### `workflow_status()` — Current node + task + branches
```python
workflow_status()
# → {"current_node": "test", "task": "Run tests", "branches": [...]}
```

### `workflow_next(branch?)` — Advance to next step
```python
workflow_next()         # Linear: advance to next node
workflow_next(branch=0) # Branching: take branch 0
# Terminal → {"completed": true}
```

### `workflow_log()` — Execution history
```python
workflow_log()
# → {"history": [{"from_node": "plan", "to_node": "execute", ...}]}
```

### `workflow_list()` / `workflow_active()` — Browse workflows
```python
workflow_list()    # All registered workflows
workflow_active()  # Currently active instances
```

### `workflow_reset()` — Restart from beginning
```python
workflow_reset()
# → Resets current workflow to start node
```

## Persistence

State persists in `~/.fleet-agent/fleet-agent.db` (SQLite). Survives server restarts and context resets.

## Included Workflows

| File | Nodes | Description |
|---|---|---|
| `daily.yaml` | review → maintain → learn → act | Daily agent routine |
| `contribution.yaml` | study → implement → test → submit → verify → done | Open source PR pipeline |
| `learning.yaml` | research → synthesize → document → apply | Structured learning |
