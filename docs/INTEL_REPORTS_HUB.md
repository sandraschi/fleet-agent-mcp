# Fleet Intel Reports Hub

Pretty HTML reports from **any fleet member**, served on a lightweight hub for iPad reading over Tailscale or Funnel. Fritz and AIWatcher are wired in; others use `POST /api/reports/publish` (see `mcp-central-docs/patterns/intel-reports-hub.md`).

## Ports

| Service | Port | URL |
|---------|------|-----|
| Intel Reports Hub | **11027** | `http://<goliath>:11027/` |
| Fritz backend | 10996 | publishes + ingests to AIWatcher |
| AIWatcher backend | 10946 | publishes digests to hub |

## Start

```powershell
# From fleet-agent-mcp (starts hub automatically)
.\start.ps1

# Hub only
just intel-hub
# or
.\scripts\start-intel-hub.ps1
```

From AIWatcher (ensure hub is up):

```powershell
.\scripts\ensure-intel-hub.ps1
```

## What gets published

| Source | Trigger | Content |
|--------|---------|---------|
| Fritz | Fleet Pulse | Full pulse markdown → HTML |
| Fritz | Office Day Prep | Combined prep report |
| Fritz | → AIWatcher | Summary event in Fleet Events feed |
| AIWatcher | Daily digest job | `html_body` from digest |
| AIWatcher | `POST /api/digest/send` | Same digest to hub |
| Fritz | Devices Watch | New critical home incidents (CO, smoke, kitchen temp, Ring) |
| Manual | `intel_reports_publish` MCP tool | Any markdown |
| Manual | `intel_reports_list` MCP tool | Catalog JSON (read-only) |

## Fritz → AIWatcher ingest

After Fleet Pulse / Day Prep, Fritz calls `ingest_fleet_event` on AIWatcher (MCP, REST fallback).

Manual:

```text
aiwatcher_push_event(
  title="Fleet Pulse — 18/20 MCP online",
  summary="Pipeline degraded: 1 critical alert",
  urgency_hint=7.5
)
```

Env (optional, if `AIWATCHER_API_KEY` is set):

| Variable | Default |
|----------|---------|
| `FLEET_AGENT_AIWATCHER_HTTP_BASE` | `http://127.0.0.1:10946` |
| `FLEET_AGENT_AIWATCHER_API_KEY` | (empty) |

## iPad access (Tailscale)

### Same tailnet (recommended)

Hub binds `0.0.0.0:11027` by default. On iPad Safari:

```
http://<goliath-tailscale-name>:11027/
```

Example: `http://goliath:11027/reports/abc123`

### Tailscale Funnel (public HTTPS)

On Goliath:

```powershell
tailscale funnel 11027
```

Copy the `https://….ts.net` URL from the command output — open on iPad anywhere.

To stop:

```powershell
tailscale funnel --https=11027 off
```

## Storage

Reports live under `%USERPROFILE%\.fleet-intel\` (override: `INTEL_REPORTS_DIR`).

- `index.json` — catalog
- `reports/{id}.html` — full pages

## API

```http
GET  /                     — index (HTML)
GET  /reports/{id}         — report (HTML)
GET  /api/health           — status JSON
GET  /api/reports          — list JSON
POST /api/reports/publish  — {title, source, html|markdown, summary?, tags?}
```

## Env reference

| Variable | Default | Used by |
|----------|---------|---------|
| `INTEL_REPORTS_HUB_PORT` | `11027` | Hub server |
| `INTEL_REPORTS_HUB_HOST` | `0.0.0.0` | Hub bind address |
| `INTEL_REPORTS_HUB_URL` | `http://127.0.0.1:11027` | Any fleet repo (httpx client) |

## Urgent email (Fritz)

When degradation or hot intel exceeds thresholds, Fritz sends **email** (if SMTP + `heartbeat_email` set) and posts to **cursor inbox**:

| Trigger | Condition |
|---------|-----------|
| Fleet Pulse | Pipeline critical or >50% MCP servers offline |
| Day Prep | Hot AIWatcher items with urgency ≥ `urgent_email_threshold` |
| Devices Watch | New critical from devices-mcp `/api/fleet/priority` (5m poll) |
| Cursor spend | warn/critical (existing behavior) |

Settings (`~/.fleet-agent/settings.json`):

| Key | Default |
|-----|---------|
| `urgent_email_enabled` | `true` |
| `urgent_email_threshold` | `8.0` |
| `coworker_devices_watch_enabled` | `true` |
| `devices_watch_interval` | `300` (seconds) |
| `devices_mcp_http_base` | `http://127.0.0.1:10717` |

Urgent emails include a link to the hub report when publish succeeded.

## MCP tools

| Tool | Purpose |
|------|---------|
| `intel_reports_publish(title, markdown, source?, summary?)` | Publish HTML report |
| `intel_reports_list(limit=20)` | List catalog entries |
| `aiwatcher_push_event(title, summary?, source?, url?, urgency_hint?)` | Push to AIWatcher Fleet Events |
| `coworker_devices_watch(deliver=True)` | Poll devices-mcp priority now |
