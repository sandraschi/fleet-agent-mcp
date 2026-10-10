# Installation

## Claude Desktop add-on (Windows)

`.mcpb` add-ons are a Claude Desktop format. Open **Windows PowerShell** and run:

```powershell
irm https://github.com/sandraschi/fleet-agent-mcp/releases/latest/download/install.ps1 | iex
```

This installs the `fleet-agent-mcp.mcpb` add-on from the latest GitHub release (and `uv` if it is missing).
Alternatively: download `fleet-agent-mcp.mcpb` from the [latest release](https://github.com/sandraschi/fleet-agent-mcp/releases/latest)
and double-click it, then fully restart Claude Desktop.

## Quick Start (source)

```powershell
# Install just if you don't have it
winget install Casey.Just    # Windows
# scoop install just          # Windows (alternative)
# brew install just           # macOS
# sudo apt install just       # Debian/Ubuntu
# cargo install just          # Linux (Rust)

git clone https://github.com/sandraschi/fleet-agent-mcp
cd fleet-agent-mcp
just
```

The interactive recipe dashboard opens in your browser. From there:

```powershell
just bootstrap   # install all dependencies
just serve       # start the server
just web         # start the frontend (if applicable)
```

> **Why not `pip install`?** MCP servers bundle webapps, configs, project scaffolding, and tooling that a flat Python package can't deliver. PyPI offers no safety advantage — it doesn't audit packages either. `just` gives you the complete, ready-to-run stack.

---

## 🐌 Traditional Setup

If you prefer not to use `just`:

1. Install [Python 3.13+](https://python.org) and [uv](https://docs.astral.sh/uv/)
2. Clone and enter the repo:
   ```powershell
   git clone https://github.com/sandraschi/fleet-agent-mcp
   cd fleet-agent-mcp
   ```
3. Install dependencies:
   ```powershell
   uv sync --all-extras
   ```
4. Start the server:
    ```powershell
    # stdio mode (for MCP clients like Claude Desktop)
    uv run python -m fleet_agent --stdio
    # (`python -m fleet_agent_mcp --stdio` is an equivalent alias.)

    # HTTP mode (for web dashboard)
    .\start.ps1 -BackendOnly
    # (serves the REST API + /mcp on http://127.0.0.1:10996)
    ```

4. (optional) Start the frontend:
   ```powershell
   cd webapp
   npm install
   npm run dev
   ```

5. Open `http://localhost:10996` or the frontend URL.

---

## ❓ Troubleshooting

| Issue | Fix |
|---|---|
| `just` not found | Install via `winget install Casey.Just`, `scoop install just`, or `brew install just` |
| Port conflict | Run `just kill-all` to clear fleet ports (10700–11000) |
| Dependencies out of sync | `uv sync --all-extras` |
| Something else | [Open a GitHub issue](https://github.com/sandraschi/fleet-agent-mcp/issues) |

---

*See the main [README](README.md) for feature overview and documentation.*
