# Fleet-agent + pywinauto Cua loop

**Servers:** `fleet_bridge` alias **`pywinauto`** (`http://127.0.0.1:10788/mcp`) + optional **`libreoffice`** (headless) / **`libreoffice-ext`** (live Writer).

## Orchestration pattern

1. **Lumen** plans a desktop task (e.g. verify Calc UI after a convert job).
2. `fleet_call_tool(server="pywinauto", tool="get_window_state", arguments={...})`
3. `fleet_call_tool(server="pywinauto", tool="automation_elements", arguments={ snapshot_id, element_index, dispatch: "background" })`
4. For PDF/ODT deliverables, call **`libreoffice`** convert tools instead of GUI clicking.

## Prerequisites

- `pywinauto-mcp` HTTP up (`web_sota/start.ps1` → **10789**).
- Computer-use profile: **not** the default IDE webapp MCP chain ([WEBAPP_STANDARDS §7](file:///D:/Dev/repos/mcp-central-docs/standards/WEBAPP_STANDARDS.md)).
- Optional: `PYWINAUTO_MCP_DISPATCH=background`, `PYWINAUTO_MCP_TRAJECTORY_LOG=1`.

## Reference

- [CUA_DRIVER_AND_PYWINAUTO.md](file:///D:/Dev/repos/mcp-central-docs/patterns/CUA_DRIVER_AND_PYWINAUTO.md)
- `pywinauto-mcp/docs/CUA_PARITY.md`
