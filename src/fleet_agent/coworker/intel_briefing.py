"""AIWatcher intel slice for Office Day Prep."""

from __future__ import annotations

from typing import Any

from .common import fleet_call, parse_fleet_payload

URGENCY_PULSE_THRESHOLD = 8.0
READLY_RELEVANCE_PULSE_THRESHOLD = 7.5


def _is_readly_longform(item: dict[str, Any]) -> bool:
    tags = item.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    source = (item.get("source") or "").lower()
    feed_type = (item.get("feed_type") or "").lower()
    if feed_type == "readly":
        return True
    if source.startswith("readly:"):
        return True
    return any(str(t).lower() in ("readly", "longform") for t in tags)


def qualifies_for_pulse_task(
    item: dict[str, Any],
    *,
    urgency_threshold: float = URGENCY_PULSE_THRESHOLD,
    readly_relevance_threshold: float = READLY_RELEVANCE_PULSE_THRESHOLD,
) -> bool:
    """Breaking news: urgency ≥ threshold. Readly longform: relevance ≥ threshold."""
    urgency = item.get("urgency")
    relevance = item.get("relevance")
    if isinstance(urgency, (int, float)) and float(urgency) >= urgency_threshold:
        return True
    if _is_readly_longform(item) and isinstance(relevance, (int, float)):
        return float(relevance) >= readly_relevance_threshold
    return False


def format_intel_section(items: list[dict[str, Any]], *, hours: int) -> str:
    lines = [f"## AI intel (last {hours}h)", ""]
    if not items:
        lines.append("_No scored items in window — run `just poll` / distillation on aiwatcher._")
        return "\n".join(lines)

    for i, item in enumerate(items[:8], 1):
        urgency = item.get("urgency")
        score = f"{urgency:.1f}" if isinstance(urgency, (int, float)) else "—"
        title = (item.get("title") or "?")[:100]
        source = item.get("source") or ""
        lines.append(f"{i}. **[{score}]** {title}" + (f" — _{source}_" if source else ""))
        summary = (item.get("summary") or "").strip()
        if summary:
            lines.append(f"   {summary[:200]}")
    return "\n".join(lines)


async def fetch_intel_briefing(
    *,
    hours: int = 24,
    limit: int = 10,
    urgency_task_threshold: float = URGENCY_PULSE_THRESHOLD,
    readly_relevance_threshold: float = READLY_RELEVANCE_PULSE_THRESHOLD,
) -> dict[str, Any]:
    """Call aiwatcher get_top_items; return markdown section and hot items for pulse tasks."""
    result = await fleet_call(
        "aiwatcher",
        "get_top_items",
        {"hours": hours, "limit": limit},
    )
    if not result.get("success"):
        return {
            "ok": False,
            "section": "## AI intel\n\n_aiwatcher offline or unreachable — skip intel slice._",
            "hot_items": [],
            "message": result.get("message", "fleet_call failed"),
        }

    payload = parse_fleet_payload(result)
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "section": "## AI intel\n\n_unexpected aiwatcher response format._",
            "hot_items": [],
            "message": "bad payload",
        }

    items = payload.get("items") or []
    hot = [
        it
        for it in items
        if qualifies_for_pulse_task(
            it,
            urgency_threshold=urgency_task_threshold,
            readly_relevance_threshold=readly_relevance_threshold,
        )
    ]
    readly_hot = sum(1 for it in hot if _is_readly_longform(it))
    return {
        "ok": True,
        "section": format_intel_section(items, hours=hours),
        "hot_items": hot,
        "count": len(items),
        "message": (
            f"{len(items)} items, {len(hot)} pulse-worthy "
            f"(urgency ≥ {urgency_task_threshold} or readly relevance ≥ {readly_relevance_threshold}; "
            f"{readly_hot} readly)"
        ),
    }
