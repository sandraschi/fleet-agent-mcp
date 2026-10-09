# Fleet MCPB pack shim - delegates to the central fleet pack script.
# Do not vendor pack logic here; fixes land centrally.
param(
    [string]$Version = ""
)
$ErrorActionPreference = "Stop"
$FleetPack = "D:\Dev\repos\mcp-central-docs\scripts\fleet-mcpb-pack.ps1"
if (-not (Test-Path -LiteralPath $FleetPack)) {
    Write-Host "ERROR: fleet pack script not found: $FleetPack" -ForegroundColor Red
    exit 1
}
$args2 = @()
if ($Version -ne "") { $args2 += @("-Version", $Version) }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $FleetPack @args2
