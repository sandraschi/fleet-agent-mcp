"""Fleet bridge tools — cross-server MCP client for calling other fleet MCP servers.

Enables the fleet agent to delegate work to specialized servers:
  - opencode-cli-mcp → run opencode agents for repo inspection
  - git-github-mcp → query GitHub repos, issues, PRs
  - documentation-mcp → search fleet documentation via RAG
  - advanced-memory-mcp → store/recall persistent memories
  - and any other fleet MCP server

Uses FastMCP 3.2 Client with StreamableHttpTransport.

Server discovery: the static FLEET_SERVERS table is the offline fallback; the
mcp-federation-hub bridge (fleet_hub_url) is the canonical registry and is
refreshed by fleet_refresh_from_hub() (hub entries win on alias conflict).
"""

import logging
from typing import Annotated, Any

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from pydantic import Field

from ...config import settings
from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.fleet_bridge")

# Legacy aliases — bare "vla" means vla-mcp (robotics), NOT vienna-life-assistant.
FLEET_SERVER_ALIASES: dict[str, str] = {
    "vla": "vla-robotics",
}

# ── Fleet MCP Server Registry ────────────────────────────────────────────────
# Each entry maps a server alias to its streamable HTTP MCP endpoint.
# Ports from WEBAPP_PORTS.md — all servers use /mcp path for Streamable HTTP.

FLEET_SERVERS: dict[str, dict[str, Any]] = {
    "opencode": {
        "daemon": False,  # launched on demand with opencode
        "url": "http://127.0.0.1:10951/mcp",
        "description": "opencode-cli-mcp — AI coding agents, sessions, provider config",
        "category": "code",
        "key_tools": ["opencode_run_agent", "opencode_list_sessions", "opencode_get_project"],
    },
    "fleet-agent": {
        "daemon": True,  # runs as a 24/7 HTTP daemon (NSSM/opencode)
        "url": "http://127.0.0.1:10996/mcp/",
        "description": "fleet-agent-mcp (Lumen) — state machine, tasks, memory, identity",
        "category": "orchestration",
        "key_tools": ["heartbeat_status", "pulse_list", "memory_card_search"],
    },
    "git-github": {
        "url": "http://127.0.0.1:10702/mcp",
        "description": "git-github-mcp — GitHub API: repos, issues, PRs, branches, commits",
        "category": "code",
        "key_tools": ["list_repos", "list_issues", "list_prs"],
    },
    "docs": {
        "url": "http://127.0.0.1:10795/mcp",
        "description": "documentation-mcp — federated RAG: semantic search, ask, reindex",
        "category": "knowledge",
        "key_tools": ["search_docs", "ask_docs", "get_document"],
    },
    "memory": {
        "daemon": True,  # runs as a 24/7 HTTP daemon (NSSM/opencode)
        "url": "http://127.0.0.1:10732/mcp",
        "description": "advanced-memory-mcp — persistent agent memory, knowledge graphs, embedding",
        "category": "knowledge",
        "key_tools": ["store_memory", "recall_memory", "search_knowledge"],
    },
    "discord": {
        "url": "http://127.0.0.1:10756/mcp",
        "description": "discord-mcp — Discord bot integration, messages, channels, guilds",
        "category": "communication",
        "key_tools": ["discord_send", "discord_read", "discord_list_channels"],
    },
    "robofang": {
        "url": "http://127.0.0.1:10871/mcp",
        "description": "robofang — AI fleet command center, robotics orchestration, alerting",
        "category": "orchestration",
        "key_tools": ["robofang_status", "robofang_trigger", "robofang_agents"],
    },
    "plex": {
        "url": "http://127.0.0.1:10740/mcp",
        "description": "plex-mcp — Plex media: libraries, streaming, users, playlists, RAG (22 tools)",  # noqa: E501
        "category": "media",
        "key_tools": ["plex_library", "plex_search", "plex_streaming", "plex_rag"],
    },
    "calibre": {
        "url": "http://127.0.0.1:10720/mcp",
        "description": "calibre-mcp — Ebook library: books, authors, fulltext search, LanceDB RAG (30+ tools)",  # noqa: E501
        "category": "media",
        "key_tools": ["query_books", "search_fulltext", "manage_libraries", "calibre_rag"],
    },
    "arxiv": {
        "daemon": True,  # runs as a 24/7 HTTP daemon (NSSM/opencode)
        "url": "http://127.0.0.1:10770/mcp",
        "description": "arxiv-mcp — Papers: search, full text, citations, DOI, lab blogs (22 tools + 10 prompts)",
        "category": "research",
        "key_tools": [
            "search_papers",
            "get_paper_details",
            "find_connected_papers",
            "arxiv_agentic_assist",
        ],
    },
    "aiwatcher": {
        "daemon": True,  # runs as a 24/7 HTTP daemon (NSSM/opencode)
        "url": "http://127.0.0.1:10946/mcp",
        "description": "aiwatcher-mcp — AI news distillation, urgency scoring, top items, search, digest history",
        "category": "intelligence",
        "key_tools": [
            "get_top_items",
            "search_items",
            "generate_digest",
            "check_alerts",
            "get_bundle_health",
            "ingest_fleet_event",
        ],
    },
    "browser": {
        "url": "http://127.0.0.1:10780/mcp",
        "description": "browser-mcp — Browser automation: open URLs, screenshots, web scraping, bookmarks",
        "category": "automation",
        "key_tools": [
            "browser_open",
            "browser_screenshot",
            "browser_navigate",
            "browser_bookmarks",
        ],
    },
    "cursor": {
        "url": "http://127.0.0.1:11000/mcp",
        "description": "cursor-mcp — Cursor platform API: usage/spend guardrails, cloud agent monitor",
        "category": "orchestration",
        "key_tools": ["cursor_usage", "cursor_cloud", "cursor_docs", "cursor_sdk", "cursor_help"],
    },
    "pywinauto": {
        "daemon": True,  # runs as a 24/7 HTTP daemon (NSSM/opencode)
        "url": "http://127.0.0.1:10788/mcp",
        "description": "pywinauto-mcp — Windows UI automation: windows, clicks, keyboard, OCR, Cua-shaped window snapshots",
        "category": "automation",
        "key_tools": [
            "get_window_state",
            "automation_windows",
            "automation_elements",
            "automation_keyboard",
            "automation_mouse",
        ],
    },
    "speech": {
        "url": "http://127.0.0.1:10909/mcp",
        "description": "speech-mcp — TTS/STT, wake word, voice command bus ingress",
        "category": "media",
        "key_tools": ["configure_local_wake_word", "transcribe_audio_file", "speech_say"],
    },
    "alexa": {
        "url": "http://127.0.0.1:10801/mcp",
        "description": "alexa-mcp — Acoustic bridge: TTS to Echo, STT of Alexa reply (interact)",
        "category": "smart_home",
        "key_tools": ["interact", "speak_command", "listen_for_response"],
    },
    "yahboom": {
        "url": "http://127.0.0.1:10892/mcp",
        "description": "yahboom-mcp — Yahboom robot car: motors, patrol, sensors, camera",
        "category": "robotics",
        "key_tools": ["yahboom_agent_mission", "yahboom_patrol", "yahboom_status"],
    },
    "teleoperator": {
        "url": "http://127.0.0.1:10901/mcp",
        "description": "teleoperator-mcp — WebXR teleop gateway: estop, takeover, authority, gaze, LiveKit video",
        "category": "robotics",
        "key_tools": [
            "teleop_voice_command",
            "teleop_status",
            "teleop_estop",
            "teleop_takeover",
            "teleop_set_mode",
        ],
    },
    "dreame": {
        "url": "http://127.0.0.1:10894/mcp",
        "description": "dreame-mcp — Dreame D20 Pro robot vacuum (status, battery, start_clean, stop, pause, go_home, find_robot)",
        "category": "smart_home",
        "key_tools": ["dreame_tool", "dreame_agentic_workflow"],
    },
    "vla-robotics": {
        "url": "http://127.0.0.1:11024/mcp",
        "description": (
            "vla-mcp (video-language-action) — X Square Wall-OSS, WALL-WM, DMuon; "
            "NOT vienna-life-assistant — use alias vienna-life for life admin"
        ),
        "category": "robotics",
        "key_tools": [
            "vla_pipeline",
            "vla_weights",
            "vla_wall",
            "vla_fleet",
            "vla_agentic_workflow",
        ],
    },
    "email": {
        "daemon": True,  # runs as a 24/7 HTTP daemon (NSSM/opencode)
        "url": "http://127.0.0.1:10813/mcp",
        "description": "email-mcp — SMTP/IMAP inbox, send, search, mailing lists, auto-respond",
        "category": "office",
        "key_tools": ["check_inbox", "send_email", "email_status", "search_emails"],
    },
    "notion": {
        "url": "http://127.0.0.1:10811/mcp",
        "description": "notion-mcp — pages, databases, search, workspace automation",
        "category": "office",
        "key_tools": ["create_page", "search_pages", "query_database"],
    },
    "onenote": {
        "url": "http://127.0.0.1:10907/mcp",
        "description": "onenote-mcp — notebooks, sections, pages via Graph",
        "category": "office",
        "key_tools": ["listNotebooks", "listPages", "createPage", "searchPages"],
    },
    "libreoffice": {
        "url": "http://127.0.0.1:10981/mcp",
        "description": "libreoffice-mcp — headless convert + bridge to LO extension MCP",
        "category": "office",
        "key_tools": ["libreoffice", "convert", "bridge_discover"],
    },
    "libreoffice-ext": {
        "url": "http://127.0.0.1:8765/mcp",
        "description": "LibreOffice extension MCP (WriterAgent / mcp-libre / Nelson) — live GUI edit",
        "category": "office",
        "key_tools": ["convert_document", "read_document_text", "create_document"],
    },
    "devices": {
        "daemon": True,  # runs as a 24/7 HTTP daemon (NSSM/opencode)
        "url": "http://127.0.0.1:10716/mcp",
        "description": "devices-mcp — home IoT: cameras, Shelly temps, Nest CO/smoke, Ring alarm",
        "category": "smart_home",
        "key_tools": [
            "security_management",
            "shelly_management",
            "ring_management",
            "home_assistant_management",
        ],
    },
    "glance": {
        "url": "http://127.0.0.1:10776/mcp",
        "description": "glance-mcp — RSS, weather, fleet probes, OPML feeds",
        "category": "intelligence",
        "key_tools": ["glance_ops", "glance_health"],
    },
    "vienna-life": {
        "url": "http://127.0.0.1:10922/mcp",
        "description": "vienna-life-assistant (ViLife) — calendar, todos, expenses; NOT vla-mcp robotics",
        "category": "life",
        "key_tools": ["vienna_life", "fleet_overview"],
    },
    "secrets": {
        "url": "http://127.0.0.1:11026/mcp",
        "description": "secrets-mcp — Bitwarden CLI, audit_fleet, fingerprint resolve",
        "category": "infra",
        "key_tools": ["secrets_ops", "audit_fleet"],
    },
}


# ── Hub-backed discovery (canonical registry) ────────────────────────────────

# Overlay populated by fleet_refresh_from_hub(); static FLEET_SERVERS remains
# the offline fallback.
_hub_servers: dict[str, dict[str, Any]] = {}
_hub_aliases: dict[str, str] = {}


def _all_servers() -> dict[str, dict[str, Any]]:
    """Merged server table: hub overlay wins over the static table."""
    merged = dict(FLEET_SERVERS)
    merged.update(_hub_servers)
    return merged


def _resolve_alias(alias: str) -> str:
    """Resolve an alias to a canonical server id (hub first, static fallback)."""
    if alias in _hub_aliases:
        return _hub_aliases[alias]
    return FLEET_SERVER_ALIASES.get(alias, alias)


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def fleet_refresh_from_hub() -> dict[str, Any]:
    """Refresh the fleet server table from the mcp-federation-hub registry.

    Fetches ``GET {hub}/api/v1/servers`` and merges every registered server
    into the bridge's lookup (hub entries win on alias conflict). The static
    table remains the offline fallback when the hub is unreachable.

    ## Return Format
    {"success": bool, "hub": str, "servers_added": int,
     "servers_total": int, "error": str|null, "message": str}

    ## Examples
    fleet_refresh_from_hub()
    """
    global _hub_servers, _hub_aliases
    hub = settings.fleet_hub_url
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{hub}/api/v1/servers")
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:  # hub down → keep static table
        return {
            "success": False,
            "hub": hub,
            "servers_added": 0,
            "servers_total": len(_all_servers()),
            "error": str(e)[:300],
            "message": f"Hub unreachable ({e}); static fleet table still active.",
        }

    servers = data.get("servers", []) if isinstance(data, dict) else []
    fresh: dict[str, dict[str, Any]] = {}
    aliases: dict[str, str] = {}
    for entry in servers:
        if not isinstance(entry, dict):
            continue
        sid = entry.get("id") or entry.get("name")
        if not sid:
            continue
        alias = str(sid).lower().removesuffix("-mcp")
        port = entry.get("mcp_port") or entry.get("port")
        web = entry.get("web_interface") or ""
        url = None
        if port:
            url = f"http://127.0.0.1:{port}/mcp"
        elif web and str(web).startswith("http"):
            url = str(web).rstrip("/") + "/mcp"
        if not url:
            continue
        fresh[alias] = {
            "url": url,
            "description": f"{sid} — via hub registry",
            "category": str(entry.get("tier") or "hub"),
            "key_tools": [],
            "hub": True,
        }
        aliases[alias] = alias
        aliases[str(sid).lower()] = alias

    _hub_servers = fresh
    _hub_aliases = aliases
    total = len(_all_servers())
    return {
        "success": True,
        "hub": hub,
        "servers_added": len(fresh),
        "servers_total": total,
        "error": None,
        "message": f"Refreshed from hub: {len(fresh)} servers ({total} total after merge).",
    }


async def _get_client(server_url: str) -> Client:
    """Create a connected MCP client for a fleet server."""
    transport = StreamableHttpTransport(server_url)
    return Client(transport)


# ── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def fleet_discover() -> dict[str, Any]:
    """Discover available fleet MCP servers and their tool surfaces.

    Probes each registered fleet server, lists its tools, and returns
    a catalog of what tools are available across the fleet.

    ## Return Format
    {"success": bool, "servers": [...], "message": str}

    ## Examples
    fleet_discover()
    """
    servers_result = []

    for alias, info in _all_servers().items():
        entry = {
            "alias": alias,
            "url": info["url"],
            "description": info["description"],
            "category": info["category"],
            "online": False,
            "daemon": bool(info.get("daemon", False)),
            "tool_count": 0,
            "tools": [],
        }

        try:
            async with await _get_client(info["url"]) as client:
                tools = await client.list_tools()
                entry["online"] = True
                entry["tool_count"] = len(tools)
                entry["tools"] = [
                    {"name": t.name, "description": t.description or ""} for t in tools
                ]
        except Exception as e:
            entry["error"] = str(e)[:200]
            logger.warning("Fleet server %s unreachable: %s", alias, e)

        servers_result.append(entry)

    online = sum(1 for s in servers_result if s["online"])
    return {
        "success": True,
        "message": f"Fleet discovery complete: {online}/{len(FLEET_SERVERS)} servers online",
        "data": {"servers": servers_result},
    }


@mcp.tool(version="0.1.0")
async def fleet_call_tool(
    server: Annotated[
        str,
        Field(
            description="Server alias or URL. Aliases: opencode, git-github, docs, email, libreoffice, libreoffice-ext, notion, onenote, ..."
        ),
    ],  # noqa: E501
    tool: Annotated[str, Field(description="Tool name to call on the target server")],
    arguments: Annotated[
        dict[str, Any] | None, Field(description="Tool arguments as key-value dict")
    ] = None,  # noqa: E501
) -> dict[str, Any]:
    """Call a tool on any fleet MCP server via HTTP bridge.

    Use fleet_discover() first to see available servers and their tools.

    ## Return Format
    {"success": bool, "data": ..., "server": str, "tool": str, "message": str}

    ## Examples
    fleet_call_tool(server="opencode", tool="opencode_get_project")
    fleet_call_tool(server="docs", tool="search_docs", arguments={"query": "FastMCP tools"})
    """
    # Resolve server alias to URL
    server_url = server
    if not server.startswith("http"):
        canonical = _resolve_alias(server)
        info = _all_servers().get(canonical)
        if not info:
            known = sorted(
                set(_all_servers().keys())
                | set(FLEET_SERVER_ALIASES.keys())
                | set(_hub_aliases.keys())
            )
            return {
                "success": False,
                "message": f"Unknown server alias '{server}'. Known: {', '.join(known)}",
                "data": {},
            }
        server_url = info["url"]
        server = canonical

    args = arguments or {}

    try:
        async with await _get_client(server_url) as client:
            result = await client.call_tool(tool, args)

            # Extract content
            content_parts = []
            for block in result.content:
                block_text = getattr(block, "text", None)
                if block_text:
                    content_parts.append(block_text)
                    continue
                block_data = getattr(block, "data", None)
                if block_data is not None:
                    content_parts.append(str(block_data))

            return {
                "success": not result.is_error,
                "message": f"Called {tool} on {server}",
                "data": {
                    "server": server,
                    "tool": tool,
                    "content": content_parts,
                    "is_error": result.is_error,
                },
            }
    except Exception as e:
        logger.error("fleet_call_tool failed for %s/%s: %s", server, tool, e)
        return {
            "success": False,
            "message": f"Failed to call {tool} on {server}: {e}",
            "data": {},
        }


@mcp.tool(version="0.1.0")
async def fleet_inspect_repo(
    repo_path: Annotated[
        str,
        Field(
            description="Absolute path to the repo to inspect. Use fleet_discover() to see available repos on disk."
        ),
    ],  # noqa: E501
    aspect: Annotated[
        str | None,
        Field(
            description="What to check: 'status' (git + lint), 'tests', 'deps', 'structure', or None for general inspection"
        ),
    ] = None,  # noqa: E501
    wait: Annotated[
        bool,
        Field(description="Wait for completion (true) or return immediately with job_id (false)"),
    ] = True,  # noqa: E501
) -> dict[str, Any]:
    """Inspect a fleet repo using opencode AI agent.

    Delegates to opencode-cli-mcp's opencode_run_agent tool which spawns
    an opencode AI agent to analyze the repo. Use this for:
    - Checking git status, lint errors, test failures
    - Reviewing code structure and health
    - Finding issues that need attention

    ## Return Format
    {"success": bool, "data": {"job_id": str, "status": str, "output": str}, "message": str}

    ## Examples
    fleet_inspect_repo(repo_path="D:/Dev/repos/discord-mcp")
    fleet_inspect_repo(repo_path="D:/Dev/repos/git-github-mcp", aspect="tests")
    """
    # Build the inspection prompt
    prompts = {
        "status": "Check the git status, look for lint errors. Report issues concisely.",
        "tests": "Run the test suite and report results. Identify failures if any.",
        "deps": "Check dependency freshness — outdated packages or security issues?",
        "structure": "Analyze repo structure — missing files, broken imports, issues?",
        None: "Check repo health: git status, lint, tests, any issues. Be concise.",
    }
    prompt = prompts.get(aspect, prompts[None])

    try:
        result = await fleet_call_tool(
            server="opencode",
            tool="opencode_run_agent",
            arguments={
                "prompt": prompt,
                "project": repo_path,
                "wait": wait,
                "timeout": 300,
            },
        )
        return result
    except Exception as e:
        # Fallback: try direct HTTP call if MCP bridge fails
        logger.error("fleet_inspect_repo MCP call failed, trying direct: %s", e)
        return {
            "success": False,
            "message": f"Could not reach opencode-cli-mcp to inspect {repo_path}: {e}",
            "data": {"hint": "Ensure opencode-cli-mcp is running (ports 10950/10951)"},
        }


# ── Fleet List Tools ─────────────────────────────────────


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def fleet_list_tools(
    server: Annotated[str, Field(description="Server alias from fleet_discover().")],
) -> dict[str, Any]:
    """List MCP tools available on a fleet server.

    Uses Streamable HTTP to call tools/list on the remote server.

    ## Return Format
    {"success": bool, "tools": list[dict], "count": int, "message": str}

    ## Examples
    fleet_list_tools(server="git-github")
    fleet_list_tools(server="docs")
    """
    canonical = _resolve_alias(server)
    info = _all_servers().get(canonical)

    if canonical in ("fleet-agent", "self"):
        from ..registry import mcp as _mcp

        try:
            tools = await _mcp.local_provider.list_tools()
            tool_list = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.parameters,
                }
                for t in tools
            ]
            return {
                "success": True,
                "tools": tool_list,
                "count": len(tool_list),
                "message": f"{len(tool_list)} tools on {canonical}",
            }
        except Exception as e:
            return {"success": False, "message": str(e), "tools": [], "count": 0}

    if info is None:
        known = sorted(
            set(_all_servers().keys()) | set(FLEET_SERVER_ALIASES.keys()) | set(_hub_aliases.keys())
        )
        return {
            "success": False,
            "message": f"Unknown server alias '{server}'. Known: {', '.join(known)}",
            "tools": [],
            "count": 0,
        }
    server_url = info["url"]

    try:
        async with await _get_client(server_url) as client:
            raw_tools = await client.list_tools()
            tool_list = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": getattr(t, "parameters", None),
                }
                for t in raw_tools
            ]
            return {
                "success": True,
                "tools": tool_list,
                "count": len(tool_list),
                "message": f"{len(tool_list)} tools on {canonical}",
            }
    except Exception as e:
        logger.error("fleet_list_tools failed for %s: %s", server, e)
        return {
            "success": False,
            "message": f"Failed to list tools on {server}: {e}",
            "tools": [],
            "count": 0,
        }
