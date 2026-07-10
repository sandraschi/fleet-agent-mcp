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
%NSSM% set fleet-agent-mcp AppStdout "%DIR%\logs\service-stdout.log"
%NSSM% set fleet-agent-mcp AppStderr "%DIR%logs\service-stderr.log"
%NSSM% set fleet-agent-mcp Start SERVICE_AUTO_START
%NSSM% set fleet-agent-mcp AppRotateFiles 1
%NSSM% set fleet-agent-mcp AppRotateSeconds 86400
%NSSM% set fleet-agent-mcp AppRotateBytes 10485760

%NSSM% start fleet-agent-mcp
echo fleet-agent-mcp service installed and started
