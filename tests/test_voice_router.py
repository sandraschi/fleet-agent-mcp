"""Voice command bus routing (no live MCP)."""

from unittest.mock import AsyncMock, patch

import pytest

from fleet_agent.voice_registry import resolve_entity
from fleet_agent.voice_router import route_voice_intent


REGISTRY = {
    "entities": {
        "boomy": {"server": "yahboom", "aliases": ["boomy", "yahboom"]},
        "alexa": {"server": "alexa", "aliases": ["alexa"]},
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
    },
}


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
