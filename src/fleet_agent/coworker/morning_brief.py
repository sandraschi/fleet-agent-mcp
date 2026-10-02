"""WF-001 - Morning brief: start morning_brief workflow + optional ViLife snapshot."""

from __future__ import annotations

from typing import Any

from ..config import settings
from ..engine.state_machine import get_state_machine
from ..engine.workflow_loader import discover_workflows
from .common import fleet_call, now_label, save_artifact
from .day_prep import DAY_PREP_PROJECT

MORNING_BRIEF_WORKFLOW = "morning_brief"


async def _launch_contract_summary() -> str:
    """Run the fleet launch-contract checker, return a markdown section.

    Never raises: on any error returns a section saying the check was
    skipped, so a broken checker can never break the morning brief.
    """
    import asyncio
    import os
    from pathlib import Path

    try:
        repos_root = os.environ.get("FLEET_REPOS_ROOT") or str(Path(settings.project_root).parent)
        script = Path(repos_root) / "mcp-central-docs" / "scripts" / "Test-FleetLaunchContract.ps1"
        if not script.is_file():
            return "## Launch contract\n\ncheck skipped: script not found.\n"
        proc = await asyncio.create_subprocess_exec(
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(script),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=180)
        except asyncio.TimeoutError:
            proc.kill()
            return "## Launch contract\n\ncheck timed out after 180s.\n"
        text = out.decode("utf-8", errors="replace").strip()
        fails = [ln for ln in text.splitlines() if ln.startswith("[FAIL]")]
        if proc.returncode == 0 and not fails:
            return "## Launch contract\n\nall module-serve backends satisfy the launch contract.\n"
        body = "\n".join(fails) if fails else text[-2000:]
        return f"## Launch contract\n\n{len(fails)} FAIL(s) - fix before launchers rot:\n\n```\n{body}\n```\n"
    except Exception as exc:  # noqa: BLE001 - brief must survive
        return f"## Launch contract\n\ncheck skipped: {exc}.\n"


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
    launch_contract = await _launch_contract_summary()
    lines = [
        f"# Morning Brief - {pulse_date}",
        "",
        f"**Workflow:** `{MORNING_BRIEF_WORKFLOW}` → `{instance.current_node}`",
        f"**Started fresh:** {started}",
        "",
        "## Current step (agent executes via fleet_bridge)",
        "",
        task,
        "",
        launch_contract,
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
        "launch_contract": launch_contract,
        "artifact_path": str(artifact) if artifact else None,
        "report": report,
    }
