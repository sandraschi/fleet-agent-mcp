"""Timezone-aware recurrence checks for pulse scheduled tasks."""

from __future__ import annotations

import calendar
import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

_CRON_DAILY = re.compile(r"^(\d{1,2})\s+(\d{1,2})\s+\*\s+\*\s+\*$")
_CRON_MONTHLY = re.compile(r"^(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+\*\s+\*$")
_WEEKDAY_TIME = re.compile(r"^wd:(\d{1,2}):(\d{2})$", re.I)
_NAMED_DAY_TIME = re.compile(r"^(mon|tue|wed|thu|fri|sat|sun):(\d{1,2}):(\d{2})$", re.I)
_DOM_TIME = re.compile(r"^d(\d{1,2}):(\d{1,2}):(\d{2})$", re.I)
_WEEKDAYS = {0, 1, 2, 3, 4}
_NAMED_DOW = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _parse_last_updated(last_updated_iso: str) -> datetime:
    raw = last_updated_iso.replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _time_of_day_due(
    hour: int,
    minute: int,
    last_updated_iso: str,
    tz_name: str,
    *,
    allowed_weekdays: set[int] | None = None,
) -> bool:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    if allowed_weekdays is not None and now.weekday() not in allowed_weekdays:
        return False
    target_min = hour * 60 + minute
    current_min = now.hour * 60 + now.minute
    if current_min < target_min:
        return False
    last_dt = _parse_last_updated(last_updated_iso).astimezone(tz)
    return last_dt.date() < now.date()


def _monthly_dom_due(
    dom: int,
    hour: int,
    minute: int,
    last_updated_iso: str,
    tz_name: str,
) -> bool:
    """Fire once per month on day-of-month (clamped to month length)."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    effective_dom = min(dom, calendar.monthrange(now.year, now.month)[1])
    if now.day != effective_dom:
        return False
    if now.hour * 60 + now.minute < hour * 60 + minute:
        return False
    last_dt = _parse_last_updated(last_updated_iso).astimezone(tz)
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return last_dt < scheduled


def recurrence_due(
    recurrence: str,
    last_updated_iso: str,
    tz_name: str = "Europe/Vienna",
) -> bool:
    """Return True if a recurring task should fire now."""
    if not recurrence or not last_updated_iso:
        return False

    rec = recurrence.strip()
    now_utc = datetime.now(UTC)
    last_dt = _parse_last_updated(last_updated_iso)

    wd = _WEEKDAY_TIME.match(rec)
    if wd:
        return _time_of_day_due(
            int(wd.group(1)), int(wd.group(2)), last_updated_iso, tz_name, allowed_weekdays=_WEEKDAYS
        )

    named = _NAMED_DAY_TIME.match(rec)
    if named:
        dow = _NAMED_DOW[named.group(1).lower()]
        return _time_of_day_due(
            int(named.group(2)),
            int(named.group(3)),
            last_updated_iso,
            tz_name,
            allowed_weekdays={dow},
        )

    dom = _DOM_TIME.match(rec)
    if dom:
        return _monthly_dom_due(
            int(dom.group(1)),
            int(dom.group(2)),
            int(dom.group(3)),
            last_updated_iso,
            tz_name,
        )

    cron_monthly = _CRON_MONTHLY.match(rec)
    if cron_monthly:
        minute, hour, day = int(cron_monthly.group(1)), int(cron_monthly.group(2)), int(cron_monthly.group(3))
        return _monthly_dom_due(day, hour, minute, last_updated_iso, tz_name)

    # Daily time: "07:00" in coworker timezone
    if ":" in rec and len(rec) <= 5:
        try:
            h, m = rec.split(":")
            return _time_of_day_due(int(h), int(m), last_updated_iso, tz_name)
        except ValueError:
            return False

    cron = _CRON_DAILY.match(rec)
    if cron:
        minute, hour = int(cron.group(1)), int(cron.group(2))
        return _time_of_day_due(hour, minute, last_updated_iso, tz_name)

    if rec.isdigit():
        return (now_utc - last_dt).total_seconds() >= int(rec)

    if rec.endswith("h") and rec[:-1].isdigit():
        return (now_utc - last_dt).total_seconds() >= int(rec[:-1]) * 3600

    if rec.endswith("m") and rec[:-1].isdigit():
        return (now_utc - last_dt).total_seconds() >= int(rec[:-1]) * 60

    return False
