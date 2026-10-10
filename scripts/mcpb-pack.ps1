#Requires -Version 5.1
# Fleet MCPB pack shim - delegates to the central fleet pack script.
# Do not vendor pack logic here; fixes land centrally.
# Bundle version comes from mcpb/manifest.json (the central script reads it).
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$FleetPack = Join-Path (Split-Path -Parent $RepoRoot) 'mcp-central-docs\scripts\fleet-mcpb-pack.ps1'
if (-not (Test-Path -LiteralPath $FleetPack)) {
    $FleetPack = 'D:\Dev\repos\mcp-central-docs\scripts\fleet-mcpb-pack.ps1'
}
if (-not (Test-Path -LiteralPath $FleetPack)) {
    Write-Host "ERROR: fleet pack script not found: $FleetPack" -ForegroundColor Red
    exit 1
}
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $FleetPack -RepoRoot $RepoRoot
