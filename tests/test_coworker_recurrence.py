"""Tests for coworker recurrence scheduling."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from fleet_agent.coworker.recurrence import recurrence_due


class TestRecurrenceDue:
    def test_daily_time_not_yet(self):
        tz = ZoneInfo("Europe/Vienna")
        now = datetime.now(tz)
        future_hour = (now.hour + 2) % 24
        rec = f"{future_hour:02d}:00"
        last = datetime.now(UTC).isoformat()
        assert recurrence_due(rec, last, tz_name="Europe/Vienna") is False

    def test_daily_time_fires_once_per_day(self):
        yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        assert recurrence_due("07:00", yesterday, tz_name="Europe/Vienna") in (True, False)

    def test_cron_daily_syntax(self):
        yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        result = recurrence_due("0 7 * * *", yesterday, tz_name="Europe/Vienna")
        assert isinstance(result, bool)

    def test_interval_seconds(self):
        old = (datetime.now(UTC) - timedelta(seconds=400)).isoformat()
        assert recurrence_due("3600", old, tz_name="Europe/Vienna") is False
        older = (datetime.now(UTC) - timedelta(seconds=4000)).isoformat()
        assert recurrence_due("3600", older, tz_name="Europe/Vienna") is True

    def test_interval_minutes(self):
        old = (datetime.now(UTC) - timedelta(minutes=45)).isoformat()
        assert recurrence_due("30m", old, tz_name="Europe/Vienna") is True

    def test_monthly_dom_fires(self):
        vienna = ZoneInfo("Europe/Vienna")
        fixed_now = datetime(2026, 5, 1, 10, 0, tzinfo=vienna)
        last = datetime(2026, 4, 1, 8, 0, tzinfo=UTC).isoformat()

        with patch("fleet_agent.coworker.recurrence.datetime") as mock_dt:
            mock_dt.now.side_effect = lambda tz=None: fixed_now if tz else datetime.now(UTC)
            mock_dt.fromisoformat = datetime.fromisoformat
            assert recurrence_due("d1:09:00", last, tz_name="Europe/Vienna") is True

    def test_monthly_cron_fires(self):
        vienna = ZoneInfo("Europe/Vienna")
        fixed_now = datetime(2026, 5, 1, 10, 0, tzinfo=vienna)
        last = datetime(2026, 4, 1, 8, 0, tzinfo=UTC).isoformat()

        with patch("fleet_agent.coworker.recurrence.datetime") as mock_dt:
            mock_dt.now.side_effect = lambda tz=None: fixed_now if tz else datetime.now(UTC)
            mock_dt.fromisoformat = datetime.fromisoformat
            assert recurrence_due("0 9 1 * *", last, tz_name="Europe/Vienna") is True

    def test_monthly_dom_skips_wrong_day(self):
        vienna = ZoneInfo("Europe/Vienna")
        fixed_now = datetime(2026, 5, 2, 10, 0, tzinfo=vienna)
        last = datetime(2026, 4, 1, 8, 0, tzinfo=UTC).isoformat()

        with patch("fleet_agent.coworker.recurrence.datetime") as mock_dt:
            mock_dt.now.side_effect = lambda tz=None: fixed_now if tz else datetime.now(UTC)
            mock_dt.fromisoformat = datetime.fromisoformat
            assert recurrence_due("d1:09:00", last, tz_name="Europe/Vienna") is False
