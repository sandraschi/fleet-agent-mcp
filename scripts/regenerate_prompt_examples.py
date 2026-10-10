"""Regenerate MCPB prompt examples from the live tool registry.

- Drops entries whose "tool" no longer exists in the registry (stale names).
- Appends one example per registry tool that has none yet.
- Guarantees the 3-4-100 floor (examples.json >= 100 entries).

Usage: uv run python scripts/regenerate_prompt_examples.py
Canonical file: assets/prompts/examples.json (mcpb/assets/prompts/ is synced
from it at pack time by the fleet pack script, Step 1b).
"""

import json
from pathlib import Path

from fleet_agent.mcp import tools  # noqa: F401 - triggers @mcp.tool registration
from fleet_agent.mcp.registry import mcp

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "assets" / "prompts" / "examples.json"

registry = sorted({v.name for v in mcp.local_provider._components.values() if hasattr(v, "name")})
current = json.loads(TARGET.read_text(encoding="utf-8"))

kept = [e for e in current if e.get("tool") in registry]
dropped = [e.get("tool") for e in current if e.get("tool") not in registry]
covered = {e["tool"] for e in kept}
appended = []
for name in registry:
    if name not in covered:
        appended.append(
            {
                "name": f"{name}-ex",
                "description": f"Execute {name} (registry-derived example)",
                "prompt": f"Run {name}",
                "tool": name,
                "arguments": {},
            }
        )

result = kept + appended
TARGET.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(f"kept={len(kept)} dropped={dropped} appended={len(appended)} total={len(result)}")
if len(result) < 100:
    raise SystemExit(f"3-4-100 FAIL: only {len(result)} examples")
