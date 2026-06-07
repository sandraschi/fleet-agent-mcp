"""Tests for Fritz → AIWatcher fleet event push."""

from unittest.mock import AsyncMock, patch

import pytest

from fleet_agent.coworker.aiwatcher_ingest import push_fleet_event


class TestAiwatcherIngest:
    @pytest.mark.asyncio
    async def test_push_via_mcp(self):
        with patch(
            "fleet_agent.coworker.aiwatcher_ingest.fleet_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {
                "success": True,
                "data": {"content": ['{"success": true, "inserted": true, "guid": "fleet:abc"}']},
            }
            result = await push_fleet_event(
                title="Fleet Pulse — 12/12 online",
                summary="All healthy",
                urgency_hint=5.0,
            )
            assert result.get("success") is True
            assert result.get("via") == "mcp"
            mock_call.assert_called_once()
            args = mock_call.call_args[0]
            assert args[0] == "aiwatcher"
            assert args[1] == "ingest_fleet_event"

    @pytest.mark.asyncio
    async def test_push_rest_fallback(self):
        with patch(
            "fleet_agent.coworker.aiwatcher_ingest.fleet_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"success": False, "message": "offline"}
            with patch(
                "fleet_agent.coworker.aiwatcher_ingest._push_fleet_event_rest",
                new_callable=AsyncMock,
            ) as mock_rest:
                mock_rest.return_value = {"success": True, "via": "rest", "inserted": True}
                result = await push_fleet_event(title="Test event")
                assert result["via"] == "rest"
                mock_rest.assert_called_once()
