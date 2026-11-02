"""FastMCP tools for the Stigmergic Swarm & Reconciliation (r11n) engine."""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from ...r11n.invariants import (
    CommandInvariant,
    FileExistsInvariant,
    PortHealthInvariant,
    TestInvariant,
)
from ...r11n.lease import (
    LeaseContentionError,
    claim_lease,
    read_claim,
    release_lease,
)
from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.r11n")


@mcp.tool
def r11n_claim(
    target_dir: Annotated[str, Field(description="Target directory or repo path to claim")],
    task_id: Annotated[str, Field(description="Unique task descriptor")],
    worker_id: Annotated[str, Field(description="Worker ID")] = "fritz-worker",
    ttl_seconds: Annotated[int, Field(description="Lease duration in seconds")] = 300,
    invariant: Annotated[str, Field(description="Invariant rule name")] = "default",
) -> dict[str, Any]:
    """Claim an atomic stigmergic lease on a target repository or directory."""
    try:
        lease = claim_lease(
            target_dir=target_dir,
            task_id=task_id,
            worker_id=worker_id,
            ttl_seconds=ttl_seconds,
            invariant=invariant,
        )
        return {
            "success": True,
            "message": f"Claimed lease for task '{task_id}' by worker '{worker_id}'",
            "lease": asdict(lease),
        }
    except LeaseContentionError as e:
        return {
            "success": False,
            "error": "lease_contention",
            "message": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "error": "claim_failed",
            "message": str(e),
        }


@mcp.tool
def r11n_status(
    target_dir: Annotated[str, Field(description="Target directory or repo path to inspect")],
) -> dict[str, Any]:
    """Check the active stigmergic claim and lease status for a target directory."""
    lease = read_claim(target_dir)
    if lease is None:
        return {
            "success": True,
            "has_lease": False,
            "message": "No claim marker present.",
        }

    return {
        "success": True,
        "has_lease": True,
        "is_active": not lease.is_expired,
        "lease": asdict(lease),
    }


@mcp.tool
def r11n_release(
    target_dir: Annotated[str, Field(description="Target directory or repo path")],
    worker_id: Annotated[str, Field(description="Claiming worker ID releasing the lease")],
    task_id: Annotated[str, Field(description="Task identifier of lease")],
) -> dict[str, Any]:
    """Release an active stigmergic lease on a target repository."""
    lease = read_claim(target_dir)
    if lease is None:
        return {"success": True, "message": "No active lease to release."}

    if lease.worker_id != worker_id:
        return {
            "success": False,
            "error": "unauthorized",
            "message": f"Cannot release lease held by '{lease.worker_id}' as worker '{worker_id}'",
        }

    ok = release_lease(lease)
    return {
        "success": ok,
        "message": "Lease released successfully." if ok else "Failed to delete claim file.",
    }


@mcp.tool
def r11n_check(
    target_dir: Annotated[str, Field(description="Target directory or repo path")],
    invariant_type: Annotated[str, Field(description="Type: test, file_exists, port, command")],
    argument: Annotated[str, Field(description="Command, relative file path, or port")] = "",
) -> dict[str, Any]:
    """Evaluate a declarative invariant against a target directory."""
    p = Path(target_dir).resolve()
    inv_type = invariant_type.lower().strip()

    if inv_type == "test":
        inv = TestInvariant(command=argument or "uv run pytest tests/ -q")
    elif inv_type == "file_exists":
        inv = FileExistsInvariant(relative_path=argument)
    elif inv_type == "port":
        try:
            port = int(argument)
            inv = PortHealthInvariant(port=port)
        except ValueError:
            return {"success": False, "error": f"Invalid port: {argument}"}
    elif inv_type == "command":
        inv = CommandInvariant(command=argument)
    else:
        return {
            "success": False,
            "error": (
                f"Unknown invariant type '{invariant_type}'. Choose from: "
                "test, file_exists, port, command."
            ),
        }

    res = inv.evaluate(p)
    return {
        "success": True,
        "invariant": inv.name,
        "is_satisfied": res.is_satisfied,
        "actual_state": res.actual_state,
        "severity": res.severity,
        "details": res.details,
    }
