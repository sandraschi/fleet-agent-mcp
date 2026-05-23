"""Identity tools — agent self-definition, north star, and human partner info."""

from typing import Any

from fastmcp import Context

from ...identity.soul import get_identity
from ..registry import mcp


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def identity_whoami(
    ctx: Context = None,
) -> dict[str, Any]:
    """Return the agent's self-introduction — name, human partner, and purpose preview.

    ## Return Format
    {"success": bool, "identity": dict, "message": str}

    ## Examples
    identity_whoami()
    """
    ident = get_identity()
    return {
        "success": True,
        "identity": ident.whoami(),
        "message": (
            f"I am {ident.whoami()['name']}, "
            f"an AI agent partnered with {ident.whoami()['human']}."
        ),
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def identity_soul(
    ctx: Context = None,
) -> dict[str, Any]:
    """Read the agent's full SOUL.md — core identity, personality, and constraints.

    ## Return Format
    {"success": bool, "soul": str, "message": str}

    ## Examples
    identity_soul()
    """
    ident = get_identity()
    soul = ident.soul
    if not soul:
        return {
            "success": False,
            "message": (
                "SOUL.md not found. "
                "Create identity/SOUL.md or ~/.fleet-agent/identity/SOUL.md."
            ),
        }
    return {
        "success": True,
        "soul": soul,
        "char_count": len(soul),
        "message": f"SOUL.md loaded ({len(soul)} chars).",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def identity_north_star(
    ctx: Context = None,
) -> dict[str, Any]:
    """Read the agent's NORTH_STAR.md — purpose, long-term goals, guiding principles.

    The north star is used by pulse_align() to prioritize tasks strategically.

    ## Return Format
    {"success": bool, "north_star": str, "message": str}

    ## Examples
    identity_north_star()
    """
    ident = get_identity()
    ns = ident.north_star
    if not ns:
        return {
            "success": False,
            "message": (
                "NORTH_STAR.md not found. "
                "Create identity/NORTH_STAR.md or ~/.fleet-agent/identity/NORTH_STAR.md."
            ),
        }
    return {
        "success": True,
        "north_star": ns,
        "char_count": len(ns),
        "message": f"NORTH_STAR.md loaded ({len(ns)} chars).",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def identity_user(
    ctx: Context = None,
) -> dict[str, Any]:
    """Read USER.md — information about the agent's human partner.

    ## Return Format
    {"success": bool, "user_info": str, "message": str}

    ## Examples
    identity_user()
    """
    ident = get_identity()
    ui = ident.user_info
    if not ui:
        return {
            "success": False,
            "message": (
                "USER.md not found. "
                "Create identity/USER.md or ~/.fleet-agent/identity/USER.md."
            ),
        }
    return {
        "success": True,
        "user_info": ui,
        "char_count": len(ui),
        "message": f"USER.md loaded ({len(ui)} chars).",
    }
