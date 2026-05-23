"""Evolution log tools — record mistakes, corrections, and lessons.

Inspired by kagura-agent: "When I mess up, it's in the git history.
When I learn something, it goes into my wiki. No curation, no hiding."
"""

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from ...memory.evolution import get_evolution_log
from ..registry import mcp


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def evolution_record(
    correction: Annotated[str, Field(description="What went wrong and how it was fixed.")],
    lesson: Annotated[
        str,
        Field(description="The lesson learned — stated as a rule to follow going forward."),
    ],
    context: Annotated[
        str,
        Field(description="What was being attempted when the mistake happened."),
    ] = "",
    ctx: Context = None,
) -> dict[str, Any]:
    """Record a mistake, correction, and lesson in the evolution log.

    Every correction becomes a permanent lesson. This creates compound improvement
    over time — the agent never makes the same mistake twice.

    ## Return Format
    {"success": bool, "entry": dict, "message": str}

    ## Examples
    evolution_record(
        correction="Used shell=True in subprocess — switched to create_subprocess_exec",
        lesson="NEVER use shell=True for subprocess calls",
        context="Building the state machine engine"
    )
    """
    evo = get_evolution_log()
    entry = evo.record(correction=correction, lesson=lesson, context=context)
    return {
        "success": True,
        "entry": entry,
        "message": "Evolution entry recorded. You're learning.",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def evolution_list(
    limit: Annotated[int, Field(description="Max entries to return.", ge=1, le=500)] = 50,
    ctx: Context = None,
) -> dict[str, Any]:
    """List recent evolution log entries — corrections and lessons.

    ## Return Format
    {"success": bool, "entries": list[dict], "count": int, "message": str}

    ## Examples
    evolution_list()
    evolution_list(limit=10)
    """
    evo = get_evolution_log()
    entries = evo.list_entries(limit=limit)
    stats = evo.stats()
    return {
        "success": True,
        "entries": entries,
        "count": len(entries),
        "stats": {
            "total_corrections": stats["total_corrections"],
            "unique_lessons": stats["unique_lessons"],
        },
        "message": (
            f"{len(entries)} entries "
            f"(total: {stats['total_corrections']}, "
            f"unique lessons: {stats['unique_lessons']})."
        ),
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def evolution_stats(
    ctx: Context = None,
) -> dict[str, Any]:
    """Get evolution log statistics — total corrections, unique lessons, patterns.

    ## Return Format
    {"success": bool, "stats": dict, "duplicate_lessons": list, "message": str}

    ## Examples
    evolution_stats()
    """
    evo = get_evolution_log()
    stats = evo.stats()
    dupes = evo.lint()
    return {
        "success": True,
        "stats": stats,
        "duplicate_lessons": dupes,
        "message": (
            f"{stats['total_corrections']} corrections, "
            f"{stats['unique_lessons']} unique lessons."
        ),
    }
