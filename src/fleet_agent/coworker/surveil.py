"""fritz_surveil - fleet-domain triage engine (P3, per FLEET_DEEP_ANALYSIS §1).

One triage engine, two domains: external (aiwatcher surge - see
aiwatcher-mcp surge.py) and fleet (this module: hub health/uptime/supervisor
precursors). Severity: informational (log only) -> notice (hub inbox to
fritz) -> urgent (hub inbox to admiral + #sfb-alerts crosspost).

A triage ROUTER, not a SIEM: no new data store (hub is the source), one
destination chain (inbox -> admiral notify), dedupe per (server, rule).

Rules (default, overridable per server via set_thresholds):
- restart_loop: >= 3 supervisor restarts in the last 10 min -> urgent
- unreachable: last_status unreachable with >= 30 checks -> urgent,
  >= 10 checks -> notice (dedupe prevents spam for permanently-dead servers)
- degraded: uptime_pct < 60% (>= 20 checks) -> urgent; < 90% -> notice
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger("fleet_agent.surveil")

_STATE_FILE = Path.home() / ".fleet-agent" / "surveil_alerts.json"

DEFAULT_RULES: dict[str, dict[str, Any]] = {
    "restart_loop": {"window_minutes": 10, "min_restarts": 3, "severity": "urgent"},
    "unreachable": {"notice_checks": 10, "urgent_checks": 30},
    "degraded": {"notice_uptime": 90.0, "urgent_uptime": 60.0, "min_checks": 20},
}

#: Re-alert suppression per (server, rule) unless severity escalates.
DEDUPE_MINUTES = 60


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _state() -> dict[str, Any]:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"alerts": [], "last_seen": {}}


def _save(state: dict[str, Any]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _hub_headers() -> dict[str, str]:
    if settings.fleet_hub_token:
        return {"Authorization": f"Bearer {settings.fleet_hub_token}"}
    return {}


async def _hub_get(path: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{settings.fleet_hub_url.rstrip('/')}{path}", headers=_hub_headers()
        )
        resp.raise_for_status()
        return resp.json()


async def _hub_inbox(to_entity: str, subject: str, body: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.fleet_hub_url.rstrip('/')}/api/v1/inbox/send",
                json={
                    "to_entity": to_entity,
                    "from_entity": "fritz-surveil",
                    "subject": subject,
                    "body": body,
                },
                headers=_hub_headers(),
            )
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("surveil: inbox send failed: %s", exc)
        return False


def _parse_restart_ts(raw: Any) -> datetime | None:
    """Supervisor restart timestamps look like 'MM/DD/YYYY HH:MM:SS' (local)."""
    if isinstance(raw, dict):
        raw = raw.get("timestamp")
    if not raw:
        return None
    for fmt in ("%m/%d/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(raw), fmt)
        except ValueError:
            continue
    return None


def evaluate_server(
    server_id: str,
    *,
    last_status: str,
    total_checks: int,
    uptime_pct: float,
    restarts_recent: int,
    was_healthy: bool = True,
    rules: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    """Evaluate one server against the rules. Returns (severity, rule, text).

    Pure function - no I/O, unit-testable. Severity order:
    informational < notice < urgent.

    unreachable/degraded only fire when the server WAS healthy in the tracked
    window (healthy_checks >= 1) - triage catches change, not permanent state
    (servers registered but not running are registry hygiene, not alerts).
    """
    rules = rules or DEFAULT_RULES
    severity = "informational"
    rule = ""
    text = ""

    if restarts_recent >= int(rules["restart_loop"]["min_restarts"]):
        window = rules["restart_loop"]["window_minutes"]
        severity = "urgent"
        rule = "restart_loop"
        text = f"{server_id}: {restarts_recent} restarts in the last {window} min - restart loop"

    if last_status == "unreachable" and was_healthy:
        notice_checks = int(rules["unreachable"]["notice_checks"])
        urgent_checks = int(rules["unreachable"]["urgent_checks"])
        candidate = "notice" if total_checks >= notice_checks else "informational"
        candidate = "urgent" if total_checks >= urgent_checks else candidate
        if candidate != "informational":
            text = f"{server_id}: unreachable for {total_checks} consecutive health checks"
            rule = "unreachable"
            if candidate == "urgent":
                severity = "urgent"
            elif severity != "urgent":
                severity = "notice"

    if was_healthy and total_checks >= int(rules["degraded"]["min_checks"]):
        if uptime_pct < float(rules["degraded"]["urgent_uptime"]):
            if severity != "urgent":
                severity = "urgent"
                rule = "degraded"
                text = (
                    f"{server_id}: uptime {uptime_pct:.1f}% over {total_checks} checks"
                    " - severe degradation"
                )
        elif uptime_pct < float(rules["degraded"]["notice_uptime"]):
            if severity not in ("urgent",):
                severity = "notice"
                rule = "degraded"
                text = (
                    f"{server_id}: uptime {uptime_pct:.1f}% over {total_checks} checks - degraded"
                )

    return severity, rule, text


def _dedupe_allowed(state: dict[str, Any], server_id: str, rule: str, severity: str) -> bool:
    """True if this (server, rule) may alert again (escalation or DEDUPE_MINUTES passed)."""
    last = state["last_seen"].get(server_id, {}).get(rule)
    if not last:
        return True
    if severity == "urgent" and last.get("severity") != "urgent":
        return True  # escalation always fires
    try:
        last_ts = datetime.fromisoformat(last["ts"])
        if datetime.now(UTC) - last_ts > timedelta(minutes=DEDUPE_MINUTES):
            return True
    except Exception:
        return True
    return False


async def scan_fleet(server_filter: str | None = None) -> dict[str, Any]:
    """Scan all supervised servers (or one) and route triage hits."""
    supervisor = await _hub_get("/api/v1/supervisor/status")
    uptime = await _hub_get("/api/v1/health/uptime")
    servers = supervisor.get("servers", {})

    state = _state()
    hits: list[dict[str, Any]] = []
    window = timedelta(minutes=int(DEFAULT_RULES["restart_loop"]["window_minutes"]))

    for server_id, info in servers.items():
        if server_filter and server_id != server_filter:
            continue
        if not info.get("supervised"):
            continue

        upt = uptime.get(server_id, {})
        restarts_recent = 0
        for entry in info.get("restart_history", []):
            ts = _parse_restart_ts(entry)
            if ts is None:
                continue
            # restart timestamps are naive local; compare against local now
            if datetime.now() - ts <= window:
                restarts_recent += 1

        rules = _rules_for(server_id)
        severity, rule, text = evaluate_server(
            server_id,
            last_status=upt.get("last_status", "unknown"),
            total_checks=int(upt.get("total_checks", 0)),
            uptime_pct=float(upt.get("uptime_pct", 0.0)),
            restarts_recent=restarts_recent,
            was_healthy=int(upt.get("healthy_checks", 0)) >= 1,
            rules=rules,
        )
        if severity == "informational" or not rule:
            continue
        if not _dedupe_allowed(state, server_id, rule, severity):
            logger.info("surveil: %s/%s deduped (%s)", server_id, rule, severity)
            continue

        alert_id = str(uuid.uuid4())[:8]
        alert = {
            "id": alert_id,
            "ts": _now(),
            "server": server_id,
            "severity": severity,
            "rule": rule,
            "text": text,
            "acked": False,
        }
        state["alerts"].append(alert)
        state["last_seen"].setdefault(server_id, {})[rule] = {"ts": _now(), "severity": severity}
        hits.append(alert)

        if severity == "urgent":
            ok_inbox = await _hub_inbox("admiral", f"[surveil-urgent] {server_id}: {rule}", text)
            ok_sfb = await _sfb_alert(server_id, rule, text)
            alert["routed"] = {"inbox": ok_inbox, "sfb": ok_sfb}
            logger.warning(
                "SURVEIL urgent %s/%s: %s (inbox=%s sfb=%s)",
                server_id,
                rule,
                text,
                ok_inbox,
                ok_sfb,
            )
        else:
            ok_inbox = await _hub_inbox("fritz", f"[surveil-notice] {server_id}: {rule}", text)
            alert["routed"] = {"inbox": ok_inbox}
            logger.info("SURVEIL notice %s/%s: %s (inbox=%s)", server_id, rule, text, ok_inbox)

    _save(state)
    return {"success": True, "scanned": len(servers), "hits": hits, "rules": DEFAULT_RULES}


async def _sfb_alert(server_id: str, rule: str, text: str) -> bool:
    """Urgent hits crosspost to #sfb-alerts via the P2 hook (best effort)."""
    try:
        from .crosspost import crosspost_event

        result = await crosspost_event(
            "alerts",
            f"[surveil] {server_id}: {rule}",
            text,
            board_channel="fleet-pulse",
            category="blooper",
        )
        return bool(result.get("success"))
    except Exception as exc:
        logger.warning("surveil: sfb alert crosspost failed: %s", exc)
        return False


def alert_history(server_id: str | None = None, since: str | None = None) -> dict[str, Any]:
    state = _state()
    alerts = state["alerts"]
    if server_id:
        alerts = [a for a in alerts if a["server"] == server_id]
    if since:
        try:
            cutoff = datetime.fromisoformat(since)
            alerts = [a for a in alerts if datetime.fromisoformat(a["ts"]) >= cutoff]
        except Exception:
            pass
    return {"alerts": alerts, "count": len(alerts)}


def ack_alert(alert_id: str) -> dict[str, Any]:
    state = _state()
    for alert in state["alerts"]:
        if alert["id"] == alert_id:
            alert["acked"] = True
            _save(state)
            return {"success": True, "alert_id": alert_id}
    return {"success": False, "error": f"alert {alert_id} not found"}


def set_thresholds(server_id: str, rules: dict[str, Any]) -> dict[str, Any]:
    """Store a per-server rules override (same shape as DEFAULT_RULES)."""
    state = _state()
    state.setdefault("rules", {})[server_id] = rules
    _save(state)
    return {"success": True, "server_id": server_id, "rules": rules}


def _rules_for(server_id: str) -> dict[str, Any]:
    state = _state()
    return state.get("rules", {}).get(server_id) or DEFAULT_RULES
