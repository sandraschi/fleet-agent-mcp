"""Tests for Morning Fleet Pulse report formatting."""

from fleet_agent.coworker.bootstrap import ensure_coworker_tasks, is_fleet_pulse_task
from fleet_agent.coworker.fleet_pulse import format_fleet_pulse_report


class TestFleetPulseReport:
    def test_format_report_sections(self):
        report = format_fleet_pulse_report(
            pulse_date="2026-05-30 07:00 CEST",
            health={
                "health": {
                    "agent_name": "Fritz",
                    "uptime_human": "1h 2m",
                    "tasks": {"pending": 3},
                    "memory_cards": 5,
                    "active_workflow": None,
                }
            },
            discovery={
                "data": {
                    "servers": [
                        {"alias": "docs", "online": True, "tool_count": 4},
                        {"alias": "arxiv", "online": False, "tool_count": 0, "error": "connection refused"},
                    ]
                }
            },
            git_rows=[
                {"repo": "fleet-agent-mcp", "status": "## main\n", "last_commit": "abc fix"},
                {"repo": "missing", "error": "path missing"},
            ],
        )
        assert "# Fleet Pulse" in report
        assert "Fritz" in report
        assert "docs" in report
        assert "arxiv" in report
        assert "fleet-agent-mcp" in report
        assert "Action items" in report

    def test_is_fleet_pulse_task_metadata(self):
        assert is_fleet_pulse_task({"task": "anything", "metadata_json": '{"coworker": "fleet_pulse"}'})

    def test_is_fleet_pulse_task_text(self):
        assert is_fleet_pulse_task({"task": "Morning Fleet Pulse please"})


class TestCoworkerBootstrap:
    def test_ensure_idempotent(self, tmp_path, monkeypatch):
        from fleet_agent.config import settings
        from fleet_agent.engine.sqlite_store import SqliteStore

        db = tmp_path / "test.db"
        monkeypatch.setattr(settings, "db_path", db)
        monkeypatch.setattr(settings, "data_dir", tmp_path)

        import fleet_agent.engine.sqlite_store as ss
        ss._store = None

        first = ensure_coworker_tasks()
        second = ensure_coworker_tasks()
        assert len(first["seeded"]) >= 1
        assert second["seeded"] == []

        store = SqliteStore(db)
        task = store.todo_get("coworker-fleet-pulse")
        assert task is not None
        assert task["recurrence"] == "07:00"
        assert store.todo_get("coworker-inbox-briefing") is not None
