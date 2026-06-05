"""Seed default coworker recurring tasks on server boot."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ..engine.sqlite_store import get_store
from ..settings_store import get_settings_store
from .common import coworker_type
from .flows import COWORKER_FLOWS

logger = logging.getLogger("fleet_agent.coworker.bootstrap")


def is_fleet_pulse_task(task: dict[str, Any]) -> bool:
    return coworker_type(task) == "fleet_pulse"


def is_coworker_task(task: dict[str, Any]) -> bool:
    return coworker_type(task) is not None


def ensure_coworker_tasks() -> dict[str, Any]:
    """Idempotently register all enabled coworker recurring pulse tasks."""
    store = get_store()
    settings = get_settings_store()
    seeded: list[str] = []
    skipped: list[str] = []

    backdate = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    now = datetime.now(UTC).isoformat()

    for flow_key, spec in COWORKER_FLOWS.items():
        if not settings.get(spec["enabled_setting"], spec["default_enabled"]):
            skipped.append(flow_key)
            continue

        task_id = spec["id"]
        existing = store.todo_get(task_id)
        if existing and existing.get("status") == "pending":
            skipped.append(flow_key)
            continue

        recurrence = settings.get(spec["recurrence_setting"], spec["default_recurrence"])
        store.todo_upsert({
            "id": task_id,
            "task": spec["task"],
            "group": "self",
            "group_name": "self",
            "priority": "high",
            "status": "pending",
            "created_at": now,
            "updated_at": backdate,
            "completed_at": None,
            "recurrence": recurrence,
            "metadata": {"coworker": flow_key},
        })
        seeded.append(flow_key)
        logger.info("Seeded coworker flow %s (%s)", flow_key, recurrence)

    tz = settings.get("coworker_timezone", "Europe/Vienna")
    return {
        "success": True,
        "seeded": seeded,
        "skipped": skipped,
        "message": (
            f"Coworker bootstrap: seeded {len(seeded)} ({', '.join(seeded) or 'none'}), "
            f"timezone {tz}"
        ),
    }
