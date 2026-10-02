# Contributing to fleet-agent-mcp

Thanks for looking at Fritz's code. This is a small, personal fleet-agent project, but
patches, bug reports, and ideas are welcome.

## Setup

```powershell
git clone https://github.com/sandraschi/fleet-agent-mcp
cd fleet-agent-mcp
uv sync
```

See [INSTALL.md](INSTALL.md) for the full setup guide, or run `just bootstrap` if you
have [`just`](https://github.com/casey/just) installed.

## Running the server

```powershell
.\start.ps1
# Server at http://127.0.0.1:10996
```

Or for stdio (Cursor / Claude Desktop):

```powershell
uv run -m fleet_agent.server --stdio
```

## Tests

```powershell
uv run pytest tests/ -q
```

Please run the full test suite before opening a PR. Tests that touch the SQLite store
or state machine are isolated to a per-test temp database (see `tests/conftest.py`) -
never point tests at the live `~/.fleet-agent/fleet-agent.db`.

## Linting

This project uses [Ruff](https://github.com/astral-sh/ruff) for Python and
[Biome](https://biomejs.dev) for the webapp (TypeScript/React).

```powershell
uv run ruff check src/
cd webapp && npx biome check .
```

## Pull requests

- Keep PRs focused - one fix or feature per PR.
- Add or update tests for anything behavioral.
- Describe *why* the change is needed, not just what changed.
- Small, reviewable diffs are preferred over large sweeping ones.

## Code of conduct

Be direct, be technical, be kind. Standard open-source courtesy applies.
