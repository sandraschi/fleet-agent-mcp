@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Please run as Administrator
    pause
    exit /b 1
)

set NSSM="C:\Program Files\Jellyfin\Server\nssm.exe"
set DIR=%~dp0

%NSSM% stop fleet-agent-mcp 2>nul
%NSSM% remove fleet-agent-mcp confirm 2>nul

%NSSM% install fleet-agent-mcp "%DIR%run-fleet-agent-service.bat"
%NSSM% set fleet-agent-mcp AppDirectory "%DIR%"

REM --- Environment pinning (REQUIRED - do not remove) -------------------------
REM NSSM services run as LocalSystem. Under that account USERPROFILE/APPDATA/
REM LOCALAPPDATA resolve to C:\WINDOWS\system32\config\systemprofile\..., NOT to
REM the developer profile. fleet_agent resolves data_dir, identity, workflows and
REM the intel hub via Path.home(), so without this pin the service writes to a
REM second, invisible store while every write still reports success.
REM On 2026-07-26 this produced two divergent fleet-agent.db files running at the
REM same time. See mcp-central-docs/standards/TRAPS_AND_PITFALLS.md trap 14.
%NSSM% set fleet-agent-mcp AppEnvironmentExtra "USERPROFILE=%USERPROFILE%" "APPDATA=%APPDATA%" "LOCALAPPDATA=%LOCALAPPDATA%" "FLEET_AGENT_DATA_DIR=%USERPROFILE%\.fleet-agent" "INTEL_REPORTS_DIR=%USERPROFILE%\.fleet-intel"
%NSSM% set fleet-agent-mcp AppStdout "%DIR%\logs\service-stdout.log"
%NSSM% set fleet-agent-mcp AppStderr "%DIR%logs\service-stderr.log"
%NSSM% set fleet-agent-mcp Start SERVICE_AUTO_START
%NSSM% set fleet-agent-mcp AppRotateFiles 1
%NSSM% set fleet-agent-mcp AppRotateSeconds 86400
%NSSM% set fleet-agent-mcp AppRotateBytes 10485760

%NSSM% start fleet-agent-mcp
echo fleet-agent-mcp service installed and started
