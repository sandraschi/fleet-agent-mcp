"""Tests for urgent alert gating."""

from unittest.mock import AsyncMock, patch

import pytest

from fleet_agent.coworker.urgent_notify import (
    deliver_urgent_alert,
    should_send_urgent,
    urgent_threshold,
)


class TestUrgentGating:
    def test_threshold_default(self):
        assert urgent_threshold() == 8.0

    def test_should_send_critical(self):
        assert should_send_urgent(critical=True) is True

    def test_should_skip_low_urgency(self):
        assert should_send_urgent(urgency=5.0) is False

    def test_should_send_high_urgency(self):
        assert should_send_urgent(urgency=8.5) is True

    @pytest.mark.asyncio
    async def test_deliver_skipped(self):
        result = await deliver_urgent_alert(
            subject="Test",
            body="body",
            reason="test",
            urgency=3.0,
        )
        assert result.get("skipped") is True

    @pytest.mark.asyncio
    async def test_deliver_critical(self):
        with patch(
            "fleet_agent.coworker.urgent_notify.deliver_report",
            new_callable=AsyncMock,
        ) as mock_email:
            mock_email.return_value = {"success": True}
            with patch(
                "fleet_agent.coworker.common.fleet_call",
                new_callable=AsyncMock,
            ) as mock_inbox:
                mock_inbox.return_value = {"success": True}
                result = await deliver_urgent_alert(
                    subject="Pipeline down",
                    body="arxiv stale",
                    reason="fleet pulse",
                    critical=True,
                    hub_url="http://127.0.0.1:11027/reports/abc",
                )
                assert result.get("skipped") is False
                mock_email.assert_called_once()
