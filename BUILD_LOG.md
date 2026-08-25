# BUILD_LOG.md — fleet-agent-mcp (v0.2.2)

> **Build Date:** 2026-08-25  
> **Release:** v0.2.2  
> **Tier:** T2 (Webapp + MCPB + Tauri NSIS Desktop Installer)

---

## Artifacts Produced

| Artifact | Path | Size | Description |
|---|---|---|---|
| **MCPB Bundle** | `dist/fleet-agent-mcp-v0.2.2.mcpb` | 0.2 MB | Claude Desktop bundle with 3-4-100 SOTA prompts & `src/fleet_agent` layout |
| **Tauri NSIS Installer** | `dist/Fleet Agent MCP_0.2.2_x64-setup.exe` | ~38 MB | Single NSIS desktop installer embedding PyInstaller frozen sidecar (`fleet-agent-mcp-backend.exe`, 28.7 MB) |

---

## Build History & Regressions Encountered

### 1. MCPB Packaging (`scripts/mcpb-pack.ps1`)
- **Issue**: Initial `.mcpbignore` had `src/*` which stripped the package source directory.
- **Fix**: Removed `src/*` from `$ignoreLines` array so `src/fleet_agent` is preserved under `mcpb/src/fleet_agent`.
- **Verification**: 3-4-100 prompts rule passed (`system.md`: 6,215 words, `user.md`: 7,023 words, `examples.json`: 105 entries). Manifest validation passed. Total 94 files included.

### 2. PyInstaller Frozen Sidecar (`fleet-agent-mcp-backend.spec`)
- **Issue**: `copy_metadata("fastapi")` threw `PackageNotFoundError: No package metadata was found for fastapi` because `fastapi` was not directly installed in venv.
- **Fix**: Wrapped `copy_metadata(pkg)` calls in `try...except` block and set `upx=False` per Tauri production pitfalls standard.
- **Verification**: Frozen backend binary `fleet-agent-mcp-backend.exe` (28.7 MB) built and passed automated launch smoke-test on test port 11999.

### 3. Tauri NSIS Single Installer (`native/build.ps1`)
- **Issue**: Initial version was `0.2.1` in `native/tauri.conf.json`.
- **Fix**: Updated `native/tauri.conf.json` to `"version": "0.2.2"` to align with `pyproject.toml` and release tag.
- **Verification**: `makensis` produced `Fleet Agent MCP_0.2.2_x64-setup.exe` in `native/target/release/bundle/nsis/` and staged to `dist/`.

---

*Log maintained by Antigravity Fleet Operations.*
