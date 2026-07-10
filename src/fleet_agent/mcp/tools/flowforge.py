"""State machine workflow tools — YAML/JSON-defined, gate-enforced step execution.

Inspired by kagura-agent/flowforge and OPC (One Person Company):
- YAML and OPC-style JSON flow templates
- Node types (build, review, gate, execute, discussion)
- Mechanical gate verification (verdict-powered routing)
- Criteria lint pre-flight for acceptance criteria
"""

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from ...config import settings
from ...engine.state_machine import get_state_machine
from ...engine.workflow_loader import discover_workflows
from ..registry import mcp


@mcp.tool(annotations={"readOnly": False}, version="0.2.0")
async def workflow_define(
    file_path: Annotated[str, Field(description="Path to workflow YAML or JSON file.")],
    ctx: Context = None,
) -> dict[str, Any]:
    """Register a workflow from a YAML or JSON file.

    Supports:
    - YAML workflows (.yaml, .yml) — linear/branch/terminal nodes
    - OPC-style JSON flow templates (.json) — with node types,
      branches_map (PASS/FAIL/ITERATE), context_schema, soft_evidence

    ## Return Format
    {"success": bool, "workflow": {"name": str, "nodes": int, "start": str}, "message": str}

    ## Examples
    workflow_define("workflows/daily.yaml")
    workflow_define("workflows/gate-build-verify.json")
    """
    sm = get_state_machine()
    try:
        import os.path
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".json":
            wf = sm.register_workflow_from_json(file_path)
        else:
            wf = sm.register_workflow(file_path)
        return {
            "success": True,
            "workflow": {
                "name": wf.name,
                "description": wf.description,
                "node_count": len(wf.nodes),
                "start": wf.start,
                "has_gate_nodes": any(
                    n.node_type == "gate" for n in wf.nodes.values()
                ),
            },
            "message": (
                f"Workflow '{wf.name}' registered with {len(wf.nodes)} nodes"
                f" (from {ext or 'yaml'})."
            ),
        }
    except FileNotFoundError as e:
        return {"success": False, "error": str(e), "message": "Workflow file not found."}
    except Exception as e:
        return {"success": False, "error": str(e), "message": f"Failed to register workflow: {e}"}


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


@mcp.tool(annotations={"readOnly": False}, version="0.2.0")
async def workflow_start(
    name: Annotated[str, Field(description="Name of the registered workflow to start.")],
    criteria_text: Annotated[
        str | None,
        Field(description=(
            "Optional acceptance criteria markdown for pre-flight linting. "
            "If provided and lint fails, start is blocked."
        )),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Start a new workflow instance.

    Optionally validates acceptance criteria before starting (criteria lint gate).
    If criteria_text fails lint, the workflow is not started.

    ## Return Format
    {"success": bool, "instance": dict, "first_task": str, "criteria_lint": dict|null, "message": str}

    ## Examples
    workflow_start("daily")
    workflow_start("build-verify",
        criteria_text="Feature: user login\\n- Email/password validation\\n- Session persists across refresh\\n## Return Format\\n{\\"success\\": bool}")
    """
    sm = get_state_machine()

    # Pre-flight criteria lint
    lint_result = None
    if criteria_text:
        from ...harness.gate_engine import lint_criteria as _lint
        lint_result = _lint(criteria_text)
        if not lint_result.passed:
            return {
                "success": False,
                "criteria_lint": {
                    "passed": False,
                    "errors": lint_result.errors,
                    "warnings": lint_result.warnings,
                    "criteria_count": lint_result.criteria_count,
                },
                "message": f"Criteria lint FAILED ({len(lint_result.errors)} error(s)). "
                           f"Fix criteria before starting workflow.",
            }

    try:
        instance = sm.start(name)
        task = sm.get_current_task()
        node_type = sm.get_current_node_type()

        result = {
            "success": True,
            "instance": instance.to_dict(),
            "first_task": task,
            "node_type": node_type,
            "message": (
                f"Workflow '{name}' started at node '{instance.current_node}' ({node_type or 'build'})."
                f" Current task: {task}"
            ),
        }
        if lint_result:
            result["criteria_lint"] = {
                "passed": True,
                "criteria_count": lint_result.criteria_count,
                "warnings": lint_result.warnings,
            }
        return result
    except ValueError as e:
        return {"success": False, "error": str(e), "message": f"Workflow '{name}' not found."}


@mcp.tool(annotations={"readOnly": True}, version="0.2.0")
async def workflow_status(
    ctx: Context = None,
) -> dict[str, Any]:
    """Get current workflow instance status — node, type, task, branches, gate state.

    ## Return Format
    {"success": bool, "active": bool, "workflow": str, "current_node": str,
     "node_type": str|null, "task": str, "branches": list|null,
     "last_verdict": str|null, "gate_count": int, "is_terminal": bool, "message": str}

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
    node_type = sm.get_current_node_type()
    last_verdict = sm.get_last_verdict()
    gate_results = sm.get_gate_results()

    wf = sm.get_workflow(instance.workflow_name)
    node = wf.nodes.get(instance.current_node) if wf else None
    is_terminal = node.terminal if node else False
    branches_map = node.branches_map if node and hasattr(node, 'branches_map') else {}

    return {
        "success": True,
        "active": True,
        "workflow": instance.workflow_name,
        "current_node": instance.current_node,
        "node_type": node_type,
        "task": task,
        "branches": branches,
        "branches_map": branches_map,
        "is_terminal": is_terminal,
        "last_verdict": last_verdict,
        "gate_count": len(gate_results),
        "gate_results": gate_results,
        "history_length": len(instance.history),
        "requires_evals": node_type in ("review", "gate") if node_type else False,
        "message": (
            f"At node '{instance.current_node}' ({node_type or 'build'})"
            f" in workflow '{instance.workflow_name}'."
            f"{' Last gate: ' + last_verdict if last_verdict else ''}"
        ),
    }


@mcp.tool(annotations={"readOnly": False}, version="0.2.0")
async def workflow_next(
    branch: Annotated[
        int | None,
        Field(description=(
            "Branch index to take (0-based) for branch-based nodes. "
            "Required if current node has branches and no verdict is given."
        )),
    ] = None,
    verdict: Annotated[
        str | None,
        Field(description=(
            "Gate verdict for review/gate nodes: 'PASS' | 'FAIL' | 'ITERATE' | 'BLOCKED'. "
            "When provided, routes via the node's branches_map (PASS→next, FAIL→loopback)."
        )),
    ] = None,
    evaluations: Annotated[
        list[dict[str, Any]] | None,
        Field(description=(
            "Eval artifacts from reviewer agents. Stored in workflow history for "
            "gate auditing. Each dict: {role, findings: [{severity, message, ...}]}."
        )),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Complete current node and advance to the next step.

    Supports gate-aware transitions: pass a verdict (PASS/FAIL/ITERATE) and
    optional evaluations for review/gate nodes. The state machine routes based
    on the node's branches_map (verdict → next).

    ## Return Format
    {"success": bool, "previous_node": str, "node_type": str|null,
     "current_node": str, "next_task": str, "completed": bool,
     "verdict_applied": str|null, "message": str}

    ## Examples
    workflow_next()
    workflow_next(branch=0)
    workflow_next(verdict="PASS", evaluations=[{"role": "security", "findings": [...]}])
    workflow_next(verdict="FAIL", evaluations=[{"role": "reviewer", "findings": [...]}])
    """
    sm = get_state_machine()
    instance = sm.status()
    if instance is None:
        return {"success": False, "message": "No active workflow."}

    prev_node = instance.current_node
    node_type = sm.get_current_node_type()

    try:
        instance = sm.next(
            branch=branch,
            verdict=verdict,
            evals=evaluations,
        )
    except (ValueError, Exception) as e:
        return {"success": False, "error": str(e), "message": f"Failed to advance: {e}"}

    if instance is None:
        return {
            "success": True,
            "completed": True,
            "finished_at": prev_node,
            "node_type": node_type,
            "verdict_applied": verdict,
            "message": f"Workflow completed at node '{prev_node}'. All steps done.",
        }

    task = sm.get_current_task()
    return {
        "success": True,
        "completed": False,
        "previous_node": prev_node,
        "node_type": node_type,
        "current_node": instance.current_node,
        "next_task": task,
        "verdict_applied": verdict,
        "message": (
            f"Advanced to '{instance.current_node}'."
            f"{' Verdict: ' + verdict if verdict else ''}"
        ),
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


@mcp.tool(annotations={"readOnly": True}, version="0.2.0")
async def workflow_nodes(
    name: Annotated[str, Field(description="Name of the registered workflow to inspect.")],
    ctx: Context = None,
) -> dict[str, Any]:
    """List all nodes in a registered workflow with their types and connections.

    Shows the full digraph: node names, types (build/review/gate/execute/discussion),
    next targets, branch conditions, and terminal flag.

    ## Return Format
    {"success": bool, "workflow": str, "nodes": list, "has_gate_nodes": bool, "message": str}

    ## Examples
    workflow_nodes("daily")
    workflow_nodes("build-verify")
    """
    sm = get_state_machine()
    wf = sm.get_workflow(name)
    if wf is None:
        return {"success": False, "message": f"Workflow '{name}' not found."}

    nodes_list = []
    for node_name, node in wf.nodes.items():
        entry: dict[str, Any] = {
            "name": node_name,
            "task": node.task,
            "node_type": node.node_type or "build",
            "terminal": node.terminal,
        }
        if node.next_node:
            entry["next"] = node.next_node
        if node.branches:
            entry["branches"] = [
                {"condition": b.condition, "next": b.next} for b in node.branches
            ]
        if node.branches_map:
            entry["branches_map"] = node.branches_map
        nodes_list.append(entry)

    has_gate = any(n.node_type == "gate" for n in wf.nodes.values())
    return {
        "success": True,
        "workflow": name,
        "description": wf.description,
        "node_count": len(nodes_list),
        "nodes": nodes_list,
        "has_gate_nodes": has_gate,
        "start_node": wf.start,
        "message": f"Workflow '{name}': {len(nodes_list)} nodes, {len(nodes_list)} start='{wf.start}'.",
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
