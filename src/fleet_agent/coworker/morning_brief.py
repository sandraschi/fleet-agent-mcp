"""WF-001 — Morning brief: start morning_brief workflow + optional ViLife snapshot."""

from __future__ import annotations

from typing import Any

from ..config import settings
from ..engine.state_machine import get_state_machine
from ..engine.workflow_loader import discover_workflows
from .common import fleet_call, now_label, save_artifact
from .day_prep import DAY_PREP_PROJECT

MORNING_BRIEF_WORKFLOW = "morning_brief"


def _ensure_morning_brief_registered() -> None:
    sm = get_state_machine()
    if sm.get_workflow(MORNING_BRIEF_WORKFLOW):
        return
    for path in discover_workflows(settings.project_root):
        if "morning_brief" in path.replace("\\", "/"):
            sm.register_workflow(path)
            return
    raise FileNotFoundError("morning_brief.yaml not found under workflows/")


async def run_morning_brief(*, deliver: bool = True) -> dict[str, Any]:
    """Register WF-001, start if idle, return current node task + ViLife brief."""
    _ensure_morning_brief_registered()
    sm = get_state_machine()
    instance = sm.status()

    if instance is None:
        instance = sm.start(MORNING_BRIEF_WORKFLOW)
        started = True
    elif instance.workflow_name != MORNING_BRIEF_WORKFLOW:
        return {
            "success": False,
            "message": (
                f"Another workflow is active: {instance.workflow_name} → {instance.current_node}. "
                "Finish or reset before morning_brief."
            ),
        }
    else:
        started = False

    task = sm.get_current_task() or ""
    vilife = await fleet_call(
        "vienna-life",
        "vienna_life",
        {"operation": "life_brief"},
    )

    pulse_date = now_label()
    lines = [
        f"# Morning Brief — {pulse_date}",
        "",
        f"**Workflow:** `{MORNING_BRIEF_WORKFLOW}` → `{instance.current_node}`",
        f"**Started fresh:** {started}",
        "",
        "## Current step (agent executes via fleet_bridge)",
        "",
        task,
        "",
        "## ViLife snapshot (vienna-life-assistant)",
        "",
        str(vilife.get("data", vilife)),
    ]
    report = "\n".join(lines)
    artifact = save_artifact(
        DAY_PREP_PROJECT,
        f"morning-brief-{pulse_date.replace(' ', '-').replace(':', '')}",
        report,
    )

    return {
        "success": True,
        "message": f"Morning brief ready at node '{instance.current_node}'",
        "workflow": instance.workflow_name,
        "current_node": instance.current_node,
        "task": task,
        "vilife_brief": vilife,
        "artifact_path": str(artifact) if artifact else None,
        "report": report,
    }
