"""Tests for devices-mcp priority watch."""

from unittest.mock import AsyncMock, patch

import pytest

from fleet_agent.coworker.devices_watch import format_devices_report, run_devices_watch


class TestDevicesWatch:
    def test_format_report(self):
        payload = {
            "timestamp": "2026-06-07T12:00:00+00:00",
            "incident_count": 1,
            "critical_count": 1,
            "highest_urgency": 10.0,
            "incidents": [{
                "title": "CO alert",
                "urgency": 10,
                "kind": "co_alarm",
                "source": "nest",
            }],
        }
        new = [{
            "id": "nest-co-1",
            "title": "CO alert",
            "urgency": 10,
            "kind": "co_alarm",
            "source": "nest",
            "description": "CO emergency",
        }]
        report = format_devices_report(payload, new_incidents=new)
        assert "CO alert" in report
        assert "New incidents" in report

    @pytest.mark.asyncio
    async def test_run_no_new_incidents(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fleet_agent.coworker.devices_watch.settings.data_dir", tmp_path)
        payload = {
            "success": True,
            "incident_count": 0,
            "critical_count": 0,
            "incidents": [],
            "sources": {},
        }
        with patch(
            "fleet_agent.coworker.devices_watch.fetch_priority_incidents",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = payload
            result = await run_devices_watch(deliver=True)
            assert result["success"] is True
            assert result["stats"]["new_count"] == 0
