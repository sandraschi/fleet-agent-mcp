import pytest
from unittest.mock import AsyncMock, patch
from fleet_agent.acp_server import FleetACPAgent
from acp.schema import TextContentBlock

@pytest.mark.asyncio
async def test_acp_agent_initialize() -> None:
    agent = FleetACPAgent()
    res = await agent.initialize(protocol_version=1)
    assert res.protocol_version == 1
    assert res.agent_info is not None
    assert res.agent_info.name == "fleet-agent-acp"

@pytest.mark.asyncio
async def test_acp_agent_sessions() -> None:
    agent = FleetACPAgent()
    res = await agent.new_session(cwd="/workspace")
    session_id = res.session_id
    assert session_id is not None
    assert agent.active_sessions[session_id] == "/workspace"

    res_list = await agent.list_sessions()
    assert len(res_list.sessions) == 1
    assert res_list.sessions[0].session_id == session_id
    assert res_list.sessions[0].cwd == "/workspace"

    # Close session
    await agent.close_session(session_id=session_id)
    assert session_id not in agent.active_sessions

@pytest.mark.asyncio
async def test_acp_agent_prompt() -> None:
    agent = FleetACPAgent()
    conn = AsyncMock()
    agent.on_connect(conn)

    with patch("fleet_agent.llm_client.chat_completion_stream") as mock_stream:
        # Mock chat completion stream yielding some tokens
        async def mock_generator(*args, **kwargs):
            yield 'data: {"c": "Hello"}\n\n'
            yield 'data: {"c": " world"}\n\n'
            yield 'data: {"done": true}\n\n'

        mock_stream.side_effect = mock_generator

        prompt_block = TextContentBlock(text="Who are you?", type="text")
        res = await agent.prompt(session_id="session-1", prompt=[prompt_block])

        assert res.stop_reason == "end_turn"
        # Verify conn.session_update was called for the two content chunks
        assert conn.session_update.call_count == 2
