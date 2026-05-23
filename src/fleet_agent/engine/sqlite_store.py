"""SQLite persistence for workflows, instances, todo items, and memory cards."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..config import settings

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS workflows (
    name TEXT PRIMARY KEY,
    description TEXT,
    definition_json TEXT NOT NULL,
    source_path TEXT,
    registered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS instances (
    workflow_name TEXT NOT NULL,
    current_node TEXT NOT NULL,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    history_json TEXT DEFAULT '[]',
    archived INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_name TEXT NOT NULL,
    event TEXT NOT NULL,
    details TEXT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS todo_items (
    id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    group_name TEXT DEFAULT 'self',
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    recurrence TEXT,
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS memory_cards (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    cross_refs TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS memory_projects (
    id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evolution_log (
    id TEXT PRIMARY KEY,
    correction TEXT NOT NULL,
    lesson TEXT NOT NULL,
    context TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
"""


class SqliteStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or settings.db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(DB_SCHEMA)

    # ── Workflows ──────────────────────────────────────────

    def save_workflow(self, wf: object) -> None:
        from .workflow_loader import Workflow
        wf_data: Workflow = wf  # type: ignore[assignment]
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO workflows
                   (name, description, definition_json, source_path, registered_at)
                   VALUES (?, ?, ?, ?, datetime('now'))""",
                (
                    wf_data.name,
                    wf_data.description,
                    json.dumps(wf_data.to_dict()),
                    wf_data.source_path,
                ),
            )

    def list_workflows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, description, source_path, registered_at FROM workflows ORDER BY name"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_workflow(self, name: str) -> Any | None:
        from .workflow_loader import Branch, Workflow, WorkflowNode
        with self._connect() as conn:
            row = conn.execute(
                "SELECT definition_json FROM workflows WHERE name = ?", (name,)
            ).fetchone()
            if row is None:
                return None
            d = json.loads(row[0])
            nodes: dict[str, WorkflowNode] = {}
            for k, v in d.get("nodes", {}).items():
                branches = [Branch(**b) for b in v.get("branches", [])]
                nodes[k] = WorkflowNode(
                    task=v.get("task", ""),
                    next_node=v.get("next"),
                    branches=branches,
                    terminal=v.get("terminal", False),
                )
            return Workflow(
                name=d["name"],
                description=d.get("description", ""),
                start=d["start"],
                nodes=nodes,
                source_path=d.get("source_path", ""),
            )

    # ── Instances ──────────────────────────────────────────

    def save_instance(self, instance: object) -> None:
        from .state_machine import WorkflowInstance
        inst: WorkflowInstance = instance  # type: ignore[assignment]
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO instances
                   (workflow_name, current_node, started_at, updated_at, history_json, archived)
                   VALUES (?, ?, ?, ?, ?, 0)""",
                (
                    inst.workflow_name,
                    inst.current_node,
                    inst.started_at,
                    inst.updated_at,
                    json.dumps(inst.history),
                ),
            )

    def get_active_instance(self) -> Any | None:
        from .state_machine import WorkflowInstance
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM instances WHERE archived = 0 ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            return WorkflowInstance(
                workflow_name=row["workflow_name"],
                current_node=row["current_node"],
                started_at=row["started_at"],
                updated_at=row["updated_at"],
                history=json.loads(row["history_json"]),
            )

    def list_active_instances(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT workflow_name, current_node, started_at, updated_at "
                "FROM instances WHERE archived = 0 ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def archive_instance(self, instance: object) -> None:
        from .state_machine import WorkflowInstance
        inst: WorkflowInstance = instance  # type: ignore[assignment]
        with self._connect() as conn:
            conn.execute(
                "UPDATE instances SET archived = 1 WHERE workflow_name = ? AND started_at = ?",
                (inst.workflow_name, inst.started_at),
            )

    def get_execution_log(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM execution_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def log_event(self, workflow_name: str, event: str, details: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO execution_log (workflow_name, event, details, timestamp) "
                "VALUES (?, ?, ?, datetime('now'))",
                (workflow_name, event, details),
            )

    # ── Todo Items ─────────────────────────────────────────

    def todo_upsert(self, item: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO todo_items
                   (id, task, group_name, priority, status, created_at,
                    updated_at, completed_at, recurrence, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item["id"],
                    item["task"],
                    item.get("group", "self"),
                    item.get("priority", "medium"),
                    item.get("status", "pending"),
                    item.get("created_at", ""),
                    item.get("updated_at", ""),
                    item.get("completed_at"),
                    item.get("recurrence"),
                    json.dumps(item.get("metadata", {})),
                ),
            )

    def todo_list(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM todo_items WHERE status = ? ORDER BY priority, created_at",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM todo_items ORDER BY status, priority, created_at"
                ).fetchall()
            return [dict(r) for r in rows]

    def todo_get(self, item_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM todo_items WHERE id = ?", (item_id,)).fetchone()
            return dict(row) if row else None

    def todo_delete(self, item_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM todo_items WHERE id = ?", (item_id,))

    def todo_stale(self, days: int = 3) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM todo_items
                   WHERE status = 'pending'
                   AND updated_at < datetime('now', ?)""",
                (f"-{days} days",),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Memory Cards ───────────────────────────────────────

    def card_upsert(self, card: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO memory_cards
                   (id, title, content, tags, category, created_at, updated_at, cross_refs)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    card["id"],
                    card["title"],
                    card["content"],
                    ",".join(card.get("tags", [])),
                    card.get("category", "general"),
                    card.get("created_at", ""),
                    card.get("updated_at", ""),
                    ",".join(card.get("cross_refs", [])),
                ),
            )

    def card_get(self, card_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM memory_cards WHERE id = ?", (card_id,)
            ).fetchone()
            if row is None:
                return None
            d = dict(row)
            d["tags"] = [t for t in d["tags"].split(",") if t]
            d["cross_refs"] = [t for t in d["cross_refs"].split(",") if t]
            return d

    def card_search(self, query: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM memory_cards
                   WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
                   ORDER BY updated_at DESC LIMIT 50""",
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["tags"] = [t for t in d["tags"].split(",") if t]
                d["cross_refs"] = [t for t in d["cross_refs"].split(",") if t]
                results.append(d)
            return results

    def cards_list(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_cards ORDER BY updated_at DESC"
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["tags"] = [t for t in d["tags"].split(",") if t]
                d["cross_refs"] = [t for t in d["cross_refs"].split(",") if t]
                results.append(d)
            return results

    def card_delete(self, card_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM memory_cards WHERE id = ?", (card_id,))

    # ── Memory Projects ────────────────────────────────────

    def project_upsert(self, item: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO memory_projects
                   (id, project_name, content, tags, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    item["id"],
                    item["project_name"],
                    item["content"],
                    ",".join(item.get("tags", [])),
                    item.get("created_at", ""),
                    item.get("updated_at", ""),
                ),
            )

    def project_list(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_projects ORDER BY updated_at DESC"
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["tags"] = [t for t in d["tags"].split(",") if t]
                results.append(d)
            return results

    def project_get(self, project_name: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM memory_projects WHERE project_name = ?", (project_name,)
            ).fetchone()
            if row is None:
                return None
            d = dict(row)
            d["tags"] = [t for t in d["tags"].split(",") if t]
            return d

    # ── Evolution Log ──────────────────────────────────────

    def evolution_add(self, entry: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO evolution_log
                   (id, correction, lesson, context, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    entry["id"],
                    entry["correction"],
                    entry["lesson"],
                    entry.get("context", ""),
                    entry.get("created_at", ""),
                ),
            )

    def evolution_list(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM evolution_log ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def evolution_lint(self) -> list[dict[str, Any]]:
        """Detect contradictions, duplicates, or stale entries."""
        # Simple check: duplicate lessons
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT lesson, COUNT(*) as cnt FROM evolution_log
                   GROUP BY lesson HAVING cnt > 1"""
            ).fetchall()
            return [
                {"type": "duplicate_lesson", "lesson": r["lesson"], "count": r["cnt"]}
                for r in rows
            ]


_store: SqliteStore | None = None


def get_store() -> SqliteStore:
    global _store
    if _store is None:
        _store = SqliteStore()
    return _store
