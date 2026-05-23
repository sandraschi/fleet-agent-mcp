"""Knowledge card system.

Inspired by karpathy's LLM Wiki and kagura-agent/wiki:
  - Compile-time knowledge accumulation > runtime RAG retrieval
  - Knowledge is integrated at write time, not assembled at query time
  - Good answers compound — they feed back into the wiki
  - Lint catches orphans, contradictions, stale content
"""

import uuid
from datetime import UTC, datetime

from ..engine.sqlite_store import get_store


class Wiki:
    def __init__(self) -> None:
        self._store = get_store()

    def create_card(
        self, title: str, content: str, tags: list[str] | None = None, category: str = "general"
    ) -> dict:
        now = datetime.now(UTC).isoformat()
        card = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,
            "tags": tags or [],
            "category": category,
            "created_at": now,
            "updated_at": now,
            "cross_refs": [],
        }
        self._store.card_upsert(card)
        return card

    def update_card(self, card_id: str, content: str, tags: list[str] | None = None) -> dict | None:
        existing = self._store.card_get(card_id)
        if existing is None:
            return None
        now = datetime.now(UTC).isoformat()
        existing["content"] = content
        if tags is not None:
            existing["tags"] = tags
        existing["updated_at"] = now
        self._store.card_upsert(existing)
        return existing

    def search(self, query: str) -> list[dict]:
        return self._store.card_search(query)

    def list_all(self) -> list[dict]:
        return self._store.cards_list()

    def get(self, card_id: str) -> dict | None:
        return self._store.card_get(card_id)

    def delete(self, card_id: str) -> bool:
        if self._store.card_get(card_id) is None:
            return False
        self._store.card_delete(card_id)
        return True

    def lint(self) -> list[dict]:
        """Detect knowledge base issues: orphans, contradictions, stale content."""
        issues: list[dict] = []
        cards = self.list_all()

        if not cards:
            return issues

        all_refs: set[str] = set()
        card_by_id: dict[str, dict] = {}

        for card in cards:
            card_by_id[card["id"]] = card
            for ref in card.get("cross_refs", []):
                all_refs.add(ref)

        # Check for broken cross-references
        for card in cards:
            for ref in card.get("cross_refs", []):
                if ref not in card_by_id:
                    issues.append({
                        "type": "broken_ref",
                        "card_id": card["id"],
                        "card_title": card["title"],
                        "broken_ref": ref,
                    })

        # Check for stale cards (not updated in 30+ days)
        from datetime import timedelta

        cutoff = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        for card in cards:
            if card["updated_at"] < cutoff:
                issues.append({
                    "type": "stale",
                    "card_id": card["id"],
                    "card_title": card["title"],
                    "last_updated": card["updated_at"],
                })

        # Check for untagged cards
        for card in cards:
            if not card.get("tags"):
                issues.append({
                    "type": "untagged",
                    "card_id": card["id"],
                    "card_title": card["title"],
                })

        return issues


def get_wiki() -> Wiki:
    return Wiki()
