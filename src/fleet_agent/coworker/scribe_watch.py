"""Scribe watch — session-scribe freshness monitoring + digest rollup.

Created 2026-07-17 (advanced-memory-mcp TODO P1, scribe v2 Fritz integration).
The session scribe (advanced-memory-mcp scripts/session_scribe.py, hourly
scheduled task) auto-captures Claude session digests into the vault inbox and
aiwatcher's data/inbox. This flow makes sure capture never silently stops:

- RED:    scribe state file missing or older than the stale threshold
          (scheduled task broken / machine issue) -> email escalation.
- YELLOW: recent scribe log contains errors, or vault digest exists but the
          aiwatcher inbox copy is missing.
- GREEN:  fresh state, clean log. Report notes how many digests await review.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .common import log_project_note, save_artifact

logger = logging.getLogger("fleet_agent.coworker.scribe_watch")

STATE_FILE = Path.home() / ".advanced-memory" / "scribe_state.json"
SCRIBE_LOG = Path(r"C:\temp\session-scribe.log")
VAULT_INBOX = Path.home() / ".advanced-memory" / "vault" / "inbox"
AIWATCHER_INBOX = Path(r"D:\Dev\repos\aiwatcher-mcp\data\inbox")
STALE_HOURS = 3.0


def _state_age_hours() -> float | None:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        last = datetime.fromisoformat(data["last_run"])
        return (datetime.now(UTC) - last).total_seconds() / 3600.0
    except Exception:
        return None


def _log_errors(max_lines: int = 200) -> list[str]:
    try:
        lines = SCRIBE_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-max_lines:]
        return [ln.strip()[:160] for ln in lines if "Traceback" in ln or "Error" in ln][-5:]
    except OSError:
        return []


def _pending_digests() -> tuple[list[str], list[str]]:
    vault = (
        sorted(p.name for p in VAULT_INBOX.glob("*session-scribe*.md"))
        if VAULT_INBOX.is_dir()
        else []
    )
    aiw = (
        sorted(p.name for p in AIWATCHER_INBOX.glob("*session-scribe*.md"))
        if AIWATCHER_INBOX.is_dir()
        else []
    )
    return vault, aiw


async def run_scribe_watch(*, deliver: bool = True) -> dict[str, Any]:
    """Check session-scribe health, save report, escalate if capture stopped."""
    from ..settings_store import get_settings_store

    settings = get_settings_store()

    age = _state_age_hours()
    errors = _log_errors()
    vault_digests, aiw_digests = _pending_digests()
    missing_copies = sorted(set(vault_digests) - set(aiw_digests))

    if age is None:
        status = "red"
        headline = "scribe state file missing/unreadable - has the scribe ever run?"
    elif age > STALE_HOURS:
        status = "red"
        headline = (
            f"scribe stale: last run {age:.1f}h ago "
            f"(threshold {STALE_HOURS}h) - scheduled task likely broken"
        )
    elif errors:
        status = "yellow"
        headline = f"scribe running but log shows {len(errors)} error line(s)"
    elif missing_copies:
        status = "yellow"
        headline = f"{len(missing_copies)} digest(s) missing from aiwatcher inbox copy"
    else:
        status = "green"
        headline = (
            f"scribe healthy: last run {age:.1f}h ago, "
            f"{len(vault_digests)} digest(s) awaiting review"
        )

    report_lines = [
        f"# Scribe Watch — {datetime.now(UTC).isoformat()}",
        "",
        f"**Status: {status.upper()}** — {headline}",
        "",
        f"- state age: {'n/a' if age is None else f'{age:.2f}h'} (stale > {STALE_HOURS}h)",
        f"- vault inbox digests awaiting review: {len(vault_digests)}",
        f"- aiwatcher inbox copies: {len(aiw_digests)}",
    ]
    if errors:
        report_lines += ["", "## Log errors", *[f"- {e}" for e in errors]]
    if missing_copies:
        report_lines += ["", "## Missing aiwatcher copies", *[f"- {n}" for n in missing_copies]]

    report = "\n".join(report_lines)
    artifact_path = save_artifact("scribe-watch", report, "Europe/Vienna")

    if status != "green":
        try:
            log_project_note(
                "main",
                f"scribe watch {status.upper()}",
                report,
                tags=["fleet-agent", "session-scribe", "monitoring", status],
            )
        except Exception as exc:  # noqa: BLE001 - vault write is best-effort
            logger.warning("scribe_watch: vault note failed: %s", exc)

    if status == "red" and deliver:
        to = settings.get("heartbeat_email", "")
        smtp_host = settings.get("smtp_host", "")
        smtp_user = settings.get("smtp_user", "")
        smtp_pass = settings.get("smtp_pass", "")
        if to and smtp_host and smtp_user:
            from ..mcp.tools.notify import _send_email_smtp

            await _send_email_smtp(
                to=to,
                subject=f"SCRIBE WATCH — RED — {headline}",
                body=report,
                smtp_host=smtp_host,
                smtp_port=int(settings.get("smtp_port", 587)),
                smtp_user=smtp_user,
                smtp_pass=smtp_pass,
            )

    return {
        "success": True,
        "status": status,
        "message": f"Scribe watch: {status.upper()} — {headline}",
        "pending_digests": len(vault_digests),
        "artifact_path": artifact_path,
    }
