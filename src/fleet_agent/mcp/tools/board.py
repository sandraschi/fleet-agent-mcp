"""fleet_board + agent inbox tools - the P2 comm bus surface.

[RATIONAL]: One portmanteau for the bulletin board (post/list/reply/search/
subscribe) plus two inbox tools keeps the agent's comm surface compact while
matching the hub's REST API 1:1. The hub is the single source of truth
(SQLite board.db); these tools are thin HTTP wrappers so agents never do raw
REST themselves (P2 protocol rule).

Board is broadcast + archive (browsable history). Inbox is addressed
delivery only - it has no browsable history by design.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

import httpx
from pydantic import Field

from ...config import settings
from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.board")


def _hub_headers() -> dict[str, str]:
    if settings.fleet_hub_token:
        return {"Authorization": f"Bearer {settings.fleet_hub_token}"}
    return {}


async def _hub_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{settings.fleet_hub_url.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.request(method, url, headers=_hub_headers(), **kwargs)
        resp.raise_for_status()
        return resp.json()


@mcp.tool(annotations={"readonly": False}, version="0.1.0")
async def fleet_board(
    operation: Annotated[
        Literal["post", "list", "reply", "search", "subscribe"],
        Field(description="Board operation."),
    ],
    channel: Annotated[
        str, Field(description="Channel: fleet-pulse, dev-worklog, handoffs.")
    ] = "dev-worklog",
    title: Annotated[str, Field(description="Short title (post only).")] = "",
    body: Annotated[str, Field(description="Post body (post/reply).")] = "",
    parent_id: Annotated[int | None, Field(description="Parent post id (reply only).")] = None,
    query: Annotated[str, Field(description="Search text (search only).")] = "",
    limit: Annotated[int, Field(description="Max rows (list/subscribe).", ge=1, le=500)] = 50,
    since_id: Annotated[
        int | None, Field(description="Return posts with id > since_id (subscribe).")
    ] = None,
) -> dict[str, Any]:
    """Bulletin board over the hub.

    post: create a post in a channel.
    list: recent posts (newest first), optional channel filter.
    reply: thread reply to an existing post (parent_id).
    search: full-text-ish search across titles/bodies/authors.
    subscribe: same as list but only posts with id > since_id (poll for new).

    ## Return Format
    {"success": bool, "posts": [...] | "post": {...} | "error": str}

    ## Examples
    fleet_board(operation="post", channel="dev-worklog",
                title="started P2", body="WIP: board module done")
    fleet_board(operation="list", channel="dev-worklog", limit=10)
    fleet_board(operation="subscribe", channel="handoffs", since_id=5)
    """
    try:
        if operation == "post":
            data = await _hub_request(
                "POST",
                "/api/v1/board/posts",
                json={
                    "channel": channel,
                    "author": settings.agent_name,
                    "title": title,
                    "body": body,
                },
            )
            return {"success": True, "post": data.get("post")}
        if operation == "reply":
            if not parent_id:
                return {"success": False, "error": "parent_id is required for reply"}
            data = await _hub_request(
                "POST",
                "/api/v1/board/posts",
                json={
                    "channel": channel,
                    "author": settings.agent_name,
                    "title": title,
                    "body": body,
                    "parent_id": parent_id,
                },
            )
            return {"success": True, "post": data.get("post")}
        if operation == "search":
            data = await _hub_request(
                "GET", "/api/v1/board/search", params={"q": query, "limit": limit}
            )
            return {"success": True, "posts": data.get("posts", [])}
        params: dict[str, Any] = {"limit": limit}
        if channel:
            params["channel"] = channel
        if since_id is not None:
            params["since_id"] = since_id
        data = await _hub_request("GET", "/api/v1/board/posts", params=params)
        return {"success": True, "posts": data.get("posts", [])}
    except Exception as exc:
        logger.warning("fleet_board %s failed: %s", operation, exc)
        return {"success": False, "error": str(exc)}


@mcp.tool(annotations={"readonly": False}, version="0.1.0")
async def agent_send(
    to_entity: Annotated[str, Field(description="Recipient entity (fritz, boomy, alexa, ...).")],
    subject: Annotated[str, Field(description="Short subject.")] = "",
    body: Annotated[str, Field(description="Message body.")] = "",
) -> dict[str, Any]:
    """Send an addressed message to another entity's hub inbox (point-to-point handoff).

    ## Return Format
    {"success": bool, "message": {...}}

    ## Examples
    agent_send(to_entity="boomy", subject="patrol", body="run the patrol route at dusk")
    """
    try:
        data = await _hub_request(
            "POST",
            "/api/v1/inbox/send",
            json={
                "to_entity": to_entity,
                "from_entity": settings.agent_name,
                "subject": subject,
                "body": body,
            },
        )
        return {"success": True, "message": data.get("message")}
    except Exception as exc:
        logger.warning("agent_send failed: %s", exc)
        return {"success": False, "error": str(exc)}


@mcp.tool(annotations={"readonly": True}, version="0.1.0")
async def agent_poll(
    entity: Annotated[str, Field(description="Entity to poll (defaults to this agent).")] = "",
    mark_read: Annotated[
        bool, Field(description="Consume messages on fetch (default true).")
    ] = True,
) -> dict[str, Any]:
    """Poll the hub inbox for unread addressed messages (fritz/boomy/alexa).

    mark_read=true consumes; set false to peek without consuming.

    ## Return Format
    {"success": bool, "messages": [...]}

    ## Examples
    agent_poll()
    agent_poll(entity="boomy", mark_read=False)
    """
    entity = entity or settings.agent_name.lower()
    try:
        data = await _hub_request(
            "GET", "/api/v1/inbox/poll", params={"entity": entity, "mark_read": mark_read}
        )
        return {"success": True, "messages": data.get("messages", [])}
    except Exception as exc:
        logger.warning("agent_poll failed: %s", exc)
        return {"success": False, "error": str(exc)}
