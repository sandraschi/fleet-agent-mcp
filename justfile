# fleet-agent-mcp justfile
import 'scripts/just/fleet.just'
# fleet-agent-mcp justfile

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# Start the agent server + webapp
start:
    pwsh -ExecutionPolicy Bypass -File "{{justfile_directory()}}\start.ps1"

# Start backend only (no webapp)
start-backend:
    Set-Location '{{justfile_directory()}}'
    .\.venv\Scripts\python.exe -m fleet_agent.server --http --port 10996

# Start webapp dev server only
start-webapp:
    Set-Location '{{justfile_directory()}}\webapp'
    npm run dev

# Force rebuild: reinstall editable, clear pycache, restart
rebuild:
    Set-Location '{{justfile_directory()}}'
    uv sync
    .\.venv\Scripts\python.exe -m pip install -e . --quiet --no-input 2>&1 | Out-Null
    Get-ChildItem -Path src -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Rebuild complete. Run 'just start' to launch."

# Build webapp for production
build-webapp:
    Set-Location '{{justfile_directory()}}\webapp'
    npm install
    npm run build

# Run tests
test:
    Set-Location '{{justfile_directory()}}'
    & "$env:USERPROFILE\.local\bin\uv.exe" run pytest tests/ -v

e2e:
    pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File "D:\Dev\repos\mcp-central-docs\scripts\playwright-audit.ps1" -RepoPath "{{justfile_directory()}}"

# Lint
lint:
    Set-Location '{{justfile_directory()}}'
    & "$env:APPDATA\Python\Python313\Scripts\ruff.exe" check src/ tests/

# Intel Reports Hub (iPad / Tailscale) — port 11027
intel-hub:
    pwsh -ExecutionPolicy Bypass -File "{{justfile_directory()}}\scripts\start-intel-hub.ps1"

# Start with stdio transport (for Cursor/Claude Desktop)
start-stdio:
    Set-Location '{{justfile_directory()}}'
    & "$env:USERPROFILE\.local\bin\uv.exe" run -m fleet_agent.server --stdio
