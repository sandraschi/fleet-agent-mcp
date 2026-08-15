"""sfb crosspost hook - one event, three surfaces (P2 protocol).

Writes board post + Discord message + vla diary entry in a single call,
traceable via board_post_id + discord_message_id in the diary metrics.

Posting budget (spec projects/sandrafleetbot P2):
- work:   <= 2 posts per task_id (start + end)
- thoughts: <= 1 per agent per hour
- alerts: <= 10 per agent per hour (safety cap; alerts are threshold-driven)

Sanitization: Discord carries human summaries only - secrets/credentials are
stripped before the message is built. Raw state stays in the board/diary.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger("fleet_agent.sfb_crosspost")

#: Default SFB Discord channel ids (created 2026-08-15, guild sas1234's server).
DEFAULT_SFB_CHANNELS: dict[str, str] = {
    "work": "1538243264300196031",
    "thoughts": "1538243282759454751",
    "alerts": "1538243284554743861",
}

#: Diary DB (vla-mcp). WAL - safe for concurrent writers; direct insert mirrors
#: vla_mcp.engine.notebook_store exactly (id, notebook, category, title, body,
#: author, tags, metrics, created_at). Prefer the vla_diary tool when vla-mcp
#: runs as an HTTP daemon; direct insert keeps the single-writer invariant.
DEFAULT_NOTEBOOKS_DB = Path("D:/Dev/repos/vla-mcp/data/notebooks/notebooks.sqlite3")

_SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}\b", re.IGNORECASE),
    re.compile(r"\b(token|apikey|api_key|password|passwd|secret|auth)\s*[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9]{32,64}\b"),  # long opaque blobs (tokens, hashes)
]

_budget_lock = threading.Lock()
_budget_file = Path.home() / ".fleet-agent" / "sfb_budget.json"


def _sanitize(text: str) -> str:
    """Strip credentials and long opaque blobs - Discord summaries only."""
    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub("[redacted]", out)
    return out


def _load_budget() -> dict[str, Any]:
    if _budget_file.exists():
        try:
            return json.loads(_budget_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"work": {}, "thoughts": {}, "alerts": {}}


def _save_budget(data: dict[str, Any]) -> None:
    _budget_file.parent.mkdir(parents=True, exist_ok=True)
    _budget_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _budget_check(target: str, agent: str, task_id: str | None) -> tuple[bool, str]:
    """Enforce the posting budget. Returns (allowed, reason)."""
    with _budget_lock:
        data = _load_budget()
        now = datetime.now(UTC).isoformat()
        if target == "work":
            key = f"{agent}:{task_id or 'untracked'}"
            posts = data["work"].get(key, [])
            if len(posts) >= 2:
                return False, "work budget exceeded (max 2 per task: start + end)"
            posts.append(now)
            data["work"][key] = posts
        else:
            key = f"{agent}:{target}"
            stamps = [s for s in data[target].get(key, []) if _age_minutes(s, now) < 60]
            cap = 1 if target == "thoughts" else 10
            if len(stamps) >= cap:
                return False, f"{target} budget exceeded (max {cap}/h)"
            stamps.append(now)
            data[target][key] = stamps
        _save_budget(data)
        return True, ""


def _age_minutes(stamp: str, now: str) -> float:
    try:
        a = datetime.fromisoformat(stamp)
        b = datetime.fromisoformat(now)
        return (b - a).total_seconds() / 60.0
    except Exception:
        return 0.0


def _diary_id() -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{__import__('uuid').uuid4().hex[:6]}"


def log_diary_entry(
    notebook: str,
    category: str,
    title: str,
    body: str,
    author: str,
    tags: list[str],
    metrics: dict[str, Any],
    db_path: Path | None = None,
) -> str:
    """Insert a diary entry directly into vla-mcp's notebooks.sqlite3 (WAL)."""
    path = db_path or Path(settings.vla_notebooks_db)
    entry_id = _diary_id()
    created = datetime.now(UTC).isoformat(timespec="seconds")
    with sqlite3.connect(path, timeout=10) as conn:
        conn.execute(
            "INSERT INTO notebook_entries"
            "(id, notebook, category, title, body, author, tags, metrics, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (
                entry_id,
                notebook,
                category,
                title,
                body,
                author,
                json.dumps(tags),
                json.dumps(metrics),
                created,
            ),
        )
        conn.commit()
    return entry_id


async def crosspost_event(
    target: str,
    title: str,
    body: str,
    *,
    board_channel: str = "dev-worklog",
    task_id: str | None = None,
    category: str = "note",
    agent: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """One event -> board post + Discord message + diary entry.

    target: work | thoughts | alerts (Discord channel + budget bucket).
    board_channel: hub board channel (default dev-worklog; thoughts/alerts
    default to fleet-pulse when not overridden).
    category: diary category (note | repo_fix | decision | blooper).
    """
    agent = agent or settings.agent_name
    if target == "work" and not task_id:
        return {"success": False, "error": "task_id is required for work posts"}

    if target in ("thoughts", "alerts") and board_channel == "dev-worklog":
        board_channel = "fleet-pulse"

    allowed, reason = _budget_check(target, agent, task_id)
    if not allowed:
        return {"success": False, "error": reason, "budgeted": True}

    # 1. Board post (hub is source of truth)
    board_post_id: int | None = None
    if not dry_run:
        async with httpx.AsyncClient(timeout=15) as client:
            headers = (
                {"Authorization": f"Bearer {settings.fleet_hub_token}"}
                if settings.fleet_hub_token
                else {}
            )
            resp = await client.post(
                f"{settings.fleet_hub_url.rstrip('/')}/api/v1/board/posts",
                json={"channel": board_channel, "author": agent, "title": title, "body": body},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            board_post_id = (data.get("post") or {}).get("id")

    # 2. Discord message (sanitized summary) - best effort: Discord rate
    # limits (429) must never fail the board+diary legs of the crosspost.
    discord_message_id: str | None = None
    discord_error: str | None = None
    if not dry_run:
        channel_id = settings.sfb_channels.get(target) or DEFAULT_SFB_CHANNELS[target]
        content = f"**{title}**\n{_sanitize(body)[:1900]}"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{settings.discord_mcp_url.rstrip('/')}/api/v1/channels/{channel_id}/messages",
                    json={"content": content},
                )
                resp.raise_for_status()
                data = resp.json()
                discord_message_id = (
                    str(
                        data.get("message_id")
                        or (data.get("message") or {}).get("id")
                        or data.get("id")
                        or ""
                    )
                    or None
                )
        except Exception as exc:
            discord_error = str(exc)
            logger.warning("sfb crosspost: discord leg failed (%s) - board+diary still posted", exc)

    # 3. Bluesky leg (P6 channel): draft via bluesky-mcp outbox - the human
    # approves in the outbox before anything is published. Best effort, and
    # disabled unless BLUESKY_MCP_URL is configured.
    bluesky_outbox_id: int | None = None
    bluesky_error: str | None = None
    if not dry_run and settings.bluesky_mcp_url:
        try:
            from fastmcp import Client
            from fastmcp.client.transports import StreamableHttpTransport

            async with Client(
                StreamableHttpTransport(f"{settings.bluesky_mcp_url.rstrip('/')}/mcp")
            ) as client:
                result = await client.call_tool(
                    "bluesky_social",
                    {
                        "operation": "outbox_enqueue",
                        "status_text": _sanitize(title)[:280],
                        "source": "fritz-surveil",
                    },
                )
                text = str(result)
                if '"success": true' in text:
                    import re

                    m = re.search(r'"outbox_id"\s*:\s*(\d+)', text)
                    if m:
                        bluesky_outbox_id = int(m.group(1))
        except Exception as exc:
            bluesky_error = str(exc)
            logger.warning("sfb crosspost: bluesky leg failed (%s) - other legs unaffected", exc)

    # 4. Diary entry (metrics carry the trace ids)
    metrics: dict[str, Any] = {
        "outcome": "posted",
        "target": target,
        "board_channel": board_channel,
    }
    if board_post_id is not None:
        metrics["board_post_id"] = board_post_id
    if discord_message_id:
        metrics["discord_message_id"] = discord_message_id
    if bluesky_outbox_id:
        metrics["bluesky_outbox_id"] = bluesky_outbox_id
    if bluesky_error:
        metrics["bluesky_error"] = bluesky_error
    if discord_error:
        metrics["discord_error"] = discord_error
    if task_id:
        metrics["task_id"] = task_id

    diary_entry_id: str | None = None
    if not dry_run:
        diary_entry_id = log_diary_entry(
            notebook="dev",
            category=category,
            title=title,
            body=body,
            author=f"agent:{agent.lower()}",
            tags=[f"agent:{agent.lower()}", f"target:{target}"],
            metrics=metrics,
        )
        logger.info(
            "sfb crosspost %s: board=%s discord=%s diary=%s",
            target,
            board_post_id,
            discord_message_id,
            diary_entry_id,
        )

    return {
        "success": True,
        "dry_run": dry_run,
        "board_post_id": board_post_id,
        "discord_message_id": discord_message_id,
        "diary_entry_id": diary_entry_id,
        "metrics": metrics,
    }
