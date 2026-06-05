"""Tests for artifact pack flow."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_artifact_pack_merge(tmp_path, monkeypatch):
    from fleet_agent.config import settings

    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "a.md").write_text("# A\n\n- one\n", encoding="utf-8")
    (artifacts / "b.md").write_text("# B\n\n- two\n", encoding="utf-8")
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    pdf_out = tmp_path / "output" / "artifact-pack-20260530.pdf"
    pdf_out.parent.mkdir(parents=True)
    pdf_out.write_bytes(b"%PDF fake")

    merge_payload = {
        "success": True,
        "data": {"success": True, "output": str(pdf_out)},
    }

    settings_mock = MagicMock()
    settings_mock.get.side_effect = lambda key, default=None: {
        "coworker_timezone": "Europe/Vienna",
        "artifact_pack_glob": "*.md",
        "artifact_pack_max_files": 20,
        "heartbeat_email": "test@example.com",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_user": "user@example.com",
        "smtp_pass": "secret",
    }.get(key, default)

    with patch(
        "fleet_agent.coworker.artifact_pack.get_settings_store",
        return_value=settings_mock,
    ), patch(
        "fleet_agent.coworker.common.get_settings_store",
        return_value=settings_mock,
    ), patch(
        "fleet_agent.coworker.artifact_pack.fleet_call",
        AsyncMock(return_value={"success": True, "data": {"content": [__import__("json").dumps(merge_payload)]}}),
    ) as mock_call, patch(
        "fleet_agent.mcp.tools.notify.send_email_message",
        AsyncMock(return_value={"success": True, "message": "sent"}),
    ):
        from fleet_agent.coworker.artifact_pack import run_artifact_pack

        result = await run_artifact_pack(deliver=True)

    assert result["success"] is True
    assert len(result["sources"]) == 2
    assert mock_call.call_args[0][2]["template"] == "fleet-artifact-pack.odt"
