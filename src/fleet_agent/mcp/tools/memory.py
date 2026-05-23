"""Knowledge accumulation tools — compile-time knowledge cards.

Inspired by kagura-agent/wiki: 270+ concept cards, 360+ project notes,
with query-writeback (answers feed back into the wiki), ingest (create +
update related pages), and lint (stale, orphan, contradiction detection).
"""

from datetime import UTC
from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from ...engine.sqlite_store import get_store
from ...memory.wiki import get_wiki
from ..registry import mcp


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def memory_card_create(
    title: Annotated[str, Field(description="Card title.")],
    content: Annotated[str, Field(description="Card content (Markdown).")],
    tags: Annotated[
        list[str] | None, Field(description="Tags for categorization and search.")
    ] = None,
    category: Annotated[
        str,
        Field(description="Category: general, pattern, project, mistake, reference."),
    ] = "general",
    ctx: Context = None,
) -> dict[str, Any]:
    """Create a knowledge card in the wiki.

    Each card captures a concept, pattern, lesson, or reference.
    Cards should be cross-linked for compound knowledge growth.

    ## Return Format
    {"success": bool, "card": dict, "message": str}

    ## Examples
    memory_card_create(
        "SQLite WAL mode",
        "WAL provides concurrent reads...",
        tags=["sqlite", "performance"],
    )
    """
    wiki = get_wiki()
    card = wiki.create_card(title=title, content=content, tags=tags, category=category)
    return {
        "success": True,
        "card": card,
        "message": f"Card '{title}' created (id: {card['id']}).",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def memory_card_search(
    query: Annotated[str, Field(description="Search query (matches title, content, and tags).")],
    ctx: Context = None,
) -> dict[str, Any]:
    """Search knowledge cards by full-text query.

    ## Return Format
    {"success": bool, "cards": list[dict], "count": int, "message": str}

    ## Examples
    memory_card_search("state machine")
    """
    wiki = get_wiki()
    cards = wiki.search(query)
    return {
        "success": True,
        "cards": cards,
        "count": len(cards),
        "message": f"Found {len(cards)} cards matching '{query}'.",
    }


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def memory_card_update(
    card_id: Annotated[str, Field(description="Card ID to update.")],
    content: Annotated[str, Field(description="New content (replaces existing).")],
    tags: Annotated[
        list[str] | None,
        Field(description="New tags (replaces existing if provided)."),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Update a knowledge card's content and/or tags.

    This implements query-writeback: when you search and find outdated info,
    update it so the knowledge compounds.

    ## Return Format
    {"success": bool, "card": dict, "message": str}

    ## Examples
    memory_card_update("a1b2c3d4", "Updated content...", tags=["updated", "sqlite"])
    """
    wiki = get_wiki()
    card = wiki.update_card(card_id=card_id, content=content, tags=tags)
    if card is None:
        return {"success": False, "message": f"Card '{card_id}' not found."}
    return {
        "success": True,
        "card": card,
        "message": f"Card '{card['title']}' updated.",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def memory_cards_list(
    ctx: Context = None,
) -> dict[str, Any]:
    """List all knowledge cards.

    ## Return Format
    {"success": bool, "cards": list[dict], "count": int, "message": str}

    ## Examples
    memory_cards_list()
    """
    wiki = get_wiki()
    cards = wiki.list_all()
    return {
        "success": True,
        "cards": cards,
        "count": len(cards),
        "message": f"{len(cards)} cards in the wiki.",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def memory_lint(
    ctx: Context = None,
) -> dict[str, Any]:
    """Lint the knowledge base for issues: broken references, stale cards, untagged cards.

    Periodic linting prevents knowledge rot — stale facts, orphaned cards,
    and missing cross-references.

    ## Return Format
    {"success": bool, "issues": list[dict], "count": int, "message": str}

    ## Examples
    memory_lint()
    """
    wiki = get_wiki()
    issues = wiki.lint()
    return {
        "success": True,
        "issues": issues,
        "count": len(issues),
        "message": (
            f"{len(issues)} issues found in knowledge base."
            if issues else "Knowledge base is healthy."
        ),
    }


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def memory_project_note(
    project: Annotated[
        str,
        Field(description="Project name (e.g. 'fleet-agent-mcp', 'flowforge')."),
    ],
    content: Annotated[str, Field(description="Note content — what you learned or observed.")],
    tags: Annotated[list[str] | None, Field(description="Tags for cross-referencing.")] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Log a project observation or learning.

    Project notes capture what you learn from working on specific repos:
    patterns, gotchas, architecture decisions, contribution conventions.

    ## Return Format
    {"success": bool, "note": dict, "message": str}

    ## Examples
    memory_project_note(
        "flowforge",
        "SQLite state survives session restarts",
        tags=["architecture", "persistence"],
    )
    """
    import uuid
    from datetime import datetime

    store = get_store()
    now = datetime.now(UTC).isoformat()
    note_id = str(uuid.uuid4())[:8]

    existing = store.project_get(project)
    if existing:
        existing["content"] = existing["content"] + f"\n\n---\n### {now}\n\n{content}"
        existing["updated_at"] = now
        if tags:
            existing["tags"] = list(set(existing.get("tags", []) + tags))
        store.project_upsert(existing)
        note = existing
    else:
        note = {
            "id": note_id,
            "project_name": project,
            "content": f"# {project}\n\n{content}",
            "tags": tags or [],
            "created_at": now,
            "updated_at": now,
        }
        store.project_upsert(note)

    return {
        "success": True,
        "note": note,
        "message": f"Note logged for project '{project}'.",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def memory_project_notes(
    project: Annotated[
        str | None,
        Field(description="Filter by project name. If omitted, lists all."),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """List project notes, optionally filtered by project.

    ## Return Format
    {"success": bool, "notes": list[dict], "count": int, "message": str}

    ## Examples
    memory_project_notes()
    memory_project_notes(project="flowforge")
    """
    store = get_store()
    if project:
        note = store.project_get(project)
        notes = [note] if note else []
    else:
        notes = store.project_list()

    return {
        "success": True,
        "notes": notes,
        "count": len(notes),
        "message": f"{len(notes)} project note(s).",
    }
