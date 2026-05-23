"""In-memory ring-buffer log store with SSE streaming support."""

import asyncio
import json
from collections import deque
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class LogStore:
    def __init__(self, max_entries: int = 500) -> None:
        self._logs: deque[dict[str, Any]] = deque(maxlen=max_entries)
        self._subscribers: list[asyncio.Queue] = []

    def add(self, level: str, message: str, source: str = "system") -> dict:
        entry = {
            "id": str(uuid4())[:8],
            "level": level,
            "message": message,
            "source": source,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._logs.append(entry)
        payload = json.dumps(entry)
        # Notify SSE subscribers
        dead: list[asyncio.Queue] = []
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.remove(q)
        return entry

    def recent(self, limit: int = 100) -> list[dict]:
        return list(self._logs)[-limit:]

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)


_store: LogStore | None = None


def get_log_store() -> LogStore:
    global _store
    if _store is None:
        _store = LogStore()
    return _store
