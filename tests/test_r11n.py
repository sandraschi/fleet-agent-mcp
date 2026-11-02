"""Unit tests for the Stigmergic Swarm & Reconciliation (r11n) module."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from fleet_agent.mcp.tools.r11n import (
    r11n_check,
    r11n_claim,
    r11n_release,
    r11n_status,
)
from fleet_agent.r11n.invariants import (
    CommandInvariant,
    FileExistsInvariant,
)
from fleet_agent.r11n.lease import (
    CLAIM_FILE_NAME,
    R11N_DIR_NAME,
    Lease,
    LeaseContentionError,
    claim_lease,
    is_lease_active,
    read_claim,
    record_blocked,
    release_lease,
)
from fleet_agent.r11n.reconciler import ReconciliationCycle

# ── Lease Tests ─────────────────────────────────────────────────────────────


def test_claim_and_read_lease(tmp_path: Path):
    lease = claim_lease(
        target_dir=tmp_path,
        task_id="test-task-1",
        worker_id="worker-alpha",
        ttl_seconds=60,
        invariant="test_inv",
    )
    assert lease.task_id == "test-task-1"
    assert lease.worker_id == "worker-alpha"
    assert not lease.is_expired
    assert is_lease_active(tmp_path)

    claim_file = tmp_path / R11N_DIR_NAME / CLAIM_FILE_NAME
    assert claim_file.exists()

    read_back = read_claim(tmp_path)
    assert read_back is not None
    assert read_back.task_id == "test-task-1"
    assert read_back.worker_id == "worker-alpha"


def test_lease_contention(tmp_path: Path):
    claim_lease(
        target_dir=tmp_path,
        task_id="task-1",
        worker_id="worker-1",
        ttl_seconds=60,
    )
    # Second worker should fail
    with pytest.raises(LeaseContentionError) as exc_info:
        claim_lease(
            target_dir=tmp_path,
            task_id="task-2",
            worker_id="worker-2",
            ttl_seconds=60,
        )
    assert "Active lease held by worker worker-1" in str(exc_info.value)


def test_lease_reentrancy_renewal(tmp_path: Path):
    claim_lease(
        target_dir=tmp_path,
        task_id="task-1",
        worker_id="worker-1",
        ttl_seconds=10,
    )
    # Same worker & task re-claims: renews
    lease2 = claim_lease(
        target_dir=tmp_path,
        task_id="task-1",
        worker_id="worker-1",
        ttl_seconds=50,
    )
    assert lease2.lease_ttl_seconds == 50


def test_lease_stale_recovery(tmp_path: Path):
    # Create an already-expired lease manually
    r11n_dir = tmp_path / R11N_DIR_NAME
    r11n_dir.mkdir(parents=True, exist_ok=True)
    claim_path = r11n_dir / CLAIM_FILE_NAME
    expired_data = {
        "task_id": "old-task",
        "worker_id": "dead-worker",
        "claimed_at": time.time() - 500,
        "lease_ttl_seconds": 60,
        "invariant": "old_inv",
        "target_dir": str(tmp_path),
        "status": "in_progress",
    }
    claim_path.write_text(json.dumps(expired_data), encoding="utf-8")

    assert not is_lease_active(tmp_path)

    # New worker claims; should reclaim stale lease seamlessly
    new_lease = claim_lease(
        target_dir=tmp_path,
        task_id="new-task",
        worker_id="worker-alive",
        ttl_seconds=100,
    )
    assert new_lease.task_id == "new-task"
    assert new_lease.worker_id == "worker-alive"


def test_release_lease(tmp_path: Path):
    lease = claim_lease(
        target_dir=tmp_path,
        task_id="task-rel",
        worker_id="worker-rel",
        ttl_seconds=60,
    )
    assert (tmp_path / R11N_DIR_NAME / CLAIM_FILE_NAME).exists()

    # Another worker cannot release
    impostor = Lease(
        task_id="task-rel",
        worker_id="worker-impostor",
        claimed_at=time.time(),
        lease_ttl_seconds=60,
        invariant="test",
        target_dir=str(tmp_path),
    )
    assert not release_lease(impostor)
    assert (tmp_path / R11N_DIR_NAME / CLAIM_FILE_NAME).exists()

    # Legitimate worker releases
    assert release_lease(lease)
    assert not (tmp_path / R11N_DIR_NAME / CLAIM_FILE_NAME).exists()


def test_record_blocked(tmp_path: Path):
    blocked_file = record_blocked(
        target_dir=tmp_path,
        task_id="task-blocked",
        worker_id="worker-err",
        reason="Repeated syntax error",
        details={"code": "E999"},
    )
    assert blocked_file.exists()
    data = json.loads(blocked_file.read_text(encoding="utf-8"))
    assert data["task_id"] == "task-blocked"
    assert data["reason"] == "Repeated syntax error"


# ── Invariants Tests ────────────────────────────────────────────────────────


def test_file_exists_invariant(tmp_path: Path):
    inv = FileExistsInvariant("AGENTS.md")
    res1 = inv.evaluate(tmp_path)
    assert not res1.is_satisfied
    assert res1.actual_state == "missing"

    (tmp_path / "AGENTS.md").write_text("# Agents Guide\n", encoding="utf-8")
    res2 = inv.evaluate(tmp_path)
    assert res2.is_satisfied
    assert res2.actual_state == "present"


def test_command_invariant_success(tmp_path: Path):
    inv = CommandInvariant(command="python -c \"print('ok')\"", name="test_cmd")
    res = inv.evaluate(tmp_path)
    assert res.is_satisfied
    assert res.actual_state == "passed"


def test_command_invariant_failure(tmp_path: Path):
    inv = CommandInvariant(command="python -c \"import sys; sys.exit(42)\"", name="test_fail")
    res = inv.evaluate(tmp_path)
    assert not res.is_satisfied
    assert "rc=42" in res.actual_state


# ── Reconciliation Loop Tests ───────────────────────────────────────────────


def test_reconciliation_already_satisfied(tmp_path: Path):
    (tmp_path / "TARGET.txt").write_text("ok", encoding="utf-8")
    inv = FileExistsInvariant("TARGET.txt")
    action_called = False

    def action(p, eval_res):
        nonlocal action_called
        action_called = True
        return True

    cycle = ReconciliationCycle(worker_id="worker-test")
    res = cycle.run(tmp_path, inv, action)

    assert res.status == "already_satisfied"
    assert res.verified is True
    assert not action_called


def test_reconciliation_happy_path(tmp_path: Path):
    target_file = tmp_path / "TARGET.txt"
    inv = FileExistsInvariant("TARGET.txt")

    def action(p, eval_res):
        target_file.write_text("reconciled", encoding="utf-8")
        return True

    cycle = ReconciliationCycle(worker_id="worker-test")
    res = cycle.run(tmp_path, inv, action)

    assert res.status == "reconciled"
    assert res.verified is True
    assert res.retries == 1
    assert target_file.exists()
    assert not is_lease_active(tmp_path)


def test_reconciliation_circuit_breaker_blocked(tmp_path: Path):
    inv = FileExistsInvariant("NON_EXISTENT.txt")

    def failing_action(p, eval_res):
        # Action fails to create the file
        return False

    cycle = ReconciliationCycle(worker_id="worker-test", max_retries=2)
    res = cycle.run(tmp_path, inv, failing_action)

    assert res.status == "blocked"
    assert res.verified is False
    assert res.retries == 2
    assert not is_lease_active(tmp_path)
    assert (tmp_path / R11N_DIR_NAME / "blocked.json").exists()


# ── FastMCP Tools Tests ─────────────────────────────────────────────────────


def test_r11n_mcp_tools(tmp_path: Path):
    # 1. Check initially
    status1 = r11n_status(str(tmp_path))
    assert status1["success"]
    assert not status1["has_lease"]

    # 2. Claim lease
    claim_res = r11n_claim(
        target_dir=str(tmp_path),
        task_id="mcp-task-1",
        worker_id="mcp-worker-1",
        ttl_seconds=60,
    )
    assert claim_res["success"]
    assert claim_res["lease"]["task_id"] == "mcp-task-1"

    # 3. Status now active
    status2 = r11n_status(str(tmp_path))
    assert status2["success"]
    assert status2["has_lease"]
    assert status2["is_active"]

    # 4. Check invariant via tool
    (tmp_path / "AGENTS.md").write_text("# Agents", encoding="utf-8")
    chk = r11n_check(str(tmp_path), "file_exists", "AGENTS.md")
    assert chk["success"]
    assert chk["is_satisfied"]

    # 5. Release lease
    rel_res = r11n_release(str(tmp_path), "mcp-worker-1", "mcp-task-1")
    assert rel_res["success"]

    # 6. Status after release
    status3 = r11n_status(str(tmp_path))
    assert not status3["has_lease"]
