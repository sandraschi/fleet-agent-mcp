# Fritz Coworker Plan — Poor Man's Viktor

> **PILOT (v0.2.0-pre)** — 9 MCP tools + 7 scheduled flows shipped; soak testing in progress.
> Central index: [mcp-central-docs/projects/fritz-coworker](https://github.com/sandraschi/mcp-central-docs/blob/main/projects/fritz-coworker/README.md)

## Why

[Viktor](https://viktor.com) sells an AI coworker in Slack that executes across 3,000 tools. Useful ideas; bad ROI for Sandra's fleet (~$200+/mo for real automation vs. owned MCP infra).

Fritz already has 80% of the substrate:

| Subsystem | Viktor-like use |
|---|---|
| `fleet_bridge` | Multi-tool runs (19 fleet servers) |
| `flowforge` | Enforced delivery pipelines |
| `pulse` + `notify` | Scheduled tasks + email delivery |
| `memory` | Skills / learned context |
| `codegen` + `github_*` | Ship code and PRs |
| `contribute` | Autonomous fix pipeline |
| `heartbeat` | Wake, prioritize, dispatch |

## New workflow: `coworker`

See `workflows/coworker.yaml`. Linear path for ad-hoc "do the work" requests:

```
intake → gather → execute → deliver → record
```

- **intake** — Parse ask; check `memory_card_search` for existing skills
- **gather** — `fleet_bridge` calls to relevant MCPs (parallel where safe)
- **execute** — codegen, file edits, or synthesis
- **deliver** — Discord (`discord-mcp`), email (`notify_email`), or artifact file
- **record** — `memory_project_note` + optional `evolution_record`

High-stakes branches (send external email, merge PR, deploy) require explicit `human` group task or workflow branch — **Viktor confirmation gate, fleet-native**.

## Pilot 1: Morning Fleet Pulse

### Schedule

```python
# pulse_add equivalent
pulse_add(
    "Morning Fleet Pulse",
    group="self",
    priority="high",
    recurrence="0 7 * * *",
)
```

Or `notify_schedule(interval="86400", time_of_day="07:00", task="heartbeat_wake")`.

### Tool chain (recipe)

1. `heartbeat_status()` — Fritz health
2. `fleet_list_servers()` — bridge registry
3. `fleet_call(server="meta-mcp", tool="help", args={})` — if meta-mcp exposes health
4. `fleet_call(server="git-github", tool="git_core", args={"operation": "status", ...})` — watched repos
5. `fleet_call(server="docs", tool="search_docs", args={"query": "TODO fleet health"})`
6. LLM synthesize → markdown report
7. `notify_email(to=..., subject="Fleet Pulse", body=report)` or Discord send

### Output template

```markdown
# Fleet Pulse — {date}

## MCP health
- {server}: {up|down}

## Git
- Open PRs: N
- Stale branches: ...

## Action items
1. ...
```

Store copy: `memory_project_note("fleet-pulse", report_summary)`.

## Pilot 2: Docs Drift Audit

Weekly. Targets repos listed in `mcp-central-docs/operations/fleet-registry.json`.

1. `fleet_inspect_repo(repo_path, aspect="readme")`
2. Cross-check ports vs `WEBAPP_PORTS.md` (docs MCP search)
3. Emit checklist markdown
4. Optional: `github_create_issue` per gap

## Pilot 3: Contribution ship (existing)

**Driver:** `scripts/fritz_pipeline_test.py`

| Test repo | Path | Purpose |
|---|---|---|
| `fritz-test` | `D:\Dev\repos\fritz-test` | Intentional bug (`grt` NameError) |
| `fritz-test-work` | `D:\Dev\repos\fritz-test-work` | Clone workspace for edits |
| `fritz-pipeline-test` | `D:\Dev\repos\fritz-pipeline-test` | Pipeline test target |

Flow: issue → `workflow_start("contribution")` → PR → merge.

This is the closest Viktor parity: **real commits, real PRs**.

## Skills (memory cards)

**Hermes parity map:** [hermes-borrowings.md](./hermes-borrowings.md) — run log FTS, curator lifecycle, workflow failure limits, `memory_card_record_run`.

Viktor "skills" → Fritz memory cards with frontmatter:

```yaml
# card: skill/fleet-pulse-format
type: skill
tags: [coworker, fleet-pulse, format]
```

Before `gather`, run:

```python
memory_card_search("fleet pulse format")
memory_card_search(tags=["coworker"])
```

Query-writeback: if output format wrong, `memory_card_update` — knowledge compounds.

## Proactive suggestions (Phase 2)

After `daily` workflow `act` node, scan evolution log for repeated manual patterns (same repo, same ask 3× in 7 days). If found:

```python
pulse_add(
    f"Automate: {pattern_summary}",
    group="human",  # Sandra confirms
    priority="medium",
)
```

Viktor does this in-product; we do it via pulse + human gate.

## Wiring heartbeat (config gap)

Today `heartbeat_wake` returns the next action but does not auto-start `coworker`. To close:

1. In `notify` scheduler executor, call `heartbeat_wake` then `workflow_start("coworker")` if pulse has high-priority recurring task due
2. Or extend `daily.yaml` `act` node to check recurrence due dates

**Not code yet** — documented for v0.2.

## Cost guardrails

| Rule | Rationale |
|---|---|
| Default LLM: local Ollama via robofang | Avoid Viktor-style credit burn |
| Log duration + token estimate per task | Transparency vs opaque credits |
| Cap fleet_bridge fan-out at 5 calls per gather | Prevent runaway multi-tool bills |
| No cloud deploy without `human` pulse task | Safety |

## Test plan

- [x] `coworker_fleet_pulse` MCP tool — manual run
- [x] Scheduler uses `recurrence_due` with `Europe/Vienna` + `07:00`
- [x] `ensure_coworker_tasks()` seeds on server boot
- [x] `uv run pytest tests/ -q` — no regressions (45 passed)
- [ ] Manual: Morning Fleet Pulse once via MCP tool chain
- [ ] `uv run python scripts/fritz_pipeline_test.py` — green
- [ ] Discord or email delivery received
- [ ] `memory_project_note` contains last pulse summary

## MCP tools

| Tool | Description |
|------|-------------|
| `coworker_fleet_pulse(deliver=True)` | Run pulse now; writes `~/.fleet-agent/artifacts/fleet-pulse-YYYYMMDD.md` |
| `coworker_inbox_briefing(deliver=True)` | Unread email digest via email-mcp |
| `coworker_day_prep(deliver=True)` | Combined inbox + pulse tasks + human waits |
| `coworker_docs_drift(deliver=True)` | Weekly README/CHANGELOG hygiene audit |
| `coworker_weekly_report_pdf(deliver=True)` | Fleet Pulse MD → PDF (libreoffice-mcp) → email attachment |
| `coworker_board_pack(deliver=True, template='fleet-board-pack.odt')` | ODT merge → styled board PDF → email |
| `coworker_artifact_pack(deliver=True)` | Batch artifacts → styled PDF → email |
| `coworker_list_flows()` | Active flows + LibreOffice roadmap ideas |

### Recurrence formats

| Format | Example | Meaning |
|--------|---------|---------|
| Daily | `07:00` | Every day at 07:00 Vienna |
| Weekday | `wd:08:00` | Mon–Fri 08:00 |
| Named day | `fri:17:00`, `sun:18:00` | That weekday |
| Monthly DOM | `d1:09:00` | 1st of month at 09:00 |
| Cron monthly | `0 9 1 * *` | Same as d1:09:00 |

`coworker_bootstrap()` seeds all enabled coworker recurring tasks (idempotent).

## Fleet bridge (office)

| Alias | Port | Use |
|-------|------|-----|
| `email` | 10813 | Inbox briefing, delivery |
| `libreoffice` | 10981 | Headless convert (MD→PDF/ODT) |
| `libreoffice-ext` | 8765 | Live Writer/Calc via extension MCP |
| `notion` | 10811 | Optional knowledge sink |
| `onenote` | 10907 | Optional notes sink |

## Settings (`/api/settings`)

| Key | Default | Purpose |
|-----|---------|---------|
| `coworker_timezone` | `Europe/Vienna` | Daily recurrence timezone |
| `fleet_pulse_time` | `07:00` | Daily fire time |
| `fleet_repos_root` | `D:/Dev/repos` | Git snapshot root |
| `fleet_pulse_repos` | `["fleet-agent-mcp","mcp-central-docs"]` | Watched repos |
| `artifact_pack_glob` | `~/.fleet-agent/artifacts/*.md` | Files for weekly artifact pack |
| `artifact_pack_max_files` | `20` | Cap per artifact pack run |
| `heartbeat_email` | `""` | Report delivery (with SMTP) |

## Changelog

See [CHANGELOG.md](../CHANGELOG.md) § 0.2.0-pre and [mcp-central-docs/projects/fritz-coworker/CHANGELOG.md](https://github.com/sandraschi/mcp-central-docs/blob/main/projects/fritz-coworker/CHANGELOG.md).

## References

- Viktor pricing analysis (chat 2026-05-30): $50/mo ≈ 40–200 tasks; crons multiply cost
- `SPEC.md` §8 Roadmap — coworker pilot in v0.2.0-pre
- `identity/NORTH_STAR.md` — "10x faster fleet development" aligns with this plan
