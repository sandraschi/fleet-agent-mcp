"""CLI wrapper for regenerating the public Intel Hub site.

Usage:
    uv run python scripts/generate-public-site.py

Schedule it (e.g. hourly) via Windows Task Scheduler or a Fritz coworker flow.
"""

import asyncio
import sys

from fleet_agent.intel_hub.public_site import generate_public_site


async def main() -> int:
    result = await generate_public_site()
    print(result.get("message", str(result)))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
