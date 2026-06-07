param([switch]$Headless)

# --- SOTA Headless Standard ---
if ($Headless -and ($Host.UI.RawUI.WindowTitle -notmatch 'Hidden')) {
    Start-Process pwsh -ArgumentList '-NoProfile', '-File', $PSCommandPath, '-Headless' -WindowStyle Hidden
    exit
}
# ------------------------------

$WebPort = 10997
$BackendPort = 10996
$Root = $PSScriptRoot

$FleetStartPath = Join-Path $Root "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath
Stop-FleetPortSquatters -Ports @($BackendPort, $WebPort) -Label "fleet-agent-mcp"

Set-Location $Root
& "$env:USERPROFILE\.local\bin\uv.exe" sync

if ($Headless) {
    # Headless: run backend inline - long runner for supervisor / NSSM
    & "$env:USERPROFILE\.local\bin\uv.exe" run -m fleet_agent.server --http --port $BackendPort
} else {
    # Interactive: full stack with webapp
    Push-Location "$Root\webapp"
    npm install --silent
    Pop-Location

    $BackendJob = Start-Job -Name "fleet-agent-backend" -ScriptBlock {
        param($Root, $BackendPort)
        Set-Location $Root
        & "C:\Users\sandr\.local\bin\uv.exe" run -m fleet_agent.server --http --port $BackendPort
    } -ArgumentList $Root, $BackendPort

    $WebappJob = Start-Job -Name "fleet-agent-webapp" -ScriptBlock {
        param($Root, $WebPort)
        Set-Location "$Root\webapp"
        npm run dev
    } -ArgumentList $Root, $WebPort

    Write-Host "fleet-agent-mcp starting..."
    Write-Host "  Backend: http://127.0.0.1:$BackendPort"
    Write-Host "  Webapp:  http://127.0.0.1:$WebPort"

    Start-Sleep -Seconds 4
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/api/whoami" -UseBasicParsing -TimeoutSec 3
        Write-Host "  Backend online."
    } catch {
        Write-Host "  Backend not yet ready - retrying..."
        Start-Sleep -Seconds 4
    }

    try { Start-Process "http://127.0.0.1:$WebPort" } catch { }
    Write-Host "Press Ctrl+C to stop."

    try {
        while ($true) {
            Receive-Job -Name "fleet-agent-backend" -ErrorAction SilentlyContinue | Out-Host
            Receive-Job -Name "fleet-agent-webapp" -ErrorAction SilentlyContinue | Out-Host
            Start-Sleep -Seconds 2
        }
    } finally {
        Stop-Job -Name "fleet-agent-backend" -ErrorAction SilentlyContinue
        Stop-Job -Name "fleet-agent-webapp" -ErrorAction SilentlyContinue
        Remove-Job -Name "fleet-agent-backend" -Force -ErrorAction SilentlyContinue
        Remove-Job -Name "fleet-agent-webapp" -Force -ErrorAction SilentlyContinue
    }
}

