# Start Fleet Intel Reports Hub (port 11027) if not already listening.
param(
    [int]$Port = 11027,
    [string]$Root = $PSScriptRoot + "\.."
)

$Root = (Resolve-Path -LiteralPath $Root).Path

function Test-PortListening {
    param([int]$PortNum)
    try {
        $conn = Get-NetTCPConnection -LocalPort $PortNum -State Listen -ErrorAction SilentlyContinue
        return ($null -ne $conn)
    } catch {
        return $false
    }
}

if (Test-PortListening -PortNum $Port) {
    Write-Host "Intel Reports Hub already listening on :$Port" -ForegroundColor DarkGreen
    exit 0
}

$uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
if (-not (Test-Path -LiteralPath $uv)) {
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($uvCmd) { $uv = $uvCmd.Source } else {
        Write-Host "WARN: uv not found - Intel Hub not started" -ForegroundColor Yellow
        exit 1
    }
}

$env:INTEL_REPORTS_HUB_PORT = "$Port"
$env:INTEL_REPORTS_HUB_HOST = if ($env:INTEL_REPORTS_HUB_HOST) { $env:INTEL_REPORTS_HUB_HOST } else { "0.0.0.0" }

Write-Host "Starting Intel Reports Hub on :$Port ..." -ForegroundColor Cyan
Set-Location $Root
Start-Process pwsh -ArgumentList @(
    '-NoProfile', '-Command',
    ('' + "& '" + $uv + "' run -m fleet_agent.intel_hub")
) -WindowStyle Hidden

Start-Sleep -Seconds 2
if (Test-PortListening -PortNum $Port) {
    Write-Host "Intel Reports Hub online: http://127.0.0.1:$Port" -ForegroundColor Green
} else {
    Write-Host "Intel Hub may still be starting - check http://127.0.0.1:$Port" -ForegroundColor Yellow
}
