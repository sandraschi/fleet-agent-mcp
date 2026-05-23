"""Evolution log — every mistake, every correction, every lesson.

Inspired by kagura-agent: "When I mess up, it's in the git history.
When I learn something, it goes into my wiki. No curation, no hiding."
"""

import uuid
from datetime import UTC, datetime

from ..engine.sqlite_store import get_store


class EvolutionLog:
    def __init__(self) -> None:
        self._store = get_store()

    def record(self, correction: str, lesson: str, context: str = "") -> dict:
        entry = {
            "id": str(uuid.uuid4())[:8],
            "correction": correction,
            "lesson": lesson,
            "context": context,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._store.evolution_add(entry)
        return entry

    def list_entries(self, limit: int = 100) -> list[dict]:
        return self._store.evolution_list(limit)

    def lint(self) -> list[dict]:
        """Detect duplicate lessons that might indicate a persistent pattern."""
        return self._store.evolution_lint()

    def stats(self) -> dict:
        entries = self.list_entries(1000)
        total = len(entries)
        if total == 0:
            return {"total_corrections": 0, "unique_lessons": 0}

        unique_lessons = len({e["lesson"] for e in entries})
        return {
            "total_corrections": total,
            "unique_lessons": unique_lessons,
            "recent": entries[:5] if entries else [],
        }


def get_evolution_log() -> EvolutionLog:
    return EvolutionLog()
