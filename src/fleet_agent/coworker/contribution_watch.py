"""Scheduled dogfooding: run fritz_contribute against Fritz's own repos.

Own-repo only (fritz_contribute pushes directly to origin for repos owned by
the authenticated gh user - see contribute.py's _own_gh_user()), and never
merges - fritz_contribute only ever calls `gh pr create`, never `gh pr merge`.
Real issues/PRs are created; a human reviews and merges (or doesn't).
"""

from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .common import save_artifact

logger = logging.getLogger("fleet_agent.coworker.contribution_watch")

OWN_REPOS_ROOT = Path("D:/Dev/repos")


def _own_repo_urls() -> list[str]:
    """GitHub URLs to dogfood against.

    If settings "contribution_dogfood_repos" (list of local dir names under
    D:\\Dev\\repos) is set, only those are used - the account has 233 repos
    total, most of them not the active fleet, so an explicit allowlist is
    the safe default path. Falls back to scanning every local checkout with
    an origin remote owned by the authenticated gh user only when no
    allowlist is configured.
    """
    from ..mcp.tools.contribute import _own_gh_user
    from ..settings_store import get_settings_store

    user = _own_gh_user()
    if not user:
        return []

    allowlist = get_settings_store().get("contribution_dogfood_repos", [])
    if allowlist:
        return [
            f"https://github.com/{user}/{name}"
            for name in allowlist
            if (OWN_REPOS_ROOT / name / ".git").exists()
        ]

    urls: list[str] = []
    for repo_dir in sorted(OWN_REPOS_ROOT.iterdir()):
        if not (repo_dir / ".git").exists():
            continue
        try:
            out = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
        except Exception:
            continue
        if f"github.com/{user}/" in out or f"github.com:{user}/" in out:
            urls.append(f"https://github.com/{user}/{repo_dir.name}")
    return urls


async def run_contribution_dogfood(*, deliver: bool = True) -> dict[str, Any]:
    """Run fritz_contribute against every own repo with ruff findings.

    fritz_contribute is a no-op (returns immediately) for a repo with no
    matching findings, so most repos on most runs do nothing. Real
    issues/PRs are opened for repos that do - never auto-merged.
    """
    from ..mcp.tools.contribute import fritz_contribute
    from ..settings_store import get_settings_store

    settings = get_settings_store()
    repos = _own_repo_urls()
    results: list[dict[str, Any]] = []
    prs_opened: list[str] = []
    errors = 0

    for repo_url in repos:
        try:
            result = await fritz_contribute(repo_url=repo_url, dry_run=False)
        except Exception as exc:
            logger.exception("Dogfood run failed for %s", repo_url)
            results.append({"repo": repo_url, "message": f"error: {exc}"})
            errors += 1
            continue
        results.append({"repo": repo_url, "message": result.get("message", "")})
        if result.get("pr_url"):
            prs_opened.append(f"{repo_url}: {result['pr_url']}")

    now = datetime.now(UTC)
    report_lines = [
        "# Contribution Dogfood Run",
        f"Generated: {now.isoformat()}",
        "",
        f"Own repos scanned: {len(repos)}",
        f"PRs opened: {len(prs_opened)}",
        "",
    ]
    report_lines.extend(f"- {p}" for p in prs_opened)
    report_lines.append("")
    report_lines.extend(f"- {r['repo']}: {r['message']}" for r in results)

    report = "\n".join(report_lines)
    artifact_path = save_artifact("contribution-dogfood", report, "Europe/Vienna")

    status = "yellow" if errors else "green"
    if prs_opened and deliver:
        to = settings.get("heartbeat_email", "")
        smtp_host = settings.get("smtp_host", "")
        smtp_user = settings.get("smtp_user", "")
        smtp_pass = settings.get("smtp_pass", "")
        if to and smtp_host and smtp_user:
            from ..mcp.tools.notify import _send_email_smtp

            await _send_email_smtp(
                to=to,
                subject=f"CONTRIBUTION DOGFOOD - {len(prs_opened)} PR(s) opened",
                body=report,
                smtp_host=smtp_host,
                smtp_port=int(settings.get("smtp_port", 587)),
                smtp_user=smtp_user,
                smtp_pass=smtp_pass,
            )

    return {
        "success": True,
        "status": status,
        "message": f"{len(repos)} repos scanned, {len(prs_opened)} PR(s) opened, {errors} error(s)",
        "artifact_path": artifact_path,
    }
