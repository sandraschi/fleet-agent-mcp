"""Shared pytest fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _isolated_fleet_agent_db(tmp_path, monkeypatch):
    """Redirect the SQLite store and state machine to a per-test temp DB.

    Without this, StateMachine.start(...) (used throughout test_state_machine.py,
    test_gate_engine.py, etc.) wrote workflow instances straight into the real
    ~/.fleet-agent/fleet-agent.db. Since the fleet-agent-mcp service normally
    runs live in the background, its agentic loop would pick those test
    instances up and tick them for real - including real Ollama LLM calls.
    That is how ~275 stray gate-test/typed-flow/agent-demo instances
    accumulated over three weeks and eventually starved real task processing
    (see agentic_loop._reap_if_stalled for the runtime-side hard ceiling that
    now also bounds this class of bug).
    """
    from fleet_agent import config as config_mod
    from fleet_agent.engine import sqlite_store as store_mod
    from fleet_agent.engine import state_machine as sm_mod

    test_db = tmp_path / "test-fleet-agent.db"
    monkeypatch.setattr(config_mod.settings, "db_path", test_db)
    store_mod._store = store_mod.SqliteStore(db_path=test_db)
    sm_mod._state_machine = sm_mod.StateMachine()
    yield
    store_mod._store = None
    sm_mod._state_machine = None
