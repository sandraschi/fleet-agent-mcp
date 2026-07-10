@echo off
cd /d "%~dp0"

:: Restart via NSSM if service exists
C:\Windows\System32\sc.exe query fleet-agent-mcp >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo fleet-agent-mcp service found -- restarting via NSSM
    "C:\Program Files\Jellyfin\Server\nssm.exe" restart fleet-agent-mcp
    echo Done.
    exit /b 0
)

:: Fallback: use pwsh
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
