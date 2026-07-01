"""Seed starter memory cards and example scripts on server boot."""

from __future__ import annotations

import logging
from typing import Any

from ..engine.sqlite_store import get_store

logger = logging.getLogger("fleet_agent.seed")

_STARTER_CARDS = [
    {
        "title": "Fritz Architecture",
        "category": "system",
        "tags": ["architecture", "overview"],
        "content": """# Fritz Architecture

Fritz (fleet-agent-mcp) is a self-evolving AI fleet conductor agent.

## Three-Layer Architecture
1. **flowforge** — YAML-defined state machine. Defines *what* to do, in *what* order.
2. **heartbeat** — Coordinator. Wakes on cron, reads state, spawns workers, evaluates, advances.
3. **coworker** — Worker. Executes scheduled flows.

## Key Concepts
- **Portmanteau tools**: related operations grouped into one tool with an operation enum
- **Fleet Bridge**: cross-server MCP client calling 19+ registered fleet servers
- **Evolution Log**: every mistake → correction → lesson persisted in SQLite
- **Teleport**: pack agent identity + memory + workflows into a portable .soul archive""",
    },
    {
        "title": "Fleet Servers",
        "category": "system",
        "tags": ["fleet", "servers", "ports"],
        "content": """# Fleet Servers Accessible via Fleet Bridge

Registered fleet servers and their MCP endpoints:

| Alias | Description | Port |
|-------|-------------|------|
| git-github | GitHub API: repos, issues, PRs | 10702 |
| docs | documentation-mcp: federated RAG | 10795 |
| memory | advanced-memory-mcp: persistent memory | 10732 |
| discord | Discord bot integration | 10756 |
| plex | Plex media: libraries, streaming | 10740 |
| robofang | Fleet command center, robotics | 10871 |
| arxiv | arXiv research paper tools | 10770 |
| aiwatcher | Fleet observability | 10946 |
| browser | Browser control, bookmarks | 10781 |
| speech | Speech-to-text, wake word | 10909 |
| email | Email management | 10813 |
| calibre | E-book management | 10720 |
| cursor | Cursor IDE usage/guardrails | 11000 |
| opencode | AI coding agents | 10951 |
| devices | Home safety: CO, smoke, Ring | 10717 |
| notion | Notion workspace API | 10811 |
| onenote | OneNote integration | 10907 |
| libreoffice | LibreOffice document conversion | 10981 |
| vla-robotics | VLA robot bridge | 11024 |
| yahboom | Yahboom robot control | 10892 |
| alexa | Amazon Alexa smart home | 10801 |""",
    },
    {
        "title": "Coworker Flows",
        "category": "automation",
        "tags": ["coworker", "schedule", "flows"],
        "content": """# Scheduled Coworker Flows

Fritz runs these automation flows on a schedule:

| Flow | Schedule | Purpose |
|------|----------|---------|
| Fleet Pulse | Daily 07:00 | MCP health, git snapshots, pipeline liveness |
| Inbox Briefing | Weekdays 08:00 | Unread email via email-mcp |
| Office Day Prep | Weekdays 08:30 | Inbox + pulse + intel combined |
| Docs Drift Audit | Sunday 10:00 | README/port drift vs fleet docs |
| Weekly Report PDF | Friday 17:00 | Fleet Pulse MD → PDF → email |
| Board Pack | 1st of month 09:00 | ODT merge → styled PDF |
| Artifact Pack | Sunday 18:00 | Batch artifacts → styled PDF |
| Cursor Spend Watch | Every 2h | Cursor-mcp spend guardrail check |
| Devices Watch | Every 5m | Home safety: CO, smoke, Ring |

All flows use the recurrence format: HH:MM (daily), wd:HH:MM (weekdays), sun:HH:MM (specific day), dN:HH:MM (day of month), or Nh/Nm (interval).""",
    },
    {
        "title": "Script System",
        "category": "system",
        "tags": ["scripts", "automation"],
        "content": """# Fritz Script System

Scripts are executable tasks that can be triggered manually or on a schedule.

## Script Types
1. **Python** — Full Python via exec() with __result, __log, __args context
2. **Shell** — Windows cmd commands via subprocess (30s timeout)
3. **PowerShell** — PowerShell scripts via pwsh (30s timeout)
4. **MCP Call** — JSON: {server, tool, params, llm_analyze?} — calls a tool on a fleet server

## MCP Call with AI Analysis
The `llm_analyze` field is optional. When set, Fritz's LLM interprets the tool result:
```json
{
  "server": "pulse",
  "tool": "pulse_list",
  "params": {"status": "pending"},
  "llm_analyze": "Summarize pending tasks by priority"
}
```

## AI Generation
Use the Scripts page's AI Generate button (or the `script_generate` tool) to create scripts from natural language. Fritz chooses the best language, server, tool, and parameters automatically.""",
    },
    {
        "title": "PR Pipeline (fritz_contribute)",
        "category": "automation",
        "tags": ["pr", "contribute", "github"],
        "content": """# Fritz PR Pipeline

`fritz_contribute` is a fully autonomous contribution pipeline:

1. **Clone** — git clone the target repo
2. **Scan** — ruff check --select S701,S110,E722,F401
3. **Prioritize** — pick highest-severity finding
4. **LLM Fix** — send file + error to LLM, get old_string/new_string
5. **File Issue** — gh issue create
6. **Branch** — git checkout -b fix/{code}
7. **Apply** — file_edit with backup + verification
8. **Commit** — git commit -m
9. **Push** — gh repo fork + git push
10. **PR** — gh pr create

Shipped PRs: discord-mcp (#2, #4), GrandOrgue (#2497, #2498), edge-bookmark-mcp-server (#5).""",
    },
]


def seed_cards_and_scripts() -> dict[str, Any]:
    """Idempotently seed starter memory cards and example scripts."""
    import json as _json
    store = get_store()
    seeded_cards = 0
    seeded_scripts = 0

    existing_cards = store.cards_list()
    existing_titles = {c.get("title") for c in existing_cards}

    for card_data in _STARTER_CARDS:
        title = card_data["title"]
        if title in existing_titles:
            continue
        store.card_upsert({
            "id": f"seed-{title.lower().replace(' ', '-')[:20]}",
            "title": title,
            "content": card_data["content"],
            "tags": card_data.get("tags", ""),
            "category": card_data.get("category", "general"),
            "created_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
        })
        seeded_cards += 1

    # Seed a few example scripts if none exist
    existing_scripts = store.script_list()
    if not existing_scripts:
        example_scripts = [
            {
                "name": "Fleet Health Summary",
                "description": "Check all fleet server health and summarize",
                "language": "mcp_call",
                "content": _json.dumps({
                    "server": "fleet-agent",
                    "tool": "heartbeat_status",
                    "params": {},
                    "llm_analyze": "Summarize the health status concisely",
                }, indent=2),
            },
            {
                "name": "Pending Tasks Report",
                "description": "List pending high-priority tasks",
                "language": "mcp_call",
                "content": _json.dumps({
                    "server": "fleet-agent",
                    "tool": "pulse_list",
                    "params": {"status": "pending"},
                    "llm_analyze": "Group the pending tasks by priority and suggest which to do first",
                }, indent=2),
            },
            {
                "name": "Pipeline Liveness Check",
                "description": "Check arxiv + aiwatcher pipeline health",
                "language": "mcp_call",
                "content": _json.dumps({
                    "server": "fleet-agent",
                    "tool": "pipeline_liveness_check",
                    "params": {"stale_hours": 48},
                    "llm_analyze": "If the pipeline is degraded, explain what's stale and what to do",
                }, indent=2),
            },
            {
                "name": "Send Fleet Pulse Email",
                "description": "Run fleet pulse and email the report",
                "language": "mcp_call",
                "content": _json.dumps({
                    "server": "fleet-agent",
                    "tool": "coworker_execute",
                    "params": {"flow": "fleet_pulse", "deliver": True},
                }, indent=2),
            },
            {
                "name": "Search GitHub Open PRs",
                "description": "List open PRs needing review across the fleet",
                "language": "mcp_call",
                "content": _json.dumps({
                    "server": "git-github",
                    "tool": "list_prs",
                    "params": {"state": "open"},
                    "llm_analyze": "Summarize which PRs need urgent attention",
                }, indent=2),
            },
            {
                "name": "Check Devices Safety",
                "description": "Check devices-mcp for CO/smoke alerts",
                "language": "mcp_call",
                "content": _json.dumps({
                    "server": "fleet-agent",
                    "tool": "coworker_execute",
                    "params": {"flow": "devices_watch", "deliver": False},
                    "llm_analyze": "Are there any critical safety alerts?",
                }, indent=2),
            },
            {
                "name": "Disk Usage Report (Python)",
                "description": "Check disk usage on all drives",
                "language": "python",
                "content": (
                    "import shutil\n"
                    'drives = ["C:", "D:"]\n'
                    "for d in drives:\n"
                    "    usage = shutil.disk_usage(d)\n"
                    "    pct = usage.used / usage.total * 100\n"
                    '    __log.append(f"{d}: {pct:.0f}% used ({usage.free // 2**30} GB free)")\n'
                    '__result["drives"] = __log[:]\n'
                ),
            },
        ]
        for script in example_scripts:
            store.script_create(
                name=script["name"],
                content=script["content"],
                language=script["language"],
                description=script["description"],
            )
            seeded_scripts += 1

    return {
        "seeded_cards": seeded_cards,
        "seeded_scripts": seeded_scripts,
        "message": f"Seeded {seeded_cards} cards, {seeded_scripts} scripts",
    }
