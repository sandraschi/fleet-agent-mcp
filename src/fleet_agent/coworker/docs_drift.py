"""Docs Drift Audit — weekly fleet documentation hygiene check."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ..settings_store import get_settings_store
from .common import (
    deliver_report,
    fleet_call,
    log_project_note,
    now_label,
    parse_fleet_payload,
    save_artifact,
)

DOCS_DRIFT_PROJECT = "docs-drift"


def _readme_head(repo_path: Path, lines: int = 8) -> str:
    readme = repo_path / "README.md"
    if not readme.is_file():
        return "(missing README.md)"
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")
        return "\n".join(text.splitlines()[:lines])
    except OSError as exc:
        return f"(read error: {exc})"


def _has_changelog(repo_path: Path) -> bool:
    return (repo_path / "CHANGELOG.md").is_file()


def format_docs_drift_report(
    *,
    pulse_date: str,
    repos: list[dict[str, Any]],
    docs_hits: list[dict[str, Any]] | None,
) -> str:
    lines = [
        f"# Docs Drift Audit — {pulse_date}",
        "",
        "## Watched repos",
        "",
    ]
    gaps: list[str] = []
    for row in repos:
        name = row["repo"]
        if row.get("error"):
            lines.append(f"- **{name}:** {row['error']}")
            gaps.append(f"{name}: {row['error']}")
            continue
        flags = []
        if not row.get("has_readme"):
            flags.append("no README")
        if not row.get("has_changelog"):
            flags.append("no CHANGELOG")
        if row.get("dirty"):
            flags.append("uncommitted docs")
        status = ", ".join(flags) if flags else "ok"
        lines.append(f"- **{name}:** {status}")
        if flags:
            gaps.append(f"{name}: {status}")
        preview = row.get("readme_preview", "").replace("\n", " ")[:100]
        if preview:
            lines.append(f"  - README: {preview}…")

    lines.extend(["", "## Fleet docs search (TODO / ports)", ""])
    if docs_hits:
        for hit in docs_hits[:8]:
            title = hit.get("title") or hit.get("path") or hit.get("source") or "?"
            snippet = (hit.get("snippet") or hit.get("content") or "")[:120]
            lines.append(f"- {title}: {snippet}")
    else:
        lines.append("_No docs MCP hits (is documentation-mcp up on :10795?)_")

    lines.extend(["", "## Checklist", ""])
    if gaps:
        for i, gap in enumerate(gaps, 1):
            lines.append(f"{i}. Fix: {gap}")
    else:
        lines.append("1. All watched repos pass basic doc hygiene.")
    lines.append("2. Cross-check `WEBAPP_PORTS.md` if you added a new webapp this week.")
    lines.append("")
    return "\n".join(lines)


async def run_docs_drift(*, deliver: bool = True) -> dict[str, Any]:
    settings = get_settings_store()
    tz_name = settings.get("coworker_timezone", "Europe/Vienna")
    pulse_date = now_label(tz_name)

    repos_root = Path(settings.get("fleet_repos_root", "D:/Dev/repos"))
    watched = settings.get("docs_drift_repos") or settings.get("fleet_pulse_repos") or [
        "fleet-agent-mcp",
        "mcp-central-docs",
        "email-mcp",
        "notion-mcp",
    ]

    repo_rows: list[dict[str, Any]] = []
    for name in watched:
        repo = repos_root / name
        row: dict[str, Any] = {"repo": name}
        if not repo.is_dir():
            row["error"] = "path missing"
            repo_rows.append(row)
            continue
        row["has_readme"] = (repo / "README.md").is_file()
        row["has_changelog"] = _has_changelog(repo)
        row["readme_preview"] = _readme_head(repo)
        try:
            st = subprocess.run(
                ["git", "-C", str(repo), "status", "-sb"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            text = (st.stdout or "").strip()
            row["dirty"] = bool(text.splitlines()[1:]) if text else False
        except (subprocess.TimeoutExpired, OSError):
            row["dirty"] = False
        repo_rows.append(row)

    docs_raw = await fleet_call(
        "docs",
        "search_docs",
        {"query": "TODO WEBAPP_PORTS fleet registry", "limit": 5},
    )
    docs_payload = parse_fleet_payload(docs_raw)
    hits: list[dict[str, Any]] = []
    if isinstance(docs_payload, dict):
        hits = (
            docs_payload.get("results")
            or docs_payload.get("documents")
            or docs_payload.get("hits")
            or []
        )
        if isinstance(docs_payload.get("data"), dict):
            hits = docs_payload["data"].get("results") or hits

    report = format_docs_drift_report(
        pulse_date=pulse_date,
        repos=repo_rows,
        docs_hits=hits if isinstance(hits, list) else [],
    )

    artifact_path = save_artifact("docs-drift", report, tz_name)
    log_project_note(DOCS_DRIFT_PROJECT, pulse_date, report, tags=["coworker", "office", "docs"])

    subject = f"Docs Drift Audit — {pulse_date.split()[0]}"
    delivery = {"email": await deliver_report(report, subject, deliver=deliver)}

    gap_count = sum(1 for r in repo_rows if r.get("error") or not r.get("has_readme"))

    return {
        "success": True,
        "message": f"Docs Drift Audit: {len(repo_rows)} repos, {gap_count} gaps",
        "report": report,
        "artifact_path": artifact_path,
        "delivery": delivery,
        "stats": {"repos_checked": len(repo_rows), "gaps": gap_count},
    }
