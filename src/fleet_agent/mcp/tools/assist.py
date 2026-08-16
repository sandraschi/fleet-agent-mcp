"""Voice assistant intents — timers, Plex playback, and media search.

Fired by the Voice Command Bus: spoken commands like
"set timer twenty minutes, then play desguello" land here after the router
matches the `fritz`/`plexy` keywords. Clauses are split on "then" / "and"
and each is dispatched: timers to speech-mcp, playback to VLC (Plex stream),
media/book search to plex-mcp / calibre-mcp.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.assist")

_VLC_CANDIDATES = (
    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
)


def _find_vlc() -> str | None:
    """Locate VLC: FLEET_VLC_PATH override, else common install paths."""
    override = os.environ.get("FLEET_VLC_PATH", "").strip()
    if override and Path(override).is_file():
        return override
    return next((p for p in _VLC_CANDIDATES if Path(p).is_file()), None)


def _plex_credentials() -> tuple[str, str] | None:
    base = os.environ.get("PLEX_BASE_URL", "").strip().rstrip("/") or os.environ.get(
        "PLEX_URL", ""
    ).strip().rstrip("/")
    token = os.environ.get("PLEX_TOKEN", "").strip()
    if not base or not token:
        return None
    return base, token


async def _plex_direct_url(rating_key: str) -> str | None:
    """Resolve the direct playable part URL for a media item.

    The HLS transcode endpoint (start.m3u8) rejects ad-hoc URLs; the direct
    /library/parts/.../file stream is served as video/mp4 and VLC plays it
    natively.
    """
    import httpx

    creds = _plex_credentials()
    if creds is None:
        return None
    base, token = creds
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{base}/library/metadata/{rating_key}",
                headers={"X-Plex-Token": token, "Accept": "application/json"},
            )
            resp.raise_for_status()
            container = resp.json().get("MediaContainer") or {}
            items = container.get("Metadata") or []
            if not items:
                return None
            media = (items[0].get("Media") or [{}])[0]
            parts = media.get("Part") or []
            if not parts:
                return None
            part_key = parts[0].get("key")
            if not part_key:
                return None
            if part_key.startswith("/"):
                return f"{base}{part_key}?X-Plex-Token={token}"
            return f"{base}/{part_key}?X-Plex-Token={token}"
    except Exception as exc:
        logger.warning("Plex direct URL resolution failed: %s", exc)
        return None


async def _plex_rest_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search Plex directly via REST (no plex-mcp env dependency)."""
    import httpx

    creds = _plex_credentials()
    if creds is None:
        return []
    base, token = creds
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{base}/search",
                params={"query": query, "type": "1"},
                headers={"X-Plex-Token": token, "Accept": "application/json"},
            )
            resp.raise_for_status()
            container = resp.json().get("MediaContainer") or {}
            return [i for i in (container.get("Metadata") or []) if isinstance(i, dict)]
    except Exception as exc:
        logger.warning("Plex REST search failed: %s", exc)
        return []


def _launch_vlc(url: str, vlc: str) -> None:
    """Detached VLC launch (Windows)."""
    creationflags = 0x08000000 | 0x00000010 if os.name == "nt" else 0  # DETACHED + NEW_CONSOLE
    subprocess.Popen(
        [vlc, "--fullscreen", url],
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


_WORD_NUMBERS: dict[str, int] = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "ninety": 90,
}

_UNITS: dict[str, int] = {
    "second": 1,
    "seconds": 1,
    "secs": 1,
    "sec": 1,
    "minute": 60,
    "minutes": 60,
    "mins": 60,
    "min": 60,
    "hour": 3600,
    "hours": 3600,
    "hrs": 3600,
    "hr": 3600,
}


def split_clauses(text: str) -> list[str]:
    """Split a spoken chain into clauses on 'then' / 'and' boundaries."""
    parts = re.split(r"\b(?:and\s+)?then\b|\s*,\s*(?:then\s+)?", text, flags=re.IGNORECASE)
    clauses = [p.strip(" ,.") for p in parts if p.strip(" ,.")]
    if len(clauses) == 1:
        pair = re.split(r"\s+and\s+", clauses[0], maxsplit=1, flags=re.IGNORECASE)
        if len(pair) == 2 and any(v in pair[1].lower() for v in ("play", "timer", "reminder")):
            clauses = [s.strip() for s in pair]
    return clauses


def parse_duration(clause: str) -> tuple[int, str] | None:
    """Parse 'twenty minutes' -> (1200, '20 minutes')."""
    text = clause.lower()
    for unit_word, mult in sorted(_UNITS.items(), key=lambda kv: -len(kv[0])):
        m = re.search(rf"(.+?)\s+{unit_word}\b", text)
        if not m:
            continue
        raw = m.group(1).strip()
        # Walk the tokens backwards from the unit: accumulate contiguous
        # number words / digits ("twenty five" -> 25, "timer for ninety" -> 90).
        n = 0
        found = False
        for token in reversed(raw.split()):
            if token.isdigit():
                n += int(token)
                found = True
                continue
            word_n = _WORD_NUMBERS.get(token)
            if word_n is None:
                break
            n += word_n
            found = True
        if not found:
            continue
        return n * mult, f"{n} {unit_word}"
    return None


def _plex_items(data: Any) -> list[dict[str, Any]]:
    """Tolerant extraction of media items from a search payload."""
    if isinstance(data, list):
        return [i for i in data if isinstance(i, dict)]
    if isinstance(data, dict):
        for key in ("items", "results", "books", "data"):
            if isinstance(data.get(key), list):
                return [i for i in data[key] if isinstance(i, dict)]
        container = data.get("MediaContainer") or {}
        if isinstance(container, dict):
            for key in ("Metadata", "Directory", "Video", "Track"):
                if isinstance(container.get(key), list):
                    return [i for i in container[key] if isinstance(i, dict)]
    return []


def _item_title(item: dict[str, Any], fallback: str) -> str:
    return str(item.get("title") or item.get("name") or item.get("label") or fallback)


async def _plex_play(query: str) -> dict[str, Any]:
    """Search Plex and play the top match — VLC preferred, client fallback."""
    from .dev import unwrap_bridge
    from .fleet_bridge import fleet_call_tool

    items = await _plex_rest_search(query)
    if not items:
        return {"success": False, "message": f"No Plex results for '{query}'."}
    first = items[0]
    key = first.get("ratingKey") or first.get("key") or first.get("media_key")
    title = _item_title(first, query)
    if key is None:
        return {"success": False, "message": f"Found '{title}' but it has no playable key."}

    vlc = _find_vlc()
    if vlc and os.name == "nt":
        url = await _plex_direct_url(str(key))
        if url is None:
            return {
                "success": False,
                "message": (
                    "Could not resolve a direct stream for "
                    f"'{title}' (PLEX_BASE_URL/PLEX_TOKEN set? Plex reachable?)."
                ),
            }
        try:
            await asyncio.to_thread(_launch_vlc, url, vlc)
        except Exception as exc:
            logger.warning("VLC launch failed: %s", exc)
            return {"success": False, "message": f"Could not start VLC: {exc}"}
        return {"success": True, "message": f"Playing {title} in VLC."}

    # Fallback: play on an active Plex client via plex-mcp
    play = await fleet_call_tool(
        server="plex",
        tool="plex_streaming",
        arguments={"operation": "play", "media_key": str(key)},
    )
    play_payload = unwrap_bridge(play)
    ok = bool(play.get("success")) and bool(play_payload.get("success", True))
    return {
        "success": ok,
        "message": (
            f"Playing {title} on Plex."
            if ok
            else str(play_payload.get("message") or "Playback failed.")
        ),
    }


async def _plex_control(verb: str) -> dict[str, Any]:
    """Map spoken playback verbs to plex_streaming operations."""
    from .dev import unwrap_bridge
    from .fleet_bridge import fleet_call_tool

    mapping = {
        "pause": "pause",
        "stop": "stop",
        "resume": "play",
        "continue": "play",
        "next": "skip_next",
        "skip": "skip_next",
        "previous": "skip_previous",
    }
    verb_l = (verb or "").strip().lower()
    op = next((v for k, v in mapping.items() if verb_l.startswith(k) or k in verb_l), None)
    if op is None:
        return {"success": False, "message": f"Unknown playback command: '{verb}'"}
    result = await fleet_call_tool(
        server="plex",
        tool="plex_streaming",
        arguments={"operation": op},
    )
    payload = unwrap_bridge(result)
    ok = bool(result.get("success")) and bool(payload.get("success", True))
    return {
        "success": ok,
        "message": (
            f"Playback {op.replace('_', ' ')} sent to Plex."
            if ok
            else str(payload.get("message") or "Playback command failed.")
        ),
    }


async def _calibre_clause(clause: str) -> dict[str, Any]:
    """Strip spoken verbs and search (or open) books in Calibre."""
    from .dev import unwrap_bridge
    from .fleet_bridge import fleet_call_tool

    lower = clause.lower()
    auto_open = any(v in lower for v in ("open", "read", "show", "launch"))
    query = re.sub(
        r"^(search|find|look\s+for|open|read|show|launch|list)\s+(for\s+|me\s+)?",
        "",
        clause,
        flags=re.IGNORECASE,
    ).strip(" ,.")
    # Strip content-hint words that are not part of the search term
    query = re.sub(
        r"^(the\s+|a\s+|my\s+)?(book|novel|audiobook|series|author|title|about)\s+(of\s+|by\s+)?",
        "",
        query,
        flags=re.IGNORECASE,
    ).strip(" ,.")
    if not query or query.lower() in ("recent", "latest", "new"):
        operation = "recent"
        limit = 5
        query_text = None
    else:
        operation = "search"
        limit = 1 if auto_open else 5
        query_text = query
    result = await fleet_call_tool(
        server="calibre",
        tool="query_books",
        arguments={
            "operation": operation,
            "text": query_text,
            "limit": limit,
            "auto_open": auto_open,
        },
    )
    payload = unwrap_bridge(result)
    if not result.get("success"):
        return {
            "success": False,
            "message": str(
                payload.get("message") or "Calibre is unreachable (calibre-mcp not running?)."
            ),
        }
    raw = payload.get("result") or payload.get("data") or {}
    items = _plex_items(raw)
    titles = [_item_title(i, "") for i in items if _item_title(i, "")]
    if auto_open:
        if not titles:
            return {"success": False, "message": f"No book found for '{query}' in Calibre."}
        return {"success": True, "message": f"Opening {titles[0]} in Calibre."}
    if not titles:
        label = "recent books" if operation == "recent" else f"'{query}'"
        return {"success": True, "message": f"No Calibre results for {label}."}
    return {"success": True, "message": f"Calibre matches: {'; '.join(titles[:3])}."}


async def _media_search(clause: str) -> dict[str, Any]:
    """Search Plex media and list the top matches."""
    from .dev import unwrap_bridge
    from .fleet_bridge import fleet_call_tool

    query = re.sub(
        r"^(search|find|look\s+for|list|what\s+do\s+we\s+have)\s+(for\s+)?",
        "",
        clause,
        flags=re.IGNORECASE,
    ).strip(" ,.")
    result = await fleet_call_tool(
        server="plex",
        tool="plex_search",
        arguments={"operation": "search", "query": query, "limit": 5},
    )
    payload = unwrap_bridge(result)
    if not result.get("success"):
        return {
            "success": False,
            "message": str(
                payload.get("message") or "Plex is unreachable (plex-mcp not running?)."
            ),
        }
    items = _plex_items(payload.get("data"))
    titles = [_item_title(i, "") for i in items if _item_title(i, "")]
    if not titles:
        return {"success": True, "message": f"No Plex results for '{query}'."}
    return {"success": True, "message": f"Plex matches: {'; '.join(titles[:3])}."}


async def _dispatch_clause(clause: str) -> dict[str, Any]:
    from .dev import _opencode_send, unwrap_bridge
    from .fleet_bridge import fleet_call_tool

    lower = clause.lower()
    if "opencode" in lower:
        return await _opencode_send(clause)

    if "timer" in lower or "reminder" in lower:
        if "cancel" in lower or "stop" in lower:
            result = await fleet_call_tool(
                server="speech",
                tool="manage_domestic_utility",
                arguments={"action": "cancel", "type": "timer", "label": ""},
            )
            payload = unwrap_bridge(result)
            if not result.get("success") or not payload.get("success", True):
                return {
                    "success": False,
                    "message": str(payload.get("message") or "Timers could not be cancelled."),
                }
            cancelled = payload.get("cancelled") or []
            return {
                "success": True,
                "message": f"Cancelled {len(cancelled)} timer{'s' if len(cancelled) != 1 else ''}.",
            }
        parsed = parse_duration(clause)
        if not parsed:
            return {
                "success": False,
                "message": (
                    f"Could not parse a timer duration from '{clause}'. "
                    "Say e.g. 'set timer twenty minutes'."
                ),
            }
        seconds, human = parsed
        label = re.sub(
            r"^(set|start|create|new)?\s*(a|the)?\s*timer\s*(for)?\s*", "", lower
        ).strip()
        label = label.replace(human, "").strip(" ,.")[:40] or "timer"
        result = await fleet_call_tool(
            server="speech",
            tool="manage_domestic_utility",
            arguments={"action": "set", "type": "timer", "value": seconds, "label": label},
        )
        payload = unwrap_bridge(result)
        if not result.get("success") or not payload.get("success", True):
            return {
                "success": False,
                "message": str(
                    payload.get("message") or "Timer could not be set (speech-mcp unreachable?)."
                ),
            }
        return {"success": True, "message": f"Timer set for {human}."}

    if lower.startswith("play "):
        return await _plex_play(clause[len("play") :].strip(" ,."))

    if any(
        w in lower
        for w in (
            "book",
            "novel",
            "author",
            "audiobook",
            "read",
            "series",
            "open",
            "show",
            "recent",
            "latest",
        )
    ):
        return await _calibre_clause(clause)

    for verb in ("pause", "stop", "resume", "continue", "next", "skip", "previous"):
        if lower.startswith(verb) or lower == verb:
            return await _plex_control(verb)

    if re.match(r"^(search|find|look for|list|what do we have)\b", lower):
        return await _media_search(clause)

    return {"success": False, "message": f"Unrecognized command: '{clause}'"}


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def voice_assist(
    text: Annotated[
        str,
        Field(description="Spoken command text; may chain intents with 'then' or 'and'."),
    ],
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Execute domestic voice intents — timers, Plex playback, media search.

    [RATIONALE]
    One portmanteau parses spoken chains ("set timer twenty minutes, then
    play desguello") and dispatches each clause to the owning fleet member:
    timers to speech-mcp, playback/search to plex-mcp, book search to
    calibre-mcp.

    ## Return Format
    {"success": bool, "message": str}

    ## Examples
    voice_assist(text="set timer twenty minutes, then play desguello")
    voice_assist(text="play some johnny cash")
    voice_assist(text="find book neuromancer")
    voice_assist(text="pause plex")
    """
    clauses = split_clauses(text)
    if not clauses:
        return {"success": False, "message": "Empty command."}
    messages: list[str] = []
    ok = True
    for clause in clauses:
        r = await _dispatch_clause(clause)
        messages.append(str(r.get("message") or ("Done." if r.get("success") else "Failed.")))
        if not r.get("success"):
            ok = False
    return {"success": ok, "message": " ".join(messages)}
