# Teleport — Soul Migration

Pack an agent's identity, memory, workflows, and database into a portable `.soul` archive for migration between machines.

**Inspired by** [kagura-agent/openclaw-teleport](https://github.com/kagura-agent/openclaw-teleport) (v0.5.0) — packs workspace + config + credentials + cron + sessions into a single file.

## Concept

Teleport captures everything that makes an agent *that agent*:

- **Identity files** — SOUL.md, NORTH_STAR.md, USER.md
- **Workflow definitions** — All YAML workflow files
- **SQLite database** — Workflows, instances, tasks, knowledge cards, evolution log
- **Memory markdown** — Cards, project notes, evolution entries

All packed into a single `.soul` tar.gz archive. Unpack on a new machine = full one-command restore.

## Security Warning

**`.soul` files may contain sensitive data** — API tokens, config, session data. Treat them like password files:
- Add `*.soul` to `.gitignore`
- Transfer via encrypted channels
- Delete after unpacking on target machine
- Consider encrypting with `gpg -c agent.soul`

## Tools

### `teleport_pack(output_path?)` — Create .soul archive
```python
teleport_pack()
# → ~/.fleet-agent/lumen_20260519.soul

teleport_pack(output_path="/tmp/backup.soul")
# → Custom path
```

Returns: archive path, file count, manifest with metadata.

### `teleport_inspect(soul_path)` — Preview without unpacking
```python
teleport_inspect("lumen_20260519.soul")
# → {"manifest": {...}, "files": ["identity/SOUL.md", ...], "file_count": 15}
```

Shows what's in the archive without extracting.

### `teleport_unpack(soul_path, target_dir?)` — Restore agent
```python
teleport_unpack("lumen_20260519.soul")
# → Restores to ~/.fleet-agent/

teleport_unpack("lumen_20260519.soul", target_dir="/custom/path")
# → Restores to custom directory
```

**DESTRUCTIVE** — overwrites existing files in target directory.

## Archive Structure

```
lumen_20260519.soul (tar.gz)
├── manifest.json           # Metadata, agent name, pack date
├── identity/
│   ├── SOUL.md
│   ├── NORTH_STAR.md
│   └── USER.md
├── workflows/
│   ├── daily.yaml
│   ├── contribution.yaml
│   └── learning.yaml
├── data/
│   └── fleet-agent.db      # SQLite database
└── memory/
    ├── cards/
    └── projects/
```

## Manifest

```json
{
  "agent_name": "Lumen",
  "human_name": "Sandra",
  "version": "0.1.0",
  "packed_at": "2026-05-19T...",
  "file_count": 15
}
```
