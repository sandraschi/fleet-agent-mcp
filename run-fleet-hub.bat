@echo off
cd /d D:\Dev\repos\fleet-agent-mcp
set PATH=C:\Users\sandr\.local\bin;%PATH%
"%~dp0.venv\Scripts\python.exe" -m fleet_agent.intel_hub
