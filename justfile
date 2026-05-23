# fleet-agent-mcp justfile

# Open the interactive recipe dashboard in the browser
default:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File ../mcp-central-docs/scripts/just-dashboard.ps1 -Path .

# Start the agent server + webapp
start:
    pwsh -ExecutionPolicy Bypass -File "{{justfile_directory()}}\start.ps1"

# Start backend only (no webapp)
start-backend:
    Set-Location '{{justfile_directory()}}'
    & "$env:USERPROFILE\.local\bin\uv.exe" run -m fleet_agent.server --http --port 10996

# Start webapp dev server only
start-webapp:
    Set-Location '{{justfile_directory()}}\webapp'
    npm run dev

# Build webapp for production
build-webapp:
    Set-Location '{{justfile_directory()}}\webapp'
    npm install
    npm run build

# Run tests
test:
    Set-Location '{{justfile_directory()}}'
    & "$env:USERPROFILE\.local\bin\uv.exe" run pytest tests/ -v

# Lint
lint:
    Set-Location '{{justfile_directory()}}'
    & "$env:APPDATA\Python\Python313\Scripts\ruff.exe" check src/ tests/

# Start with stdio transport (for Cursor/Claude Desktop)
start-stdio:
    Set-Location '{{justfile_directory()}}'
    & "$env:USERPROFILE\.local\bin\uv.exe" run -m fleet_agent.server --stdio
