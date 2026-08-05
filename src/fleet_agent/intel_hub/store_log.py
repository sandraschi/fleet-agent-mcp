"""Ring-buffer log store for Fleet Hub — recent log entries from all fleet repos."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .store import reports_root

_MAX_LOG_ENTRIES = 500


def _log_path() -> Path:
    return reports_root() / "logs.json"


def _load_logs() -> list[dict[str, Any]]:
    path = _log_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_logs(entries: list[dict[str, Any]]) -> None:
    path = _log_path()
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def ingest_log(
    *,
    message: str,
    level: str = "ERROR",
    source: str = "unknown",
    repo: str = "",
    details: str = "",
) -> dict[str, Any]:
    """Append a log entry to the ring buffer. Returns the entry metadata."""
    if not message.strip():
        raise ValueError("message is required")

    entry: dict[str, Any] = {
        "id": datetime.now(UTC).strftime("%Y%m%d%H%M%S%f"),
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level.upper()[:10],
        "source": source[:60],
        "repo": repo[:80],
        "message": message[:500],
        "details": details[:2000],
    }

    logs = _load_logs()
    logs.insert(0, entry)
    logs = logs[:_MAX_LOG_ENTRIES]
    _save_logs(logs)
    return {"success": True, "entry": entry, "total_entries": len(logs)}


def list_logs(
    *,
    limit: int = 50,
    level: str | None = None,
    source: str | None = None,
    repo: str | None = None,
) -> list[dict[str, Any]]:
    """Return recent log entries, optionally filtered."""
    logs = _load_logs()
    if level:
        logs = [e for e in logs if e.get("level", "").upper() == level.upper()]
    if source:
        logs = [e for e in logs if source.lower() in e.get("source", "").lower()]
    if repo:
        logs = [e for e in logs if repo.lower() in e.get("repo", "").lower()]
    return logs[: max(1, limit)]


def log_stats() -> dict[str, Any]:
    """Aggregate counts for the index page."""
    logs = _load_logs()
    counts: dict[str, int] = {}
    sources: set[str] = set()
    for e in logs:
        lvl = e.get("level", "UNKNOWN")
        counts[lvl] = counts.get(lvl, 0) + 1
        if e.get("source"):
            sources.add(str(e["source"]))
    return {
        "total": len(logs),
        "by_level": counts,
        "sources": sorted(sources),
        "errors_24h": sum(
            1
            for e in logs
            if e.get("level") in ("ERROR", "CRITICAL")
            and str(e.get("timestamp", ""))[:10] == datetime.now(UTC).strftime("%Y-%m-%d")
        ),
    }
