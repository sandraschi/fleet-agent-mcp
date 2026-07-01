"""Background task to poll open PR status via GitHub CLI."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger("fleet_agent.coworker.pr_poll")


async def poll_open_contributions() -> None:
    """Check open contributions for GitHub PR status updates."""
    from ..engine.sqlite_store import get_store

    store = get_store()
    contribs = store.contrib_list(limit=100)
    open_ones = [c for c in contribs if c.get("status") == "open" and c.get("pr_number") and c.get("repo")]

    if not open_ones:
        return

    import json
    import subprocess  # noqa: S404

    for c in open_ones:
        repo = c.get("repo", "")
        pr_num = c.get("pr_number", "")
        if not repo or not pr_num:
            continue

        try:
            result = subprocess.run(
                ["gh", "pr", "view", pr_num, "--repo", repo, "--json", "state,mergedAt"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                continue

            data = json.loads(result.stdout)
            state = data.get("state", "")

            if state == "MERGED":
                store.contrib_update(c["id"], status="merged", pr_url=c.get("pr_url", ""))
                logger.info("PR %s/%s merged", repo, pr_num)
            elif state == "CLOSED":
                store.contrib_update(c["id"], status="closed", pr_url=c.get("pr_url", ""))
                logger.info("PR %s/%s closed without merge", repo, pr_num)
        except Exception as e:
            logger.debug("PR poll %s/%s: %s", repo, pr_num, e)


async def pr_poll_loop(interval: int = 300) -> None:
    """Background loop checking PR status every `interval` seconds."""
    from ..log_store import get_log_store
    logs = get_log_store()
    logs.add("info", f"PR poll loop started ({interval}s interval)", "system")
    while True:
        try:
            await poll_open_contributions()
        except Exception as e:
            logs.add("error", f"PR poll: {e}", "system")
        await asyncio.sleep(interval)
