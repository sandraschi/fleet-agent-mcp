# Build Log — fleet-agent-mcp

## 2026-07-01 — v0.1.0 NSIS Build

| Metric | Value |
|--------|-------|
| Build time | ~8 min (PyInstaller 1min + Rust 2.5min + NSIS) |
| Installer size | 30.4 MB |
| Backend exe | 26.9 MB |
| Frontend | 3.4 KB gzip |

### Gates
- [x] API_BASE verification (port 10996) — PASS
- [x] TypeScript lint (tsc --noEmit + tsc -b) — PASS
- [x] Frontend build (vite) — PASS
- [x] PyInstaller frozen binary — PASS (26.9 MB)
- [x] Size gate (>= 5 MB) — PASS (26.9 MB)
- [x] Frozen binary smoke test — PASS
- [x] Rust compilation (cargo check) — PASS (2 warnings: unused import, unused mut)
- [x] NSIS installer — PASS (30.4 MB)

### Output
- `native/target/release/bundle/nsis/Fleet Agent MCP_0.1.0_x64-setup.exe`
- Staged to `dist/Fleet Agent MCP_0.1.0_x64-setup.exe`

### Notes
- WSL not enabled for this build; manual build on Windows.
- PyInstaller `--clean` forces full rebuild each time (no incremental).
- `beforeBuildCommand` disabled in tauri.conf.json for manual pipeline; re-enable for CI.
