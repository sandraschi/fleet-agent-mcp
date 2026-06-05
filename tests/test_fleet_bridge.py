"""Tests for the fleet_bridge subsystem — cross-server MCP client."""

from unittest.mock import AsyncMock, patch

import pytest


class TestFleetServerRegistry:
    def test_all_servers_have_url(self):
        from fleet_agent.mcp.tools.fleet_bridge import FLEET_SERVERS
        for alias, info in FLEET_SERVERS.items():
            assert "url" in info, f"{alias} missing url"
            assert info["url"].startswith("http"), f"{alias} url not http"
            assert "/mcp" in info["url"], f"{alias} url missing /mcp path"

    def test_all_servers_have_description(self):
        from fleet_agent.mcp.tools.fleet_bridge import FLEET_SERVERS
        for alias, info in FLEET_SERVERS.items():
            assert "description" in info, f"{alias} missing description"
            assert len(info["description"]) > 10, f"{alias} description too short"

    def test_all_servers_have_category(self):
        from fleet_agent.mcp.tools.fleet_bridge import FLEET_SERVERS
        valid = {
            "code", "orchestration", "knowledge", "communication", "media",
            "research", "automation", "robotics", "office", "smart_home",
            "intelligence", "life", "security", "infra",
        }
        for alias, info in FLEET_SERVERS.items():
            assert "category" in info, f"{alias} missing category"
            assert info["category"] in valid, f"{alias} invalid category: {info['category']}"

    def test_server_count(self):
        from fleet_agent.mcp.tools.fleet_bridge import FLEET_SERVERS
        assert len(FLEET_SERVERS) >= 9

    def test_key_tools_are_lists(self):
        from fleet_agent.mcp.tools.fleet_bridge import FLEET_SERVERS
        for alias, info in FLEET_SERVERS.items():
            assert "key_tools" in info, f"{alias} missing key_tools"
            assert isinstance(info["key_tools"], list), f"{alias} key_tools not list"
            assert len(info["key_tools"]) >= 2, f"{alias} key_tools too few"

    def test_all_ports_unique(self):
        from fleet_agent.mcp.tools.fleet_bridge import FLEET_SERVERS
        ports = []
        for info in FLEET_SERVERS.values():
            port = info["url"].split(":")[-1].split("/")[0]
            ports.append(port)
        assert len(ports) == len(set(ports)), "Duplicate ports detected"


class TestFleetDiscover:
    @pytest.mark.asyncio
    async def test_fleet_discover_structure(self):
        from fleet_agent.mcp.tools.fleet_bridge import FLEET_SERVERS, fleet_discover
        result = await fleet_discover()
        assert "success" in result
        assert "data" in result
        assert "servers" in result["data"]
        assert len(result["data"]["servers"]) == len(FLEET_SERVERS)
        for server in result["data"]["servers"]:
            assert "alias" in server
            assert "url" in server
            assert "online" in server
            assert isinstance(server["online"], bool)


class TestFleetCallTool:
    def test_vla_legacy_alias_maps_to_robotics(self):
        from fleet_agent.mcp.tools.fleet_bridge import (
            FLEET_SERVER_ALIASES,
            FLEET_SERVERS,
        )
        assert FLEET_SERVER_ALIASES.get("vla") == "vla-robotics"
        assert "vla-robotics" in FLEET_SERVERS
        assert "vienna-life" in FLEET_SERVERS
        assert FLEET_SERVERS["vla-robotics"]["url"] != FLEET_SERVERS["vienna-life"]["url"]

    @pytest.mark.asyncio
    async def test_unknown_alias_returns_error(self):
        from fleet_agent.mcp.tools.fleet_bridge import fleet_call_tool
        result = await fleet_call_tool(server="nonexistent", tool="test")
        assert result["success"] is False
        assert "Unknown" in result["message"]

    @pytest.mark.asyncio
    async def test_direct_url_accepted(self):
        from fleet_agent.mcp.tools.fleet_bridge import fleet_call_tool
        result = await fleet_call_tool(
            server="http://127.0.0.1:99999/mcp",
            tool="test",
        )
        assert result["success"] is False


class TestFleetInspectRepo:
    @pytest.mark.asyncio
    async def test_fleet_inspect_repo_unknown_server(self):
        with patch(
            "fleet_agent.mcp.tools.fleet_bridge.fleet_call_tool",
            AsyncMock(return_value={"success": False, "message": "not reachable", "data": {}}),
        ):
            from fleet_agent.mcp.tools.fleet_bridge import fleet_inspect_repo
            result = await fleet_inspect_repo(repo_path="D:/nonexistent")
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_fleet_inspect_repo_with_aspect(self):
        mock_result = {
            "success": True,
            "message": "Agent completed",
            "data": {"job_id": "abc123", "status": "completed", "output": "All good"},
        }
        with patch(
            "fleet_agent.mcp.tools.fleet_bridge.fleet_call_tool",
            AsyncMock(return_value=mock_result),
        ) as mock_call:
            from fleet_agent.mcp.tools.fleet_bridge import fleet_inspect_repo
            result = await fleet_inspect_repo(repo_path="D:/Dev/repos/test", aspect="tests")
            assert result["success"] is True
            mock_call.assert_called_once()
            args = mock_call.call_args.kwargs
            assert args["server"] == "opencode"
            assert args["tool"] == "opencode_run_agent"
            assert "test suite" in args["arguments"]["prompt"].lower()

    @pytest.mark.asyncio
    async def test_fleet_inspect_repo_waits_by_default(self):
        with patch(
            "fleet_agent.mcp.tools.fleet_bridge.fleet_call_tool",
            AsyncMock(return_value={"success": True, "data": {}, "message": "ok"}),
        ) as mock_call:
            from fleet_agent.mcp.tools.fleet_bridge import fleet_inspect_repo
            await fleet_inspect_repo(repo_path="D:/Dev/repos/test")
            assert mock_call.call_args.kwargs["arguments"]["wait"] is True
