"""Voice command bus routing (no live MCP)."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from fleet_agent.mcp.tools.assist import parse_duration, split_clauses
from fleet_agent.voice_registry import resolve_entity
from fleet_agent.voice_router import _bridge_summary, route_voice_intent

REGISTRY = {
    "router": {"default_entity": "fritz"},
    "entities": {
        "boomy": {"server": "yahboom", "aliases": ["boomy", "yahboom"]},
        "alexa": {"server": "alexa", "aliases": ["alexa"]},
        "fritz": {"server": "fleet-agent", "aliases": ["fritz", "lumen"]},
        "opencode": {"server": "fleet-agent", "aliases": ["opencode", "open code"]},
        "dreame": {"server": "dreame", "aliases": ["dreame", "vacuum", "robohoove"]},
        "calibre": {"server": "fleet-agent", "aliases": ["calibre", "caliber"]},
        "plexy": {"server": "fleet-agent", "aliases": ["plexy", "plex"]},
    },
    "handlers": {
        "boomy": [
            {
                "keywords": ["patrol", "report"],
                "tool": "yahboom_agent_mission",
                "args": {"goal": "{remainder}", "speak": True},
            },
        ],
        "alexa": [
            {
                "default": {
                    "tool": "interact",
                    "args": {"command": "{remainder}", "wait_for_response": True},
                },
            },
        ],
        "fritz": [
            {
                "keywords": ["start webapp", "launch webapp"],
                "tool": "dev_ops",
                "args": {"operation": "start_webapp", "repo": "{remainder}"},
            },
            {
                "keywords": ["gpu status", "gpu stats"],
                "tool": "dev_ops",
                "args": {"operation": "gpu_status"},
            },
            {
                "keywords": ["kick invokeai", "start invokeai"],
                "tool": "dev_ops",
                "args": {"operation": "invokeai_kick"},
            },
            {
                "keywords": ["opencode"],
                "tool": "dev_ops",
                "args": {"operation": "opencode_send", "prompt": "{remainder}"},
            },
            {
                "keywords": ["set timer", "set a timer", "reminder"],
                "tool": "voice_assist",
                "args": {"text": "{remainder}"},
            },
            {
                "keywords": ["play", "music", "search", "find"],
                "tool": "voice_assist",
                "args": {"text": "{remainder}"},
            },
            {
                "default": {
                    "tool": "fritz_voice_agent",
                    "args": {"prompt": "{remainder}", "speak": True},
                },
            },
        ],
        "opencode": [
            {
                "default": {
                    "tool": "dev_ops",
                    "args": {"operation": "opencode_send", "prompt": "{remainder}"},
                },
            },
        ],
        "dreame": [
            {
                "keywords": ["clean", "vacuum", "sweep"],
                "tool": "dreame_tool",
                "args": {"operation": "start_clean"},
            },
            {"keywords": ["stop", "halt"], "tool": "dreame_tool", "args": {"operation": "stop"}},
            {
                "keywords": ["home", "dock"],
                "tool": "dreame_tool",
                "args": {"operation": "go_home"},
            },
            {
                "keywords": ["find", "locate"],
                "tool": "dreame_tool",
                "args": {"operation": "find_robot"},
            },
            {
                "default": {
                    "tool": "dreame_tool",
                    "args": {"operation": "status"},
                },
            },
        ],
        "calibre": [
            {
                "keywords": ["find", "search", "open", "read"],
                "tool": "voice_assist",
                "args": {"text": "{remainder}"},
            },
            {
                "default": {
                    "tool": "voice_assist",
                    "args": {"text": "{remainder}"},
                },
            },
        ],
        "plexy": [
            {
                "keywords": ["play", "watch", "pause", "stop", "next"],
                "tool": "voice_assist",
                "args": {"text": "{remainder}"},
            },
            {
                "default": {
                    "tool": "voice_assist",
                    "args": {"text": "{remainder}"},
                },
            },
        ],
    },
}


def _local_result(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))])


def test_resolve_entity_boomy() -> None:
    entity, remainder = resolve_entity("boomy go on patrol and report findings", REGISTRY)
    assert entity == "boomy"
    assert "patrol" in remainder


@pytest.mark.asyncio
async def test_route_boomy_patrol() -> None:
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        with patch(
            "fleet_agent.mcp.tools.fleet_bridge.fleet_call_tool",
            new_callable=AsyncMock,
            return_value={"success": True, "message": "ok", "data": {}},
        ) as mock_call:
            out = await route_voice_intent(
                wake="wakeywakey",
                transcript="boomy go on patrol and report what you found",
            )
    assert out["success"] is True
    assert out["entity"] == "boomy"
    assert out["tool"] == "yahboom_agent_mission"
    mock_call.assert_awaited_once()
    assert mock_call.await_args.kwargs["server"] == "yahboom"


@pytest.mark.asyncio
async def test_route_fritz_gpu_status() -> None:
    """Dev commands run in-process via mcp.call_tool, not the HTTP bridge."""
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        local = AsyncMock(
            return_value=_local_result({"success": True, "message": "RTX 4090: 12% load"})
        )
        with patch("fleet_agent.mcp.registry.mcp.call_tool", local):
            out = await route_voice_intent(wake="wakeywakey", transcript="fritz gpu status")
    assert out["success"] is True
    assert out["entity"] == "fritz"
    assert out["tool"] == "dev_ops"
    assert out["server"] == "fleet-agent"
    local.assert_awaited_once_with("dev_ops", {"operation": "gpu_status"})


@pytest.mark.asyncio
async def test_route_fritz_start_webapp() -> None:
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        local = AsyncMock(
            return_value=_local_result({"success": True, "message": "arxiv starting"})
        )
        with patch("fleet_agent.mcp.registry.mcp.call_tool", local):
            out = await route_voice_intent(wake="wakeywakey", transcript="fritz start webapp arxiv")
    assert out["tool"] == "dev_ops"
    local.assert_awaited_once_with(
        "dev_ops", {"operation": "start_webapp", "repo": "start webapp arxiv"}
    )


@pytest.mark.asyncio
async def test_route_fritz_kick_invokeai() -> None:
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        local = AsyncMock(
            return_value=_local_result({"success": True, "message": "Engine starting"})
        )
        with patch("fleet_agent.mcp.registry.mcp.call_tool", local):
            out = await route_voice_intent(wake="wakeywakey", transcript="fritz kick invokeai")
    assert out["tool"] == "dev_ops"
    local.assert_awaited_once_with("dev_ops", {"operation": "invokeai_kick"})


@pytest.mark.asyncio
async def test_route_bare_command_default_entity() -> None:
    """Bare commands (no entity word) route to the default entity (fritz)."""
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        local = AsyncMock(return_value=_local_result({"success": True, "message": "ok"}))
        with patch("fleet_agent.mcp.registry.mcp.call_tool", local):
            out = await route_voice_intent(wake="wakeywakey", transcript="gpu status")
    assert out["entity"] == "fritz"
    assert out["tool"] == "dev_ops"
    local.assert_awaited_once_with("dev_ops", {"operation": "gpu_status"})


@pytest.mark.asyncio
async def test_route_opencode_send() -> None:
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        local = AsyncMock(return_value=_local_result({"success": True, "message": "sent"}))
        with patch("fleet_agent.mcp.registry.mcp.call_tool", local):
            out = await route_voice_intent(
                wake="wakeywakey", transcript="opencode assfix devices, run"
            )
    assert out["tool"] == "dev_ops"
    assert out["entity"] == "opencode"
    local.assert_awaited_once_with(
        "dev_ops", {"operation": "opencode_send", "prompt": "assfix devices, run"}
    )


@pytest.mark.asyncio
async def test_route_timer_music_chain() -> None:
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        local = AsyncMock(return_value=_local_result({"success": True, "message": "done"}))
        with patch("fleet_agent.mcp.registry.mcp.call_tool", local):
            out = await route_voice_intent(
                wake="wakeywakey",
                transcript="set timer twenty minutes, then play desguello",
            )
    assert out["tool"] == "voice_assist"
    local.assert_awaited_once_with(
        "voice_assist", {"text": "set timer twenty minutes, then play desguello"}
    )


def test_split_clauses_then_and() -> None:
    assert split_clauses("set timer twenty minutes, then play desguello") == [
        "set timer twenty minutes",
        "play desguello",
    ]
    assert split_clauses("set timer 5 minutes and play mozart") == [
        "set timer 5 minutes",
        "play mozart",
    ]
    assert split_clauses("play desguello") == ["play desguello"]


def test_parse_duration_words_and_digits() -> None:
    assert parse_duration("set timer twenty minutes") == (1200, "20 minutes")
    assert parse_duration("timer for ninety seconds") == (90, "90 seconds")
    assert parse_duration("set timer 5 mins") == (300, "5 mins")
    assert parse_duration("set timer two hours") == (7200, "2 hours")
    assert parse_duration("play desguello") is None


@pytest.mark.asyncio
async def test_route_dreame_clean() -> None:
    """Robohoove commands bridge to dreame-mcp."""
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        bridge = AsyncMock(
            return_value={"success": True, "message": "called", "data": {"content": []}}
        )
        with patch("fleet_agent.mcp.tools.fleet_bridge.fleet_call_tool", bridge):
            out = await route_voice_intent(wake="wakeywakey", transcript="dreame clean the kitchen")
    assert out["entity"] == "dreame"
    assert out["tool"] == "dreame_tool"
    bridge.assert_awaited_once()
    assert bridge.await_args.kwargs["server"] == "dreame"
    assert bridge.await_args.kwargs["arguments"] == {"operation": "start_clean"}


@pytest.mark.asyncio
async def test_route_calibre_search() -> None:
    """Calibre routes through voice_assist so spoken verbs get stripped."""
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        local = AsyncMock(
            return_value=_local_result(
                {"success": True, "message": "Calibre matches: Neuromancer."}
            )
        )
        with patch("fleet_agent.mcp.registry.mcp.call_tool", local):
            out = await route_voice_intent(wake="wakeywakey", transcript="calibre find neuromancer")
    assert out["entity"] == "calibre"
    assert out["tool"] == "voice_assist"
    local.assert_awaited_once_with("voice_assist", {"text": "find neuromancer"})


@pytest.mark.asyncio
async def test_route_plexy_play() -> None:
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        local = AsyncMock(
            return_value=_local_result({"success": True, "message": "Playing Inception on Plex."})
        )
        with patch("fleet_agent.mcp.registry.mcp.call_tool", local):
            out = await route_voice_intent(wake="wakeywakey", transcript="plexy play inception")
    assert out["entity"] == "plexy"
    assert out["tool"] == "voice_assist"
    local.assert_awaited_once_with("voice_assist", {"text": "play inception"})


@pytest.mark.asyncio
async def test_route_opencode_entity() -> None:
    """'opencode' is its own receiver now, not just a fritz keyword."""
    with patch("fleet_agent.voice_router.load_registry", return_value=REGISTRY):
        local = AsyncMock(return_value=_local_result({"success": True, "message": "sent"}))
        with patch("fleet_agent.mcp.registry.mcp.call_tool", local):
            out = await route_voice_intent(wake="wakeywakey", transcript="opencode assfix devices")
    assert out["entity"] == "opencode"
    assert out["tool"] == "dev_ops"
    local.assert_awaited_once_with(
        "dev_ops", {"operation": "opencode_send", "prompt": "assfix devices"}
    )


def test_bridge_summary_markdown() -> None:
    result = {
        "success": True,
        "message": "Called dreame_tool on dreame",
        "data": {"content": ["### Dreame Robot Status\n**Battery**: 87%\nMode: docked"]},
    }
    summary = _bridge_summary(result)
    assert "Dreame Robot Status" in summary
    assert "Battery: 87%" in summary
    assert "###" not in summary
    assert "**" not in summary


def test_bridge_summary_json_message() -> None:
    result = {
        "success": True,
        "message": "Called query_books on calibre",
        "data": {"content": ['{"success": true, "message": "3 books found"}']},
    }
    assert _bridge_summary(result) == "3 books found"


@pytest.mark.asyncio
async def test_voice_assist_play_uses_vlc() -> None:
    """play clauses search Plex via REST and launch VLC with the direct stream."""
    from fleet_agent.mcp.tools import assist
    from fleet_agent.mcp.tools.assist import voice_assist

    with patch.object(assist, "_find_vlc", return_value="C:/vlc.exe"):
        with patch.object(assist, "_launch_vlc") as mock_launch:
            with patch.object(assist, "_plex_rest_search") as mock_search:
                mock_search.return_value = [{"ratingKey": "202", "title": "Charade", "year": 1963}]
                with patch.object(assist, "_plex_direct_url") as mock_url:
                    mock_url.return_value = (
                        "http://localhost:32400/library/parts/459/1354559650/file.mp4"
                        "?X-Plex-Token=tok"
                    )
                    out = await voice_assist(text="play charade")
    assert out["success"] is True
    assert "Charade" in out["message"]
    assert "VLC" in out["message"]
    mock_launch.assert_called_once()
    url = mock_launch.call_args.args[0]
    assert "/library/parts/" in url and "file.mp4" in url
    assert "X-Plex-Token=tok" in url


@pytest.mark.asyncio
async def test_voice_assist_play_no_stream_url() -> None:
    """Missing Plex credentials produce a clear error, not a silent failure."""
    from fleet_agent.mcp.tools import assist
    from fleet_agent.mcp.tools.assist import voice_assist

    with patch.object(assist, "_find_vlc", return_value="C:/vlc.exe"):
        with patch.object(assist, "_plex_rest_search") as mock_search:
            mock_search.return_value = [{"ratingKey": "202", "title": "Charade"}]
            with patch.object(assist, "_plex_direct_url", return_value=None):
                out = await voice_assist(text="play charade")
    assert out["success"] is False
    assert "Charade" in out["message"]


@pytest.mark.asyncio
async def test_voice_assist_calibre_strips_verbs() -> None:
    """Book clauses strip spoken verbs before hitting calibre search."""
    from fleet_agent.mcp.tools.assist import voice_assist

    payload = {
        "success": True,
        "message": "books",
        "data": {"content": ['{"success": true, "result": [{"title": "Neuromancer"}]}']},
    }
    bridge = AsyncMock(return_value=payload)
    with patch("fleet_agent.mcp.tools.fleet_bridge.fleet_call_tool", bridge):
        out = await voice_assist(text="find book neuromancer")
    assert out["success"] is True
    assert "Neuromancer" in out["message"]
    bridge.assert_awaited_once()
    assert bridge.await_args.kwargs["server"] == "calibre"
    assert bridge.await_args.kwargs["arguments"]["text"] == "neuromancer"
    assert bridge.await_args.kwargs["arguments"]["operation"] == "search"
