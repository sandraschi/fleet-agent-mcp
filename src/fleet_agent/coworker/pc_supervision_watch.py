"""PC + fleet-state supervision watches: GPU/VRAM, workflow-instance health,
task-backlog age, and disk space.

Added 2026-09-08 after a leftover 'gate-test' workflow instance sat stuck in
an infinite gate<->review loop for over a week, permanently pinning the
4090's VRAM and starving the real task queue with nothing watching for it.
These complement agentic_loop._reap_if_stalled (the automatic hard-ceiling
fix) by surfacing the condition to Sandra instead of only self-healing
silently.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

from .common import save_artifact

logger = logging.getLogger("fleet_agent.coworker.pc_supervision_watch")


async def _escalate(subject: str, report: str) -> None:
    from ..settings_store import get_settings_store

    settings = get_settings_store()
    to = settings.get("heartbeat_email", "")
    smtp_host = settings.get("smtp_host", "")
    smtp_user = settings.get("smtp_user", "")
    smtp_pass = settings.get("smtp_pass", "")
    if not (to and smtp_host and smtp_user):
        return

    from ..mcp.tools.notify import _send_email_smtp

    await _send_email_smtp(
        to=to,
        subject=subject,
        body=report,
        smtp_host=smtp_host,
        smtp_port=int(settings.get("smtp_port", 587)),
        smtp_user=smtp_user,
        smtp_pass=smtp_pass,
    )


async def run_gpu_vram_watch(*, deliver: bool = True) -> dict[str, Any]:
    """Poll nvidia-smi + Ollama's loaded models; escalate if VRAM stays high."""
    from ..settings_store import get_settings_store

    settings = get_settings_store()
    threshold_pct = float(settings.get("gpu_vram_watch_pct_threshold", 75))

    try:
        out = (
            await asyncio.to_thread(
                subprocess.run,
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used,memory.total,utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        ).stdout.strip()
        used_mib, total_mib, util_pct = (float(x.strip()) for x in out.split(","))
    except Exception as exc:
        return {"success": False, "status": "unknown", "message": f"nvidia-smi failed: {exc}"}

    pct_used = (used_mib / total_mib * 100) if total_mib else 0.0

    loaded_models: list[dict[str, Any]] = []
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://127.0.0.1:11434/api/ps")
            if r.status_code == 200:
                loaded_models = r.json().get("models", [])
    except Exception:
        pass

    status = "red" if pct_used >= threshold_pct else "green"
    models_str = (
        ", ".join(
            f"{m.get('name', '?')} ({m.get('size_vram', 0) // (1024**2)}MiB)" for m in loaded_models
        )
        or "none"
    )

    report = (
        f"# GPU/VRAM Watch\nGenerated: {datetime.now(UTC).isoformat()}\n\n"
        f"VRAM: {used_mib:.0f}/{total_mib:.0f} MiB ({pct_used:.1f}%), GPU util {util_pct:.0f}%\n"
        f"Ollama loaded: {models_str}\n"
    )
    artifact_path = save_artifact("gpu-vram-watch", report, "Europe/Vienna")

    if status == "red" and deliver:
        await _escalate(f"GPU VRAM WATCH RED - {pct_used:.0f}% used", report)

    return {
        "success": True,
        "status": status,
        "message": (
            f"VRAM {pct_used:.0f}% ({used_mib:.0f}/{total_mib:.0f} MiB), loaded: {models_str}"
        ),
        "artifact_path": artifact_path,
    }


async def run_workflow_health_watch(*, deliver: bool = True) -> dict[str, Any]:
    """Surface non-archived workflow instances approaching the reaper's hard ceiling."""
    from ..engine.sqlite_store import get_store
    from ..settings_store import get_settings_store

    store = get_store()
    settings = get_settings_store()
    warn_age_hours = float(settings.get("workflow_instance_warn_age_hours", 2))

    active = store.list_active_instances()
    now = datetime.now(UTC)
    warnings: list[str] = []
    for inst in active:
        try:
            started = datetime.fromisoformat(inst["started_at"])
        except (KeyError, ValueError):
            continue
        age_hours = (now - started).total_seconds() / 3600
        if age_hours >= warn_age_hours:
            warnings.append(
                f"{inst['workflow_name']} @ {inst['current_node']}: "
                f"age={age_hours:.1f}h (auto-reaped at 6h)"
            )

    recent_reaps = [e for e in store.get_execution_log(limit=20) if e.get("event") == "blocked"]

    status = "yellow" if warnings else "green"
    report_lines = [
        "# Workflow Instance Health",
        f"Generated: {now.isoformat()}",
        "",
        f"Non-archived instances: {len(active)}",
    ]
    report_lines.extend(f"- WARN: {w}" for w in warnings)
    if recent_reaps:
        report_lines.append(f"Recently blocked/reaped (last 20 log entries): {len(recent_reaps)}")

    report = "\n".join(report_lines)
    artifact_path = save_artifact("workflow-health-watch", report, "Europe/Vienna")

    if status == "yellow" and deliver:
        await _escalate("WORKFLOW HEALTH WATCH - instance approaching stall ceiling", report)

    return {
        "success": True,
        "status": status,
        "message": f"{len(active)} active instance(s), {len(warnings)} warning(s)",
        "artifact_path": artifact_path,
    }


async def run_task_backlog_watch(*, deliver: bool = True) -> dict[str, Any]:
    """Alert if the real (non-recurring) task backlog is old or large."""
    from ..engine.sqlite_store import get_store
    from ..settings_store import get_settings_store

    store = get_store()
    settings = get_settings_store()
    warn_age_hours = float(settings.get("task_backlog_warn_age_hours", 48))
    warn_count = int(settings.get("task_backlog_warn_count", 20))

    pending = [t for t in store.todo_list(status="pending") if not t.get("recurrence")]
    now = datetime.now(UTC)
    oldest_age_hours = 0.0
    oldest_task = ""
    for t in pending:
        try:
            created = datetime.fromisoformat(t["created_at"])
        except (KeyError, ValueError):
            continue
        age = (now - created).total_seconds() / 3600
        if age > oldest_age_hours:
            oldest_age_hours = age
            oldest_task = t.get("task", "")[:80]

    status = (
        "red" if (oldest_age_hours >= warn_age_hours or len(pending) >= warn_count) else "green"
    )
    report = (
        f"# Task Backlog Age Watch\nGenerated: {now.isoformat()}\n\n"
        f"Pending non-recurring tasks: {len(pending)}\n"
        f"Oldest: {oldest_age_hours:.1f}h - {oldest_task}\n"
    )
    artifact_path = save_artifact("task-backlog-watch", report, "Europe/Vienna")

    if status == "red" and deliver:
        await _escalate(
            f"TASK BACKLOG WATCH RED - {len(pending)} pending, oldest {oldest_age_hours:.0f}h",
            report,
        )

    return {
        "success": True,
        "status": status,
        "message": f"{len(pending)} pending, oldest {oldest_age_hours:.1f}h",
        "artifact_path": artifact_path,
    }


async def run_disk_watch(*, deliver: bool = True) -> dict[str, Any]:
    """Check free disk space on the drives fleet dev work depends on."""
    from ..settings_store import get_settings_store

    settings = get_settings_store()
    min_free_pct = float(settings.get("disk_watch_min_free_pct", 10))
    drives = settings.get("disk_watch_drives", ["C:\\", "D:\\"])

    status = "green"
    lines = ["# Disk Watch", f"Generated: {datetime.now(UTC).isoformat()}", ""]
    low: list[str] = []
    for drive in drives:
        try:
            total, _used, free = shutil.disk_usage(drive)
        except Exception as exc:
            lines.append(f"- {drive}: check failed ({exc})")
            continue
        free_pct = free / total * 100 if total else 0.0
        lines.append(f"- {drive}: {free / (1024**3):.1f} GiB free ({free_pct:.1f}%)")
        if free_pct < min_free_pct:
            low.append(drive)
            status = "red"

    report = "\n".join(lines)
    artifact_path = save_artifact("disk-watch", report, "Europe/Vienna")

    if status == "red" and deliver:
        await _escalate(f"DISK WATCH RED - low space: {', '.join(low)}", report)

    return {
        "success": True,
        "status": status,
        "message": "; ".join(lines[3:]) if len(lines) > 3 else "ok",
        "artifact_path": artifact_path,
    }
