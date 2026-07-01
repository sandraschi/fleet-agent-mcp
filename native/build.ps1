$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RepoName = Split-Path -Leaf $Root
$Triple = "x86_64-pc-windows-msvc"
$ResourceDir = "$PSScriptRoot\resources"
$DevDir = "$PSScriptRoot\binaries"
New-Item -ItemType Directory -Force -Path $ResourceDir, $DevDir | Out-Null

Write-Host "=== ${RepoName} Tauri Release Build ===" -ForegroundColor Cyan

# Step 0: API_BASE verification (catches "Failed to fetch" before Tauri build)
Write-Host "-> [0/6] API_BASE verification..." -ForegroundColor Yellow
$apiFile = "$Root\webapp\src\lib\api.ts"
if (Test-Path $apiFile) {
    $apiContent = Get-Content $apiFile -Raw
    if ($apiContent -match "127.0.0.1:(\d+)") {
        $apiPort = [int]$Matches[1]
        if ($apiPort -ne 10996) {
            throw "API_BASE in $apiFile points to port $apiPort but backend serves on 10996. In dev Vite proxies work, in prod/NSIS this gives 'Failed to fetch'."
        }
        Write-Host "  API_BASE port: $apiPort (matches backend) OK" -ForegroundColor Green
    }
}

# Step 1: TypeScript lint gate + frontend build
$frontendDirs = @("web_sota", "webapp/frontend", "webapp")
foreach ($dir in $frontendDirs) {
    $frontend = Join-Path $Root $dir
    if (Test-Path "$frontend\package.json") {
        Write-Host "-> [1/6] Building frontend ($dir)..." -ForegroundColor Yellow
        Push-Location $frontend

        Write-Host "  tsc --noEmit..." -ForegroundColor Gray
        $tscOut = npx tsc --noEmit 2>&1
        $tscExit = $LASTEXITCODE
        if ($tscExit -ne 0) {
            Write-Host "  TypeScript compilation FAILED" -ForegroundColor Red
            Write-Host $tscOut
            throw "TypeScript compilation failed -- fix all errors before building NSIS installer"
        }

        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
        Pop-Location
        break
    }
}

# Step 2: Verify entry point exists before PyInstaller
Write-Host "-> [2/6] PyInstaller backend..." -ForegroundColor Yellow
$specFile = "$Root\${RepoName}-backend.spec"
if (-not (Test-Path $specFile)) {
    throw "Backend spec file not found at $specFile -- create ${RepoName}-backend.spec before building NSIS installer"
}
$entryFile = "$Root\run_server.py"
if (-not (Test-Path $entryFile)) {
    throw "run_server.py not found at $entryFile -- the spec file references this as the entry point"
}

Push-Location $Root

# Ensure pyinstaller in project venv
$pyiExe = "$Root\.venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $pyiExe)) {
    Write-Host "  Installing pyinstaller in project venv..." -ForegroundColor Yellow
    uv add --dev pyinstaller
}

# Pre-clean stale exe to avoid PermissionError on rebuild
Remove-Item "$Root\dist\${RepoName}-backend.exe" -Force -ErrorAction SilentlyContinue

# Patch fastmcp metadata fallback for frozen builds
$fm = "$Root\.venv\Lib\site-packages\fastmcp\__init__.py"
if (Test-Path $fm) {
    $c = Get-Content $fm -Raw
    if ($c -match 'except PackageNotFoundError:\s+    __version__ = _version\("fastmcp"\)') {
        $c = $c -replace 'except PackageNotFoundError:\s+    __version__ = _version\("fastmcp"\)', 'except PackageNotFoundError:
    try:
        __version__ = _version("fastmcp")
    except PackageNotFoundError:
        __version__ = "0.0.0"'
        Set-Content $fm -Value $c -Encoding utf8
        Write-Host "  Patched fastmcp metadata fallback" -ForegroundColor Yellow
    }
}

# Run PyInstaller via project venv
& $pyiExe "$specFile" --clean --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

# Gate: size check (>= 5 MB)
$frozenExe = "$Root\dist\${RepoName}-backend.exe"
if (-not (Test-Path $frozenExe)) { throw "Backend exe not found at $frozenExe" }
$sizeMB = [math]::Round((Get-Item $frozenExe).Length / 1MB, 1)
if ($sizeMB -lt 5) {
    throw "Backend exe is only ${sizeMB} MB -- PyInstaller produced an empty/broken binary. Check SKIP list, pathex, and run_server.py."
}
Write-Host "  Frozen binary: ${sizeMB} MB" -ForegroundColor Green

# Gate: smoke-test the frozen binary (catches ALL import crashes generically)
Write-Host "  Smoke-testing frozen binary..." -ForegroundColor Yellow
$testPort = 11999
$oldPort = $env:FLEET_AGENT_PORT; $oldHost = $env:FLEET_AGENT_HOST; $oldTauri = $env:FLEET_AGENT_TAURI
$env:FLEET_AGENT_PORT = "$testPort"; $env:FLEET_AGENT_HOST = "127.0.0.1"; $env:FLEET_AGENT_TAURI = "1"
$testProc = Start-Process -FilePath $frozenExe -NoNewWindow -PassThru -RedirectStandardError "$Root\dist\pyi-crash.log"
Start-Sleep -Seconds 5
$env:FLEET_AGENT_PORT = $oldPort; $env:FLEET_AGENT_HOST = $oldHost; $env:FLEET_AGENT_TAURI = $oldTauri
if ($testProc.HasExited) {
    $crash = Get-Content "$Root\dist\pyi-crash.log" -Raw
    throw "Frozen binary crashed on launch (exit $($testProc.ExitCode)):`n$crash"
}
$testProc.Kill(); $testProc.Dispose()
Remove-Item "$Root\dist\pyi-crash.log" -Force -ErrorAction SilentlyContinue
Write-Host "  Frozen binary smoke test PASSED" -ForegroundColor Green

Pop-Location

# Step 3: Embed in Tauri resources (+ dev fallback)
Write-Host "-> [3/6] Embedding backend..." -ForegroundColor Yellow
$src = "$Root\dist\${RepoName}-backend.exe"
if (-not (Test-Path $src)) { throw "Backend exe not found at $src -- PyInstaller step failed" }
Copy-Item $src "$ResourceDir\${RepoName}-backend.exe" -Force
Copy-Item $src "$DevDir\${RepoName}-backend-$Triple.exe" -Force
Write-Host "  Backend exe: ${sizeMB} MB" -ForegroundColor Green

# Bundle .env.example (NOT .env -- dev .env has personal API keys)
$envExample = "$Root\.env.example"
if (Test-Path $envExample) {
    Copy-Item $envExample "$ResourceDir\.env.example" -Force
    Write-Host "  Bundled .env.example OK" -ForegroundColor Green
} else {
    Write-Host "  WARNING: .env.example not found at repo root" -ForegroundColor DarkYellow
}

# Step 4: Single NSIS installer
Write-Host "-> [4/6] Tauri NSIS bundle..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
npx @tauri-apps/cli build --bundles nsis
if ($LASTEXITCODE -ne 0) { throw "Tauri build failed with exit code $LASTEXITCODE" }
Pop-Location

# Step 5: Stage to repo dist/
$distDir = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
$nsisDir = "$PSScriptRoot\target\release\bundle\nsis"
if (Test-Path $nsisDir) { Copy-Item "$nsisDir\*-setup.exe" "$distDir\" -Force }

# Step 6: Clean stray backend exe from Tauri target dir (prevents shadow copy)
$strayExe = "$PSScriptRoot\target\release\fleet-agent-mcp-backend.exe"
if (Test-Path $strayExe) { Remove-Item $strayExe -Force; Write-Host "  Cleaned stray: $strayExe" -ForegroundColor DarkGray }

Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Ship: $nsisDir\*.exe"
