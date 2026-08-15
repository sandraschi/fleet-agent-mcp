"""Proactive schedule suggestions (P4, Viktor steal #1).

Track repeated manual executions of the same key (coworker flow, workflow id,
agent task) and - after SUGGEST_THRESHOLD manual runs - post a one-time
suggestion to the board + diary that the key is a cron candidate. The
suggestion fires once per key (acked flag); the agent/human decides.

Storage: ~/.fleet-agent/suggestions.db (SQLite, WAL).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("fleet_agent.suggestions")

_DB_PATH = Path.home() / ".fleet-agent" / "suggestions.db"
_lock = threading.Lock()

SUGGEST_THRESHOLD = 3
SUGGEST_WINDOW_DAYS = 7

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    first_ts TEXT NOT NULL,
    last_ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS suggestions (
    key TEXT PRIMARY KEY,
    suggested_at TEXT NOT NULL,
    message TEXT NOT NULL
);
"""


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(UTC).isoformat()


def record_manual_usage(key: str, kind: str = "flow") -> dict[str, Any]:
    """Increment a manual-run counter; returns a suggestion if newly triggered."""
    with _lock:
        conn = _conn()
        try:
            row = conn.execute("SELECT * FROM usage WHERE key=?", (key,)).fetchone()
            now = _now()
            if row is None:
                conn.execute(
                    "INSERT INTO usage(key, kind, count, first_ts, last_ts) VALUES (?,?,1,?,?)",
                    (key, kind, now, now),
                )
                count = 1
            else:
                count = int(row["count"]) + 1
                conn.execute(
                    "UPDATE usage SET count=?, last_ts=? WHERE key=?",
                    (count, now, key),
                )
            conn.commit()

            suggested = conn.execute(
                "SELECT message FROM suggestions WHERE key=?", (key,)
            ).fetchone()

            window_ok = True
            if row is not None:
                try:
                    first = datetime.fromisoformat(row["first_ts"])
                    if datetime.now(UTC) - first > timedelta(days=SUGGEST_WINDOW_DAYS):
                        window_ok = False
                except Exception:
                    pass

            if suggested is None and count >= SUGGEST_THRESHOLD and window_ok:
                message = (
                    f"`{key}` has been run manually {count} times in the last "
                    f"{SUGGEST_WINDOW_DAYS} days - consider a cron schedule "
                    f"(agent_schedule_create or coworker flow cron)."
                )
                conn.execute(
                    "INSERT INTO suggestions(key, suggested_at, message) VALUES (?,?,?)",
                    (key, now, message),
                )
                conn.commit()
                return {"suggested": True, "key": key, "count": count, "message": message}
            return {"suggested": False, "key": key, "count": count}
        finally:
            conn.close()


def list_suggestions() -> dict[str, Any]:
    conn = _conn()
    try:
        rows = conn.execute("SELECT * FROM suggestions ORDER BY suggested_at DESC").fetchall()
        items = []
        for row in rows:
            usage = conn.execute(
                "SELECT count, last_ts FROM usage WHERE key=?", (row["key"],)
            ).fetchone()
            items.append(
                {
                    "key": row["key"],
                    "suggested_at": row["suggested_at"],
                    "message": row["message"],
                    "runs": int(usage["count"]) if usage else 0,
                    "last_run": usage["last_ts"] if usage else None,
                }
            )
        return {"suggestions": items, "count": len(items)}
    finally:
        conn.close()


def ack_suggestion(key: str) -> dict[str, Any]:
    """Remove a suggestion (acked: the cron was created or declined)."""
    with _lock:
        conn = _conn()
        try:
            cur = conn.execute("DELETE FROM suggestions WHERE key=?", (key,))
            conn.commit()
            return {"success": cur.rowcount > 0, "key": key}
        finally:
            conn.close()


def suggestion_summary_json(key: str) -> str:
    return json.dumps(record_manual_usage(key))
