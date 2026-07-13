import asyncio
import json
import logging
import uuid
from typing import Any

from acp import Agent, run_agent
from acp.interfaces import Client
from acp.schema import (
    AgentCapabilities,
    AgentMessageChunk,
    AuthenticateResponse,
    CloseSessionResponse,
    ForkSessionResponse,
    Implementation,
    InitializeResponse,
    ListSessionsResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    ResumeSessionResponse,
    SessionInfo,
    SetSessionConfigOptionResponse,
    SetSessionModeResponse,
    TextContentBlock,
)

logger = logging.getLogger("fleet-agent.acp")

class FleetACPAgent(Agent):
    def __init__(self) -> None:
        self.conn: Client | None = None
        self.active_sessions: dict[str, str] = {}

    def on_connect(self, conn: Client) -> None:
        self.conn = conn
        logger.info("ACP client connected")

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: Any = None,
        client_info: Any = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        logger.info(f"ACP initialized with version: {protocol_version}")
        return InitializeResponse(
            protocol_version=protocol_version,
            agent_info=Implementation(name="fleet-agent-acp", version="0.1.0"),
            agent_capabilities=AgentCapabilities(),
        )

    async def new_session(
        self,
        cwd: str,
        additional_directories: list[str] | None = None,
        mcp_servers: list[Any] | None = None,
        **kwargs: Any,
    ) -> NewSessionResponse:
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = cwd
        logger.info(f"Created new ACP session: {session_id} for cwd: {cwd}")
        return NewSessionResponse(session_id=session_id)

    async def load_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: list[Any] | None = None,
        additional_directories: list[str] | None = None,
        **kwargs: Any,
    ) -> LoadSessionResponse | None:
        self.active_sessions[session_id] = cwd
        logger.info(f"Loaded ACP session: {session_id}")
        return LoadSessionResponse(session_id=session_id)

    async def list_sessions(
        self, cwd: str | None = None, cursor: str | None = None, **kwargs: Any
    ) -> ListSessionsResponse:
        sessions = [
            SessionInfo(session_id=sid, cwd=dir_path)
            for sid, dir_path in self.active_sessions.items()
        ]
        return ListSessionsResponse(sessions=sessions)

    async def set_session_mode(
        self, session_id: str, mode_id: str, **kwargs: Any
    ) -> SetSessionModeResponse | None:
        return None

    async def set_config_option(
        self, config_id: str, session_id: str, value: Any, **kwargs: Any
    ) -> SetSessionConfigOptionResponse | None:
        return None

    async def authenticate(self, method_id: str, **kwargs: Any) -> AuthenticateResponse | None:
        return None

    async def prompt(
        self,
        session_id: str,
        prompt: list[Any],
        **kwargs: Any,
    ) -> PromptResponse:
        # Extract user prompt query text
        query_text = ""
        for block in prompt:
            if hasattr(block, "text") and block.text:
                query_text += block.text

        logger.info(f"ACP Prompt received for session {session_id}: {query_text[:100]}...")

        if not query_text:
            return PromptResponse(stop_reason="end_turn")

        # Call Fritz stream chat logic
        from .llm_client import build_system_prompt, chat_completion_stream
        from .settings_store import get_settings_store

        model = get_settings_store().get("model", "")
        all_messages = build_system_prompt() + [{"role": "user", "content": query_text}]

        try:
            async for sse_line in chat_completion_stream(all_messages, model):
                # Parse the SSE line
                # e.g., data: {"c": "hello"}\n\n
                if sse_line.startswith("data: "):
                    content_str = sse_line[len("data: "):].strip()
                    if not content_str:
                        continue
                    try:
                        data = json.loads(content_str)
                        if "c" in data:
                            delta = data["c"]
                            if self.conn:
                                await self.conn.session_update(
                                    session_id=session_id,
                                    update=AgentMessageChunk(
                                        session_update="agent_message_chunk",
                                        content=TextContentBlock(text=delta, type="text"),
                                    ),
                                )
                        elif "error" in data:
                            err = data["error"]
                            if self.conn:
                                await self.conn.session_update(
                                    session_id=session_id,
                                    update=AgentMessageChunk(
                                        session_update="agent_message_chunk",
                                        content=TextContentBlock(
                                            text=f"\n[Error: {err}]\n", type="text"
                                        ),
                                    ),
                                )
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Error handling ACP prompt: {e}")
            if self.conn:
                await self.conn.session_update(
                    session_id=session_id,
                    update=AgentMessageChunk(
                        session_update="agent_message_chunk",
                        content=TextContentBlock(
                            text=f"\n[Internal Error: {e}]\n", type="text"
                        ),
                    ),
                )

        return PromptResponse(stop_reason="end_turn")

    async def fork_session(
        self,
        session_id: str,
        cwd: str,
        additional_directories: list[str] | None = None,
        mcp_servers: list[Any] | None = None,
        **kwargs: Any,
    ) -> ForkSessionResponse:
        new_sid = str(uuid.uuid4())
        self.active_sessions[new_sid] = cwd
        logger.info(f"Forked session {session_id} to new session {new_sid}")
        return ForkSessionResponse(session_id=new_sid)

    async def resume_session(
        self,
        session_id: str,
        cwd: str,
        additional_directories: list[str] | None = None,
        mcp_servers: list[Any] | None = None,
        **kwargs: Any,
    ) -> ResumeSessionResponse:
        self.active_sessions[session_id] = cwd
        logger.info(f"Resumed session: {session_id}")
        return ResumeSessionResponse(session_id=session_id)

    async def close_session(self, session_id: str, **kwargs: Any) -> CloseSessionResponse | None:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        logger.info(f"Closed session: {session_id}")
        return CloseSessionResponse(session_id=session_id)

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        logger.info(f"Cancelled processing for session: {session_id}")

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        pass


def run_acp_server() -> None:
    logger.info("Starting Fritz ACP stdio agent server...")
    asyncio.run(run_agent(FleetACPAgent()))
