"""State machine workflow tools — YAML-defined, enforced step execution.

Inspired by kagura-agent/flowforge: prevents agents from skipping steps by
enforcing a DAG of nodes with branching conditions and terminal states.

[RATIONAL]: Consolidates workflow CRUD + execution into one tool set because
the state machine, persistence, and advancement logic form a single concern.
"""

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from ...config import settings
from ...engine.state_machine import get_state_machine
from ...engine.workflow_loader import discover_workflows
from ..registry import mcp


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def workflow_define(
    yaml_path: Annotated[str, Field(description="Path to workflow YAML file.")],
    ctx: Context = None,
) -> dict[str, Any]:
    """Register a workflow from a YAML file.

    Workflows are state machines that enforce step-by-step execution.
    They support linear progression, branching (condition-based), and terminal nodes.

    ## Return Format
    {"success": bool, "workflow": {"name": str, "nodes": int, "start": str}, "message": str}

    ## Examples
    workflow_define("workflows/daily.yaml")
    """
    sm = get_state_machine()
    try:
        wf = sm.register_workflow(yaml_path)
        return {
            "success": True,
            "workflow": {
                "name": wf.name,
                "description": wf.description,
                "node_count": len(wf.nodes),
                "start": wf.start,
            },
            "message": f"Workflow '{wf.name}' registered with {len(wf.nodes)} nodes.",
        }
    except FileNotFoundError as e:
        return {"success": False, "error": str(e), "message": "Workflow file not found."}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to register workflow."}


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def workflow_autodiscover(
    ctx: Context = None,
) -> dict[str, Any]:
    """Auto-discover and register all YAML workflows from ./workflows/
    and ~/.fleet-agent/workflows/.

    ## Return Format
    {"success": bool, "registered": int, "workflows": list[str], "message": str}

    ## Examples
    workflow_autodiscover()
    """
    sm = get_state_machine()
    paths = discover_workflows(settings.project_root)
    registered = []
    errors = []
    for path in paths:
        try:
            wf = sm.register_workflow(path)
            registered.append(wf.name)
        except Exception as e:
            errors.append(f"{path}: {e}")
    return {
        "success": True,
        "registered": len(registered),
        "workflows": registered,
        "errors": errors,
        "message": f"Registered {len(registered)} workflows from {len(paths)} files.",
    }


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def workflow_start(
    name: Annotated[str, Field(description="Name of the registered workflow to start.")],
    ctx: Context = None,
) -> dict[str, Any]:
    """Start a new workflow instance.

    ## Return Format
    {"success": bool, "instance": dict, "first_task": str, "message": str}

    ## Examples
    workflow_start("daily")
    """
    sm = get_state_machine()
    try:
        instance = sm.start(name)
        task = sm.get_current_task()
        return {
            "success": True,
            "instance": instance.to_dict(),
            "first_task": task,
            "message": (
                f"Workflow '{name}' started at node '{instance.current_node}'."
                f" Current task: {task}"
            ),
        }
    except ValueError as e:
        return {"success": False, "error": str(e), "message": f"Workflow '{name}' not found."}


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def workflow_status(
    ctx: Context = None,
) -> dict[str, Any]:
    """Get current workflow instance status — node, task, and available branches.

    ## Return Format
    {"success": bool, "workflow": str, "current_node": str, "task": str,
     "branches": list|null, "is_terminal": bool, "message": str}

    ## Examples
    workflow_status()
    """
    sm = get_state_machine()
    instance = sm.status()
    if instance is None:
        return {
            "success": True,
            "active": False,
            "message": "No active workflow. Start one with workflow_start().",
        }
    task = sm.get_current_task()
    branches = sm.get_current_branches()
    is_terminal = branches is None and task is not None

    wf = sm.get_workflow(instance.workflow_name)
    node = wf.nodes.get(instance.current_node) if wf else None
    is_terminal = node.terminal if node else False

    return {
        "success": True,
        "active": True,
        "workflow": instance.workflow_name,
        "current_node": instance.current_node,
        "task": task,
        "branches": branches,
        "is_terminal": is_terminal,
        "history_length": len(instance.history),
        "message": f"At node '{instance.current_node}' in workflow '{instance.workflow_name}'.",
    }


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def workflow_next(
    branch: Annotated[
        int | None,
        Field(description=(
            "Branch index to take (0-based). "
            "Required if current node has branches."
        )),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Complete current node and advance to the next step.

    ## Return Format
    {"success": bool, "next_node": str, "next_task": str, "completed": bool, "message": str}

    ## Examples
    workflow_next()
    workflow_next(branch=0)
    """
    sm = get_state_machine()
    instance = sm.status()
    if instance is None:
        return {"success": False, "message": "No active workflow."}

    prev_node = instance.current_node
    try:
        instance = sm.next(branch)
    except ValueError as e:
        return {"success": False, "error": str(e), "message": "Invalid branch index."}

    if instance is None:
        return {
            "success": True,
            "completed": True,
            "finished_at": prev_node,
            "message": f"Workflow completed at node '{prev_node}'. All steps done.",
        }

    task = sm.get_current_task()
    return {
        "success": True,
        "completed": False,
        "previous_node": prev_node,
        "current_node": instance.current_node,
        "next_task": task,
        "message": f"Advanced to node '{instance.current_node}'. Task: {task}",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def workflow_log(
    ctx: Context = None,
) -> dict[str, Any]:
    """View execution history for the current workflow instance.

    ## Return Format
    {"success": bool, "workflow": str, "history": list[dict],
     "steps_completed": int, "message": str}

    ## Examples
    workflow_log()
    """
    sm = get_state_machine()
    history = sm.log()
    instance = sm.status()
    workflow_name = instance.workflow_name if instance else "none"

    return {
        "success": True,
        "workflow": workflow_name,
        "history": history,
        "steps_completed": len(history),
        "message": f"{len(history)} steps completed in '{workflow_name}'.",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def workflow_list(
    ctx: Context = None,
) -> dict[str, Any]:
    """List all registered workflows.

    ## Return Format
    {"success": bool, "workflows": list[dict], "count": int, "message": str}

    ## Examples
    workflow_list()
    """
    sm = get_state_machine()
    wfs = sm.list_workflows()
    return {
        "success": True,
        "workflows": wfs,
        "count": len(wfs),
        "message": f"{len(wfs)} workflows registered.",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def workflow_active(
    ctx: Context = None,
) -> dict[str, Any]:
    """List all active workflow instances.

    ## Return Format
    {"success": bool, "active": list[dict], "count": int, "message": str}

    ## Examples
    workflow_active()
    """
    sm = get_state_machine()
    active = sm.list_active()
    return {
        "success": True,
        "active": active,
        "count": len(active),
        "message": f"{len(active)} active workflow instance(s).",
    }


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def workflow_reset(
    ctx: Context = None,
) -> dict[str, Any]:
    """Reset the current workflow instance back to its start node.

    ## Return Format
    {"success": bool, "workflow": str, "message": str}

    ## Examples
    workflow_reset()
    """
    sm = get_state_machine()
    instance = sm.reset()
    if instance is None:
        return {"success": False, "message": "No active workflow to reset."}

    task = sm.get_current_task()
    return {
        "success": True,
        "workflow": instance.workflow_name,
        "current_node": instance.current_node,
        "task": task,
        "message": f"Workflow '{instance.workflow_name}' reset to node '{instance.current_node}'.",
    }
