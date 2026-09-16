"""Grade Watch - weekly external directory grade refresh (ToolBench, Glama, LobeHub).

Calls scraper-mcp's scraper_refresh() to pull fresh grades across all three
platforms, then scraper_matrix() to report the current state. scraper-mcp's
own _alert_if_drop already pushes a drop alert to aiwatcher-mcp per-repo, so
this flow's job is the weekly forcing function plus a human-readable digest -
without it, refresh only happens if someone remembers to call it manually.
"""

from __future__ import annotations

from typing import Any

from .common import (
    deliver_report,
    fleet_call,
    log_project_note,
    now_label,
    parse_fleet_payload,
    save_artifact,
)

GRADE_WATCH_PROJECT = "grade-watch"


def format_grade_watch_report(
    *,
    pulse_date: str,
    refresh_summary: dict[str, Any],
    matrix: dict[str, Any],
) -> str:
    lines = [
        f"# Grade Watch - {pulse_date}",
        "",
        "## Refresh",
        "",
        f"- {refresh_summary.get('message', 'no refresh summary returned')}",
        "",
        "## Current grades",
        "",
    ]

    repos = matrix.get("repos") or {}
    platforms = matrix.get("platforms") or []
    if not repos:
        lines.append("_No grade data returned - is scraper-mcp reachable on :10998?_")
    else:
        header = "| Repo | " + " | ".join(platforms) + " |"
        sep = "|---|" + "---|" * len(platforms)
        lines.extend([header, sep])
        low_grades: list[str] = []
        for repo, per_platform in sorted(repos.items()):
            cells = []
            for pid in platforms:
                entry = per_platform.get(pid)
                if not entry:
                    cells.append("-")
                    continue
                grade = entry.get("grade", "?")
                cells.append(grade)
                if grade in ("D", "F"):
                    low_grades.append(f"{repo} ({pid}: {grade})")
            lines.append(f"| {repo} | " + " | ".join(cells) + " |")
        lines.extend(["", "## Repos needing attention (D/F grade)", ""])
        if low_grades:
            for i, item in enumerate(low_grades, 1):
                lines.append(f"{i}. {item}")
        else:
            lines.append("None this week.")

    lines.append("")
    return "\n".join(lines)


async def run_grade_watch(*, deliver: bool = True) -> dict[str, Any]:
    from ..settings_store import get_settings_store

    settings = get_settings_store()
    tz_name = settings.get("coworker_timezone", "Europe/Vienna")
    pulse_date = now_label(tz_name)

    refresh_raw = await fleet_call("scraper", "scraper_refresh", {})
    refresh_payload = parse_fleet_payload(refresh_raw)
    refresh_summary = (
        refresh_payload if isinstance(refresh_payload, dict) else {"message": str(refresh_payload)}
    )

    matrix_raw = await fleet_call("scraper", "scraper_matrix", {})
    matrix_payload = parse_fleet_payload(matrix_raw)
    matrix = (matrix_payload.get("data") if isinstance(matrix_payload, dict) else None) or {}

    report = format_grade_watch_report(
        pulse_date=pulse_date,
        refresh_summary=refresh_summary,
        matrix=matrix,
    )

    artifact_path = save_artifact("grade-watch", report, tz_name)
    log_project_note(GRADE_WATCH_PROJECT, pulse_date, report, tags=["coworker", "fleet", "grades"])

    subject = f"Grade Watch - {pulse_date.split()[0]}"
    delivery = {"email": await deliver_report(report, subject, deliver=deliver)}

    repo_count = matrix.get("repo_count", 0)
    low_count = sum(
        1
        for per_platform in (matrix.get("repos") or {}).values()
        for entry in per_platform.values()
        if entry.get("grade") in ("D", "F")
    )

    return {
        "success": True,
        "message": f"Grade Watch: {repo_count} repos checked, {low_count} low-grade flags",
        "report": report,
        "artifact_path": artifact_path,
        "delivery": delivery,
        "stats": {"repos_checked": repo_count, "low_grade_flags": low_count},
    }
