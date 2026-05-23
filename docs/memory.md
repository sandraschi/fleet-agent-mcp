# Memory — Knowledge Wiki

Compile-time knowledge accumulation system. Knowledge is integrated at write time, not assembled at query time.

**Inspired by** [kagura-agent/wiki](https://github.com/kagura-agent/wiki) — 270+ concept cards, 360+ project notes, 1290 commits. Also inspired by Karpathy's LLM Wiki.

## Concept

Memory has three layers:

1. **Cards** — Knowledge cards (concepts, patterns, lessons, references)
2. **Projects** — Per-project observations (what you learned from working on something)
3. **Evolution** — Every mistake → correction → lesson (see `docs/evolution.md`)

### Query Writeback

When you search and find outdated or incomplete information, you update it. Answers compound — they feed back into the wiki so you never re-derive them.

### Lint

Periodic health checks detect:
- **Broken cross-references** — card A links to card B, but card B was deleted
- **Stale cards** — 30+ days since last update
- **Untagged cards** — harder to discover, harder to link

## Tools

### `memory_card_create(title, content, tags?, category?)` — Create card
```python
memory_card_create(
    title="SQLite WAL mode",
    content="WAL provides concurrent reads while one writer writes...",
    tags=["sqlite", "performance", "persistence"],
    category="pattern"
)
```

Categories: `general`, `pattern`, `project`, `mistake`, `reference`.

### `memory_card_search(query)` — Full-text search
```python
memory_card_search("state machine")
# → Matches title, content, and tags
```

### `memory_card_update(card_id, content, tags?)` — Update card
```python
memory_card_update("a1b2c3d4", "Updated content...", tags=["updated", "sqlite"])
```
Implements query writeback — find outdated info → update → knowledge compounds.

### `memory_cards_list()` — List all cards
```python
memory_cards_list()
```

### `memory_lint()` — Health check
```python
memory_lint()
# → {"issues": [{"type": "broken_ref", ...}, {"type": "stale", ...}]}
```
Run periodically (daily workflow does this).

### `memory_project_note(project, content, tags?)` — Log project learning
```python
memory_project_note(
    project="flowforge",
    content="SQLite state survives session restarts",
    tags=["architecture", "persistence"]
)
```
Appends to existing project note or creates a new one.

### `memory_project_notes(project?)` — List project notes
```python
memory_project_notes()                    # All projects
memory_project_notes(project="flowforge") # Specific project
```

## Card Schema

```json
{
  "id": "a1b2c3d4",
  "title": "SQLite WAL mode",
  "content": "WAL provides concurrent reads...",
  "tags": ["sqlite", "performance"],
  "category": "pattern",
  "cross_refs": ["sqlite-basics", "performance-tuning"],
  "created_at": "2026-05-19T...",
  "updated_at": "2026-05-19T..."
}
```

## Persistence

- Cards → `fleet-agent.db` → `memory_cards` table
- Project notes → `fleet-agent.db` → `memory_projects` table
- Optional Markdown mirrors in `memory/cards/` and `memory/projects/`
