"""MCP tools for querying the in-memory log store with filters."""

from typing import Any

from fastmcp import FastMCP

from ..registry import mcp

_READ_ONLY = {"readOnly": True}

ERROR_KEYWORDS = ["critical", "error", "exception", "offline", "failed", "unreachable", "crash"]


@mcp.tool(annotations=_READ_ONLY, version="0.1.0")
async def query_logs(
    source: str | None = None,
    level: str | None = None,
    search: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Query the in-memory log store. Filters by source, level, or keyword.

    ## Parameters
    - source: Filter by log source (e.g. "heartbeat", "system", "coworker")
    - level: Filter by level (e.g. "error", "warn", "info")
    - search: Case-insensitive keyword search in message text
    - limit: Max entries to return (default 50, max 500)

    ## Return Format
    {"success": bool, "logs": list, "count": int, "filtered_by": dict}

    ## Examples
    await query_logs(level="error", limit=10)
    await query_logs(source="heartbeat", limit=5)
    await query_logs(search="offline")
    """
    from ..log_store import get_log_store

    store = get_log_store()
    all_logs = store.recent(5000)

    filtered = all_logs
    if source:
        filtered = [e for e in filtered if e.get("source") == source]
    if level:
        filtered = [e for e in filtered if e.get("level") == level]
    if search:
        search_lower = search.lower()
        filtered = [e for e in filtered if search_lower in e.get("message", "").lower()]

    truncated = filtered[-limit:] if len(filtered) > limit else filtered

    return {
        "success": True,
        "logs": truncated,
        "count": len(truncated),
        "total_matching": len(filtered),
        "filtered_by": {"source": source, "level": level, "search": search, "limit": limit},
    }


@mcp.tool(annotations=_READ_ONLY, version="0.1.0")
async def check_log_errors(
    max_errors: int = 20,
) -> dict[str, Any]:
    """Scan recent logs for error/critical entries. Returns a summary.

    Useful for Fritz heartbeat — checks for problems across NSSM services.

    ## Return Format
    {"success": bool, "error_count": int, "errors": list, "sources_with_errors": list}

    ## Examples
    await check_log_errors()
    """
    from ..log_store import get_log_store

    store = get_log_store()
    all_logs = store.recent(5000)

    errors = [
        e for e in all_logs
        if e.get("level") in ("error", "critical")
        or any(kw in e.get("message", "").lower() for kw in ERROR_KEYWORDS)
    ]

    sources = list(set(e.get("source", "?") for e in errors))
    truncated = errors[-max_errors:] if len(errors) > max_errors else errors

    return {
        "success": True,
        "error_count": len(errors),
        "errors": truncated,
        "sources_with_errors": sources,
    }
