"""Tests for weekly report PDF coworker flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_weekly_report_pdf_happy_path(tmp_path, monkeypatch):
    from fleet_agent.config import settings

    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    md = artifacts / "fleet-pulse-20260530.md"
    md.write_text("# Fleet Pulse\n\n- online: 10/10\n", encoding="utf-8")
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    pdf_out = tmp_path / "output" / "fleet-pulse-20260530.pdf"
    pdf_out.parent.mkdir(parents=True)
    pdf_out.write_bytes(b"%PDF-1.4 fake")

    convert_payload = {
        "success": True,
        "data": {
            "success": True,
            "output": str(pdf_out),
        },
    }

    settings_mock = MagicMock()
    settings_mock.get.side_effect = lambda key, default=None: {
        "coworker_timezone": "Europe/Vienna",
        "heartbeat_email": "test@example.com",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_user": "user@example.com",
        "smtp_pass": "secret",
    }.get(key, default)

    with patch(
        "fleet_agent.coworker.weekly_report_pdf.get_settings_store",
        return_value=settings_mock,
    ), patch(
        "fleet_agent.coworker.common.get_settings_store",
        return_value=settings_mock,
    ), patch(
        "fleet_agent.coworker.weekly_report_pdf.fleet_call",
        AsyncMock(
            return_value={
                "success": True,
                "data": {"content": [__import__("json").dumps(convert_payload)]},
            },
        ),
    ), patch(
        "fleet_agent.mcp.tools.notify.send_email_message",
        AsyncMock(return_value={"success": True, "message": "sent"}),
    ) as mock_mail:
        from fleet_agent.coworker.weekly_report_pdf import run_weekly_report_pdf

        result = await run_weekly_report_pdf(deliver=True)

    assert result["success"] is True
    assert result["pdf_path"] == str(pdf_out)
    mock_mail.assert_called_once()
    assert str(pdf_out) in mock_mail.call_args.kwargs["attachment_paths"]


def test_extract_libreoffice_output_nested():
    import json

    from fleet_agent.coworker.common import extract_libreoffice_output

    result = {
        "success": True,
        "data": {
            "content": [
                json.dumps({
                    "success": True,
                    "data": {"success": True, "output": "C:/tmp/report.pdf"},
                })
            ]
        },
    }
    assert extract_libreoffice_output(result) == "C:/tmp/report.pdf"
