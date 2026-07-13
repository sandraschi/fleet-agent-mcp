param([switch]$Headless)

$svc = Get-Service -Name fleet-agent-mcp -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq 'Running') {
    Write-Host 'fleet-agent-mcp service is running -- starting frontend only' -ForegroundColor Cyan
    $Root = $PSScriptRoot
    $WebRoot = Join-Path $Root "webapp"
    Push-Location $WebRoot
    npm run dev
    Pop-Location
    exit
}

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

$portResolve = @{
    Ports      = @($WebPort, $BackendPort)
    Label      = "fleet-agent-mcp"
    AllowReuse = $ReuseIfRunning
}
if ($ReuseIfRunning) {
    $portResolve.HealthChecks = @{
        $WebPort = "http://127.0.0.1:$WebPort/"
        $BackendPort = "http://127.0.0.1:$BackendPort/health"
    }
}
$portState = Resolve-FleetPortConflict @portResolve
if ($portState.Action -eq 'Blocked') { exit 1 }
if ($portState.Reuse) { return }

Set-Location $Root
& "$env:USERPROFILE\.local\bin\uv.exe" sync

# Force editable install to bypass uv build cache
& "$Root\.venv\Scripts\python.exe" -m pip install -e "$Root" --quiet --no-input 2>&1 | Out-Null

# Clear pycache for fresh module load
Get-ChildItem -Path "$Root\src" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$IntelHubScript = Join-Path $Root "scripts\start-intel-hub.ps1"
if (Test-Path -LiteralPath $IntelHubScript) {
    & $IntelHubScript -Root $Root
}

if ($Headless) {
    # Headless: run backend inline - long runner for supervisor / NSSM
    & "$Root\.venv\Scripts\python.exe" -B -m fleet_agent.server --http --port $BackendPort
} else {
    # Interactive: full stack with webapp
    Push-Location "$Root\webapp"
    npm install --silent
    Pop-Location

    $BackendJob = Start-Job -Name "fleet-agent-backend" -ScriptBlock {
        param($Root, $BackendPort)
        Set-Location $Root
        & "$Root\.venv\Scripts\python.exe" -B -m fleet_agent.server --http --port $BackendPort
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


