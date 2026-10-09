# Local biome gate for webapp-like roots (fleet template, minimal).
$ErrorActionPreference = "Stop"
$roots = @("webapp", "web_sota", "webapp/frontend", "web") | Where-Object { Test-Path $_ }
if (-not $roots) { Write-Host "biome: no web root, skipping."; exit 0 }
$Bun = "$env:USERPROFILE\.bun\bin\bun.exe"
foreach ($r in $roots) {
    Write-Host "biome: checking $r ..."
    & $Bun run --cwd $r biome:ci
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host "biome: clean."
