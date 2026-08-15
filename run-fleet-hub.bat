@echo off
cd /d D:\Dev\repos\fleet-agent-mcp
set PATH=C:\Users\sandr\.local\bin;%PATH%
if not defined INTEL_REPORTS_HUB_USER set INTEL_REPORTS_HUB_USER=fleet
if not defined INTEL_REPORTS_HUB_PASS set INTEL_REPORTS_HUB_PASS=intel
"%~dp0.venv\Scripts\python.exe" -m fleet_agent.intel_hub
