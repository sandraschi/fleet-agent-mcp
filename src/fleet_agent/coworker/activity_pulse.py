"""Fritz activity pulse — concise periodic status to Fleet Hub."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("fleet_agent.coworker.activity_pulse")


def _ago(ts: str) -> str:
    try:
        raw = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        secs = int((datetime.now(UTC) - dt).total_seconds())
        if secs < 60:
            return f"{secs}s"
        if secs < 3600:
            return f"{secs // 60}m"
        if secs < 86400:
            return f"{secs // 3600}h"
        return f"{secs // 86400}d"
    except Exception:
        return ts


def _next_fire(rec: str, last_updated_iso: str, tz_name: str) -> str | None:
    """Estimate next fire time for a recurring task."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    try:
        raw = last_updated_iso.replace("Z", "+00:00")
        last_dt = datetime.fromisoformat(raw)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=UTC)
        last_local = last_dt.astimezone(tz)
    except Exception:
        return None

    rec = rec.strip()

    if rec.endswith("m") and rec[:-1].isdigit():
        mins = int(rec[:-1])
        next_dt = last_local + timedelta(minutes=mins)
        if next_dt < now:
            next_dt = now + timedelta(minutes=mins)
        return next_dt.strftime("%H:%M")

    if rec.endswith("h") and rec[:-1].isdigit():
        hrs = int(rec[:-1])
        next_dt = last_local + timedelta(hours=hrs)
        if next_dt < now:
            next_dt = now + timedelta(hours=hrs)
        return next_dt.strftime("%H:%M")

    if rec.isdigit():
        secs = int(rec)
        next_dt = last_local + timedelta(seconds=secs)
        if next_dt < now:
            next_dt = now + timedelta(seconds=secs)
        return next_dt.strftime("%H:%M")

    if ":" in rec and len(rec) <= 5:
        try:
            h, m = rec.split(":")
            target = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target.strftime("%H:%M")
        except ValueError:
            return None

    if rec.lower().startswith("wd:"):
        try:
            _, h, m = rec.split(":")
            days_ahead = 0
            while days_ahead < 7:
                cand = now + timedelta(days=days_ahead)
                if cand.weekday() < 5:
                    target = cand.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
                    if target > now:
                        return target.strftime("%a %H:%M")
                days_ahead += 1
        except ValueError:
            return None

    named_days = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    prefix = rec.lower().split(":")[0]
    if prefix in named_days:
        try:
            parts = rec.split(":")
            target_dow = named_days[parts[0].lower()]
            h, m = int(parts[1]), int(parts[2])
            for offset in range(8):
                cand = now + timedelta(days=offset)
                if cand.weekday() == target_dow:
                    target = cand.replace(hour=h, minute=m, second=0, microsecond=0)
                    if target > now:
                        return target.strftime("%a %H:%M")
        except (ValueError, IndexError):
            return None

    if rec.lower().startswith("d"):
        try:
            _, day, h, m = rec.split(":")
            target_day = int(day)
            import calendar

            last_day = calendar.monthrange(now.year, now.month)[1]
            actual_day = min(target_day, last_day)
            target = now.replace(
                day=actual_day, hour=int(h), minute=int(m), second=0, microsecond=0
            )
            if target <= now:
                target = target.replace(day=1, month=now.month + 1 if now.month < 12 else 1)
                if now.month == 12:
                    target = target.replace(year=now.year + 1, month=1)
                last_day = calendar.monthrange(target.year, target.month)[1]
                target = target.replace(day=min(target_day, last_day))
            return target.strftime("%d %H:%M")
        except (ValueError, IndexError):
            return None

    return None


def _find_result_text(logs: list[dict], firing_ts: str) -> str:
    """Chronological search for result line after a firing."""
    found = None
    for entry in logs:
        if entry.get("source") != "heartbeat":
            continue
        msg = entry.get("message", "")
        if msg.startswith("  ") and entry.get("timestamp", "") >= firing_ts:
            found = msg.strip()
        elif msg.startswith("Firing:") and entry.get("timestamp", "") > firing_ts:
            break
    if found:
        parts = found.split(":", 1)
        return (parts[1] if len(parts) > 1 else parts[0]).strip()[:55]
    return "processing"


def _is_truly_stale(rec: str, last_updated_iso: str) -> bool:
    """Only flag tasks overdue beyond 2x their normal interval."""
    try:
        raw = last_updated_iso.replace("Z", "+00:00")
        last_dt = datetime.fromisoformat(raw)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=UTC)
    except Exception:
        return True
    elapsed = (datetime.now(UTC) - last_dt).total_seconds()
    rec = rec.strip()

    if rec.endswith("m") and rec[:-1].isdigit():
        threshold = int(rec[:-1]) * 60 * 2
        return elapsed > threshold
    if rec.endswith("h") and rec[:-1].isdigit():
        threshold = int(rec[:-1]) * 3600 * 2
        return elapsed > threshold
    if rec.isdigit():
        threshold = int(rec) * 2
        return elapsed > threshold

    # Time-of-day, day-of-week, day-of-month — flag as stale
    return True


async def run_activity_pulse(deliver: bool = True) -> dict[str, Any]:
    """Publish a short Fritz activity report to the Fleet Hub (overwrites)."""
    try:
        from ..engine.sqlite_store import get_store
        from ..engine.state_machine import get_state_machine
        from ..intel_hub.client import hub_base_url, publish_to_hub
        from ..log_store import get_log_store
        from ..settings_store import get_settings_store
        from .flows import COWORKER_FLOWS

        sm = get_state_machine()
        store = get_store()
        logs_store = get_log_store()
        settings = get_settings_store()
        tz_name = settings.get("coworker_timezone", "Europe/Vienna")

        logs_store.add("info", "Firing: Fritz Activity Pulse", "heartbeat")

        instance = sm.status()
        tasks = store.todo_list()
        now = datetime.now(UTC)

        # ── Workflow ──
        wf_line = (
            f"**{instance.workflow_name}** \u2192 {instance.current_node}" if instance else "*idle*"
        )

        # ── Scheduler status from LogStore (current session) ──
        recent = logs_store.recent(500)
        scheduler_entries = [
            e for e in recent if e.get("source") in ("heartbeat", "system", "agentic")
        ]
        last_tick = None
        for e in reversed(scheduler_entries):
            if e.get("message", "").startswith("Firing:"):
                last_tick = _ago(e["timestamp"])
                break
        scheduler_status = last_tick or "starting..."

        # ── Recent fires with results (persistent execution_log) ──
        exec_log = store.get_execution_log(20)
        recent_fires = exec_log[:8] if exec_log else []

        # ── Task status ──
        by_recency: list[tuple[Any, str]] = []
        flow_by_id = {v["id"]: k for k, v in COWORKER_FLOWS.items()}

        for t in tasks:
            if t.get("status") != "pending":
                continue
            tid = t.get("id", "")
            rec = t.get("recurrence", "")
            updated = t.get("updated_at") or t.get("created_at", "")
            flow_key = None
            if isinstance(t.get("metadata"), dict):
                flow_key = t["metadata"].get("coworker")
            if not flow_key:
                flow_key = flow_by_id.get(tid)
            cat = "other"
            if flow_key and flow_key in COWORKER_FLOWS:
                cat = COWORKER_FLOWS[flow_key]["category"]
            by_recency.append((t, cat))

        # ── Classify tasks ──
        from .recurrence import recurrence_due

        stale_tasks: list[Any] = []
        upcoming: list[tuple[Any, str, str]] = []

        for t, cat in by_recency:
            rec = t.get("recurrence", "")
            updated = t.get("updated_at") or t.get("created_at", "")
            if not rec:
                continue
            if recurrence_due(rec, updated, tz_name=tz_name):
                stale_tasks.append(t)
            else:
                next_fire = _next_fire(rec, updated, tz_name)
                label = t.get("task", "")[:60]
                if next_fire:
                    upcoming.append((t, cat, next_fire))

        # ── Next fires (soonest first) ──
        def _sort_key(item: tuple[Any, str, str]) -> str:
            return item[2]

        upcoming.sort(key=_sort_key)
        next_lines = ""
        for t, cat, next_fire in upcoming[:8]:
            label = t.get("task", "")[:55].replace("_", "")
            rec = t.get("recurrence", "")
            next_lines += f"- {next_fire}  {label}  ({rec})\n"
        if len(upcoming) > 8:
            next_lines += f"- *+{len(upcoming) - 8} more*\n"

        # ── Alerts ──
        alerts: list[str] = []
        for e in reversed(scheduler_entries):
            msg = e.get("message", "")
            if "RED" in msg or "DOWN" in msg or "down" in msg.lower().split(" ")[:3]:
                alerts.append(msg[:120])
            if len(alerts) >= 3:
                break
        # Flag tasks overdue beyond their expected window (2x the interval)
        for t in stale_tasks:
            rec = t.get("recurrence", "")
            updated = t.get("updated_at") or t.get("created_at", "")
            if _is_truly_stale(rec, updated):
                label = t.get("task", "")[:60]
                last = _ago(t.get("updated_at", ""))
                alerts.append(f"overdue: {label} (last {last})")

        alert_lines = ""
        if alerts:
            seen = set()
            for a in alerts:
                key = a[:80]
                if key not in seen:
                    seen.add(key)
                    alert_lines += f"- {a}\n"

        # ── Scheduler recently fired tasks ──
        heartbeat_firings = [
            e
            for e in recent
            if e.get("source") == "heartbeat" and e.get("message", "").startswith("Firing:")
        ]
        firing_lines = ""
        for e in heartbeat_firings[-5:]:
            task_name = e["message"].removeprefix("Firing: ")[:55]
            result_txt = _find_result_text(recent, e["timestamp"])
            firing_lines += f"- {_ago(e['timestamp'])}  {task_name}  \u2192 {result_txt}\n"
        if not firing_lines:
            firing_lines = "*scheduler just started — waiting for next tick*\n"

        # ── Build ──
        lines = [f"**Fritz** \u2014 {_recurrence_summary(tasks, flow_by_id)}"]
        lines.append(f"**Scheduler**: last tick {scheduler_status}")
        lines.append(f"**Workflow**: {wf_line}")
        lines.append("")

        if alert_lines:
            lines.append("### \u26a0\ufe0f Alerts")
            lines.append(alert_lines)
            lines.append("")

        lines.append("### Next Fires")
        lines.append(next_lines if next_lines else "*no scheduled tasks*\n")
        lines.append("")

        lines.append("### Recent Activity")
        lines.append(firing_lines)
        lines.append("")

        if recent_fires:
            lines.append("### Execution Log (persistent)")
            for entry in recent_fires[:5]:
                ev = entry.get("event", "")[:60]
                ts = entry.get("timestamp", "")[:16]
                lines.append(f"- {ev}  ({ts})")
            lines.append("")

        markdown = "\n".join(lines)

        logs_store.add(
            "info",
            f"  activity_pulse: {len(stale_tasks)} stale, {len(heartbeat_firings)} recent fires",
            "heartbeat",
        )

        date_str = now.strftime("%Y-%m-%d")
        result = await publish_to_hub(
            title=f"Fritz \u2014 {date_str} {now.strftime('%H:%M UTC')}",
            markdown=markdown,
            source="fritz",
            summary=f"{len(stale_tasks)} stale, {len(heartbeat_firings)} recent",
            tags=["fritz", "activity-pulse"],
            report_id="fritz-activity",
        )
        hub_url = hub_base_url()
        return {
            "success": True,
            "message": f"Fritz pulse: {len(stale_tasks)} stale, {len(heartbeat_firings)} active",
            "stable_url": f"{hub_url}/reports/fritz-activity",
            "stale": len(stale_tasks),
            "active": len(heartbeat_firings),
            "hub_result": result,
        }
    except Exception as exc:
        logger.exception("activity_pulse failed")
        return {"success": False, "error": str(exc)}


def _recurrence_summary(tasks: list[dict], flow_by_id: dict[str, str]) -> str:
    """Brief summary of tasks by category."""
    counts: dict[str, int] = {}
    for t in tasks:
        if t.get("status") != "pending":
            continue
        flow_key = None
        if isinstance(t.get("metadata"), dict):
            flow_key = t["metadata"].get("coworker")
        if not flow_key:
            flow_key = flow_by_id.get(t.get("id", ""))
        cat = "other"
        if flow_key:
            from .flows import COWORKER_FLOWS

            spec = COWORKER_FLOWS.get(flow_key)
            if spec:
                cat = spec["category"]
        counts[cat] = counts.get(cat, 0) + 1
    parts = [f"{c} {k}" for k, c in sorted(counts.items()) if c > 0]
    return f"{sum(counts.values())} tasks: {', '.join(parts)}" if counts else "0 tasks"
