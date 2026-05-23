"""Fleet bridge tools — cross-server MCP client for calling other fleet MCP servers.

Enables the fleet agent to delegate work to specialized servers:
  - opencode-cli-mcp → run opencode agents for repo inspection
  - git-github-mcp → query GitHub repos, issues, PRs
  - documentation-mcp → search fleet documentation via RAG
  - advanced-memory-mcp → store/recall persistent memories
  - and any other fleet MCP server

Uses FastMCP 3.2 Client with StreamableHttpTransport.
"""

import logging
from typing import Annotated, Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from pydantic import Field

from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.fleet_bridge")

# ── Fleet MCP Server Registry ────────────────────────────────────────────────
# Each entry maps a server alias to its streamable HTTP MCP endpoint.
# Ports from WEBAPP_PORTS.md — all servers use /mcp path for Streamable HTTP.

FLEET_SERVERS: dict[str, dict[str, Any]] = {
    "opencode": {
        "url": "http://127.0.0.1:10951/mcp",
        "description": "opencode-cli-mcp — AI coding agents, sessions, provider config",
        "category": "code",
        "key_tools": ["opencode_run_agent", "opencode_list_sessions", "opencode_get_project"],
    },
    "fleet-agent": {
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
        "url": "http://127.0.0.1:10770/mcp",
        "description": "arxiv-mcp — Papers: search, full text, citations, DOI, lab blogs (22 tools + 10 prompts)",  # noqa: E501
        "category": "research",
        "key_tools": ["search_papers", "get_paper_details", "find_connected_papers", "arxiv_agentic_assist"],  # noqa: E501
    },
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

    for alias, info in FLEET_SERVERS.items():
        entry = {
            "alias": alias,
            "url": info["url"],
            "description": info["description"],
            "category": info["category"],
            "online": False,
            "tool_count": 0,
            "tools": [],
        }

        try:
            async with await _get_client(info["url"]) as client:
                tools = await client.list_tools()
                entry["online"] = True
                entry["tool_count"] = len(tools)
                entry["tools"] = [
                    {"name": t.name, "description": t.description or ""}
                    for t in tools
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
    server: Annotated[str, Field(description="Server alias or URL. Aliases: opencode, git-github, docs, memory, discord, fleet-agent, plex, calibre, arxiv")],  # noqa: E501
    tool: Annotated[str, Field(description="Tool name to call on the target server")],
    arguments: Annotated[dict[str, Any] | None, Field(description="Tool arguments as key-value dict")] = None,  # noqa: E501
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
        info = FLEET_SERVERS.get(server)
        if not info:
            aliases = ", ".join(FLEET_SERVERS.keys())
            return {
                "success": False,
                "message": f"Unknown server alias '{server}'. Known: {aliases}",
                "data": {},
            }
        server_url = info["url"]

    args = arguments or {}

    try:
        async with await _get_client(server_url) as client:
            result = await client.call_tool(tool, args)

            # Extract content
            content_parts = []
            for block in result.content:
                if hasattr(block, "text"):
                    content_parts.append(block.text)
                elif hasattr(block, "data"):
                    content_parts.append(str(block.data))

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
    repo_path: Annotated[str, Field(description="Absolute path to the repo to inspect. Use fleet_discover() to see available repos on disk.")],  # noqa: E501
    aspect: Annotated[str | None, Field(description="What to check: 'status' (git + lint), 'tests', 'deps', 'structure', or None for general inspection")] = None,  # noqa: E501
    wait: Annotated[bool, Field(description="Wait for completion (true) or return immediately with job_id (false)")] = True,  # noqa: E501
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
