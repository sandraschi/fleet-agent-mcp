"""Tests for board pack coworker flow."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_board_pack_merge_path(tmp_path, monkeypatch):
    from fleet_agent.config import settings

    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    md = artifacts / "fleet-pulse-20260530.md"
    md.write_text(
        "# Fleet Pulse\n\n## MCP fleet\n\n- docs: up\n\n## Action items\n\n1. Restart arxiv\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    pdf_out = tmp_path / "output" / "board-pack-20260530.pdf"
    pdf_out.parent.mkdir(parents=True)
    pdf_out.write_bytes(b"%PDF-1.4 fake")

    merge_payload = {
        "success": True,
        "data": {
            "success": True,
            "output": str(pdf_out),
            "merged_odt": str(tmp_path / "output" / "board-pack-20260530.odt"),
        },
    }

    settings_mock = MagicMock()
    settings_mock.get.side_effect = lambda key, default=None: {
        "coworker_timezone": "Europe/Vienna",
        "fleet_repos_root": str(tmp_path),
        "fleet_pulse_repos": [],
        "heartbeat_email": "test@example.com",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_user": "user@example.com",
        "smtp_pass": "secret",
    }.get(key, default)

    with patch(
        "fleet_agent.coworker.board_pack.get_settings_store",
        return_value=settings_mock,
    ), patch(
        "fleet_agent.coworker.common.get_settings_store",
        return_value=settings_mock,
    ), patch(
        "fleet_agent.mcp.tools.fleet_bridge.fleet_discover",
        AsyncMock(return_value={"data": {"servers": [{"online": True}, {"online": False}]}}),
    ), patch(
        "fleet_agent.mcp.tools.heartbeat.heartbeat_status",
        AsyncMock(return_value={"health": {"agent_name": "Fritz", "tasks": {"pending": 2}}}),
    ), patch(
        "fleet_agent.coworker.board_pack.fleet_call",
        AsyncMock(return_value={"success": True, "data": {"content": [__import__("json").dumps(merge_payload)]}}),
    ) as mock_call, patch(
        "fleet_agent.mcp.tools.notify.send_email_message",
        AsyncMock(return_value={"success": True, "message": "sent"}),
    ):
        from fleet_agent.coworker.board_pack import run_board_pack

        result = await run_board_pack(deliver=True)

    assert result["success"] is True
    assert result["pdf_path"] == str(pdf_out)
    mock_call.assert_called_once()
    args = mock_call.call_args[0][2]
    assert args["operation"] == "merge"
    assert args["template"] == "fleet-board-pack.odt"
    assert "TITLE" in args["placeholders"]
