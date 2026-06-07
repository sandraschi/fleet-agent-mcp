"""Office Day Prep — combine inbox highlights with Fritz task queue."""

from __future__ import annotations

from typing import Any

from ..engine.sqlite_store import get_store
from ..settings_store import get_settings_store
from .common import deliver_report, log_project_note, now_label, publish_intel_report, save_artifact
from .inbox_briefing import run_inbox_briefing
from .intel_briefing import _is_readly_longform, fetch_intel_briefing

DAY_PREP_PROJECT = "office-day-prep"


def format_day_prep(
    *,
    pulse_date: str,
    inbox_report: str,
    intel_section: str,
    pending_tasks: list[dict[str, Any]],
    stale_tasks: list[dict[str, Any]],
    human_tasks: list[dict[str, Any]],
) -> str:
    lines = [
        f"# Office Day Prep — {pulse_date}",
        "",
        "## Today's focus (Fritz pulse)",
        "",
    ]
    priority_order = {"high": 0, "medium": 1, "low": 2}
    top = sorted(
        pending_tasks,
        key=lambda t: (priority_order.get(t.get("priority", "medium"), 1), t.get("created_at", "")),
    )[:5]
    if top:
        for i, t in enumerate(top, 1):
            lines.append(f"{i}. [{t.get('priority', 'medium')}] {t.get('task', '?')[:120]}")
    else:
        lines.append("_No pending pulse tasks — good day for deep work._")

    lines.extend(["", "## Waiting on you (human group)", ""])
    if human_tasks:
        for t in human_tasks[:5]:
            lines.append(f"- {t.get('task', '?')[:120]}")
    else:
        lines.append("_Nothing blocked on Sandra._")

    if stale_tasks:
        lines.extend(["", "## Stale (3+ days untouched)", ""])
        for t in stale_tasks[:5]:
            lines.append(f"- {t.get('task', '?')[:100]}")

    lines.extend(["", intel_section, "", "## Inbox highlights", "", inbox_report])
    return "\n".join(lines)


async def run_day_prep(*, deliver: bool = True) -> dict[str, Any]:
    settings = get_settings_store()
    tz_name = settings.get("coworker_timezone", "Europe/Vienna")
    pulse_date = now_label(tz_name)

    inbox_result = await run_inbox_briefing(deliver=False)
    inbox_report = inbox_result.get("report", "")

    intel_result = await fetch_intel_briefing(hours=24, limit=10)
    intel_section = intel_result.get("section", "")

    store = get_store()
    pulse_created = 0
    for item in intel_result.get("hot_items") or []:
        urgency = float(item.get("urgency") or 0)
        relevance = float(item.get("relevance") or 0)
        title = (item.get("title") or "AI news item")[:90]
        if _is_readly_longform(item) and urgency < 8.0:
            label = f"[Readly {relevance:.1f}] {title}"
            priority = "high" if relevance >= 8.5 else "medium"
        else:
            label = f"[AIWatcher {urgency:.1f}] {title}"
            priority = "high" if urgency >= 9.0 else "medium"
        store.todo_add(label, group="agent", priority=priority)
        pulse_created += 1
    pending = [t for t in store.todo_list(status="pending") if not (t.get("recurrence"))]
    human = [t for t in pending if t.get("group_name") == "human" or t.get("group") == "human"]
    stale = store.todo_stale(days=3)

    report = format_day_prep(
        pulse_date=pulse_date,
        inbox_report=inbox_report,
        intel_section=intel_section,
        pending_tasks=pending,
        stale_tasks=stale,
        human_tasks=human,
    )

    artifact_path = save_artifact("office-day-prep", report, tz_name)
    log_project_note(DAY_PREP_PROJECT, pulse_date, report, tags=["coworker", "office"])

    subject = f"Office Day Prep — {pulse_date.split()[0]}"
    delivery = {"email": await deliver_report(report, subject, deliver=deliver)}

    hub_result: dict[str, Any] = {}
    ingest_result: dict[str, Any] = {}
    urgent_result: dict[str, Any] = {}
    try:
        from .aiwatcher_ingest import push_fritz_report_event
        from .urgent_notify import deliver_urgent_alert, urgent_threshold

        hub_result = await publish_intel_report(
            title=subject,
            markdown=report,
            source="fritz",
            tags=["day-prep", "coworker"],
        )
        hot_items = intel_result.get("hot_items") or []
        hot = len(hot_items)
        max_urgency = max(
            (float(it.get("urgency") or 0) for it in hot_items),
            default=0.0,
        )
        ingest_result = await push_fritz_report_event(
            flow="day_prep",
            title=subject,
            summary=(
                f"{len(pending)} pending tasks, {len(human)} human waits, "
                f"{intel_result.get('count', 0)} intel items ({hot} hot). "
                f"Hub: {hub_result.get('url_path', '/')}"
            ),
            urgency_hint=max(max_urgency, 8.0 if hot else 5.5),
        )

        hub_link = ""
        if hub_result.get("success"):
            from ..intel_hub.client import hub_base_url

            hub_link = f"{hub_base_url()}{hub_result.get('url_path', '/')}"

        if hot and max_urgency >= urgent_threshold():
            headlines = [
                f"- [{it.get('urgency', '?')}] {(it.get('title') or '?')[:100]}"
                for it in hot_items[:5]
            ]
            urgent_result = await deliver_urgent_alert(
                subject=subject,
                body="Breaking intel:\n" + "\n".join(headlines),
                reason="day prep hot intel",
                urgency=max_urgency,
                hub_url=hub_link,
            )
    except Exception:
        pass

    return {
        "success": True,
        "message": f"Office Day Prep: {min(len(pending), 5)} focus items, {len(human)} human waits",
        "report": report,
        "artifact_path": artifact_path,
        "delivery": delivery,
        "intel_hub": hub_result,
        "aiwatcher_ingest": ingest_result,
        "urgent_alert": urgent_result,
        "stats": {
            "pending_tasks": len(pending),
            "human_tasks": len(human),
            "stale_tasks": len(stale),
            "inbox_ok": inbox_result.get("success", False),
            "intel_ok": intel_result.get("ok", False),
            "intel_items": intel_result.get("count", 0),
            "intel_pulse_tasks": pulse_created,
        },
    }
