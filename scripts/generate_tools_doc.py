"""Generate docs/TOOLS.md from the live FastMCP tool registry (source of truth).

Usage: uv run python scripts/generate_tools_doc.py
Run this after adding/renaming tools, then commit docs/TOOLS.md alongside.
"""

from collections import defaultdict
from pathlib import Path

from fleet_agent.mcp import tools  # noqa: F401 - triggers @mcp.tool registration
from fleet_agent.mcp.registry import mcp

groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
for comp in mcp.local_provider._components.values():
    name = getattr(comp, "name", None)
    if not name:
        continue
    desc = (getattr(comp, "description", "") or "").split("\n")[0].strip()
    groups[name.split("_")[0]].append((name, desc))

total = sum(len(t) for t in groups.values())
lines = [
    "# TOOLS.md - fleet-agent-mcp tool reference",
    "",
    "> Generated from the live FastMCP registry by",
    "> `uv run python scripts/generate_tools_doc.py`. Do not hand-edit the",
    "> tables below - re-run the generator after adding tools.",
    "",
    f"**{total} tools** across **{len(groups)}** subsystems (portmanteau pattern:",
    "one tool per workflow area, `operation` enum selects the action).",
    "Every tool returns a dialogic dict with `success`, `message`, and domain fields.",
    "",
]
for prefix in sorted(groups):
    members = sorted(groups[prefix])
    lines += [f"## {prefix} ({len(members)})", "", "| Tool | What it does |", "|---|---|"]
    for name, desc in members:
        lines += [f"| `{name}` | {desc} |"]
    lines += [""]

out = Path(__file__).resolve().parent.parent / "docs" / "TOOLS.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {out}: {total} tools, {len(groups)} groups")
