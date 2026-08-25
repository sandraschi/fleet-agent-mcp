param([string]$RepoRoot)
if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }
Set-Location $RepoRoot

Write-Host "=== MCPB SOTA Packaging: fleet-agent-mcp ===" -ForegroundColor Cyan

$proj = Get-Content pyproject.toml -Raw
$name = if ($proj -match '(?m)^name = "(.*)"') { $matches[1] } else { "fleet-agent-mcp" }
$ver = if ($proj -match '(?m)^version = "(.*)"') { $matches[1] } else { "0.2.2" }
$pkg = "fleet_agent"

$mcpbDir = Join-Path $RepoRoot "mcpb"
$distDir = Join-Path $RepoRoot "dist"
New-Item -ItemType Directory -Force -Path $mcpbDir, $distDir | Out-Null

# Step 1: Fresh stage — wipe mcpb/src and recopy src/fleet_agent
Write-Host "-> [1/5] Staging fresh source tree (src/$pkg -> mcpb/src/$pkg)..." -ForegroundColor Yellow
$mcpbSrc = Join-Path $mcpbDir "src"
if (Test-Path $mcpbSrc) { Remove-Item -Recurse -Force $mcpbSrc }
$stagePkg = Join-Path $mcpbSrc $pkg
New-Item -ItemType Directory -Force -Path $stagePkg | Out-Null
Copy-Item -Recurse -Force (Join-Path $RepoRoot "src\$pkg\*") $stagePkg
Write-Host "  Staged $pkg source OK" -ForegroundColor Green

# Step 2: Copy assets (icon.png + prompts)
Write-Host "-> [2/5] Staging assets..." -ForegroundColor Yellow
$assetsDst = Join-Path $mcpbDir "assets"
if (Test-Path $assetsDst) { Remove-Item -Recurse -Force $assetsDst }
New-Item -ItemType Directory -Force -Path $assetsDst | Out-Null
if (Test-Path (Join-Path $RepoRoot "assets")) {
    Copy-Item -Recurse -Force (Join-Path $RepoRoot "assets\*") $assetsDst
}
Write-Host "  Assets staged OK" -ForegroundColor Green

# Step 3: Manifest & .mcpbignore
Write-Host "-> [3/5] Syncing manifest.json & .mcpbignore..." -ForegroundColor Yellow
$desc = "Self-evolving AI agent — state machine, task management, knowledge accumulation, identity."
$entry = "src/fleet_agent/server.py"
$manifestJson = @{
    manifest_version = "0.2"
    name = $name
    version = $ver
    description = $desc
    author = @{ name = "Sandra Schipal" }
    server = @{
        type = "python"
        entry_point = $entry
        mcp_config = @{
            command = "uv"
            args = @("run", "--directory", "${PWD}", "python", "-m", "fleet_agent.server")
            env = @{
                PYTHONPATH = "${PWD}/src"
                PYTHONUNBUFFERED = "1"
            }
        }
    }
} | ConvertTo-Json -Depth 5
$manifestJson | Set-Content (Join-Path $mcpbDir "manifest.json") -Encoding utf8

$ignoreLines = @(
    "tests/", ".git/", "__pycache__/", "*.pyc", ".venv/", "dist/", "build/", "target/",
    "webapp/node_modules/", "webapp/dist/", "node_modules/", ".ruff_cache/", ".pytest_cache/",
    "*.bak", "*.bak.*", "*.orig", "*.rej"
)
$ignoreLines | Set-Content (Join-Path $mcpbDir ".mcpbignore") -Encoding utf8

# Step 4: 3-4-100 Rule Verification
Write-Host "-> [4/5] 3-4-100 Prompts Verification..." -ForegroundColor Yellow
function Get-WordCount([string]$path) {
    if (-not (Test-Path $path)) { return 0 }
    return (@(Get-Content -Raw $path) -split '\s+' | Where-Object { $_ }).Count
}
$sysWords = Get-WordCount (Join-Path $RepoRoot "assets\prompts\system.md")
$userWords = Get-WordCount (Join-Path $RepoRoot "assets\prompts\user.md")
$exPath = Join-Path $RepoRoot "assets\prompts\examples.json"
$exCount = if (Test-Path $exPath) { (Get-Content $exPath -Raw | ConvertFrom-Json).Count } else { 0 }

Write-Host "  system.md: $sysWords words (min 3000)" -ForegroundColor Green
Write-Host "  user.md:   $userWords words (min 4000)" -ForegroundColor Green
Write-Host "  examples:  $exCount items (min 100)" -ForegroundColor Green

if ($sysWords -lt 3000 -or $userWords -lt 4000 -or $exCount -lt 100) {
    throw "3-4-100 FAIL: system=$sysWords, user=$userWords, examples=$exCount (need 3000/4000/100)"
}

# Step 5: mcpb pack
Write-Host "-> [5/5] Packing MCPB bundle..." -ForegroundColor Yellow
$outMcpb = Join-Path $distDir "$name-v$ver.mcpb"
Push-Location $mcpbDir
npx --yes @anthropic-ai/mcpb pack . $outMcpb
$exitCode = $LASTEXITCODE
Pop-Location

if ($exitCode -ne 0 -or -not (Test-Path $outMcpb)) {
    throw "mcpb pack failed with exit code $exitCode"
}

$mcpbSize = [math]::Round((Get-Item $outMcpb).Length / 1MB, 2)
Write-Host "=== MCPB Bundle complete: $outMcpb (${mcpbSize} MB) ===" -ForegroundColor Green
