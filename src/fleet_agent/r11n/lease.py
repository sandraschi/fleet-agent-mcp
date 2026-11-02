"""Atomic file-based lease claiming and decay protocol for stigmergic agents."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("fleet_agent.r11n.lease")

R11N_DIR_NAME = ".r11n"
CLAIM_FILE_NAME = "claim.json"
BLOCKED_FILE_NAME = "blocked.json"
DEFAULT_LEASE_TTL = 300  # 5 minutes


class LeaseContentionError(Exception):
    """Raised when an active, unexpired lease is already held by another worker."""


class LeaseExpiredError(Exception):
    """Raised when attempting to renew or release a lease that has already expired."""


@dataclass
class Lease:
    """Represents an active task lease claimed by a worker."""

    task_id: str
    worker_id: str
    claimed_at: float
    lease_ttl_seconds: int
    invariant: str
    target_dir: str
    status: str = "in_progress"

    @property
    def expires_at(self) -> float:
        """Absolute Unix timestamp when lease expires."""
        return self.claimed_at + self.lease_ttl_seconds

    @property
    def is_expired(self) -> bool:
        """True if the lease has timed out."""
        return time.time() >= self.expires_at


def get_r11n_dir(target_dir: str | Path) -> Path:
    """Ensure and return the .r11n directory within target_dir."""
    p = Path(target_dir) / R11N_DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_claim(target_dir: str | Path) -> Lease | None:
    """Read the current claim file if it exists, or None."""
    claim_path = Path(target_dir) / R11N_DIR_NAME / CLAIM_FILE_NAME
    if not claim_path.exists():
        return None
    try:
        data = json.loads(claim_path.read_text(encoding="utf-8"))
        return Lease(
            task_id=data["task_id"],
            worker_id=data["worker_id"],
            claimed_at=float(data["claimed_at"]),
            lease_ttl_seconds=int(data["lease_ttl_seconds"]),
            invariant=data.get("invariant", "unknown"),
            target_dir=str(target_dir),
            status=data.get("status", "in_progress"),
        )
    except Exception as e:
        logger.warning("Failed to parse claim file %s: %s", claim_path, e)
        return None


def is_lease_active(target_dir: str | Path) -> bool:
    """Check if an unexpired lease exists on target_dir."""
    lease = read_claim(target_dir)
    return lease is not None and not lease.is_expired


def claim_lease(
    target_dir: str | Path,
    task_id: str,
    worker_id: str,
    ttl_seconds: int = DEFAULT_LEASE_TTL,
    invariant: str = "default",
    force_stale: bool = True,
) -> Lease:
    """Atomically claim a lease for task_id on target_dir.

    Args:
        target_dir: Path to directory / repository.
        task_id: Unique task descriptor.
        worker_id: Unique worker descriptor.
        ttl_seconds: Lease duration before expiration.
        invariant: Declared invariant being reconciled.
        force_stale: If True, overwrite expired leases automatically.

    Returns:
        Acquired Lease object.

    Raises:
        LeaseContentionError: If an unexpired lease is held by another worker.
    """
    r11n_dir = get_r11n_dir(target_dir)
    claim_path = r11n_dir / CLAIM_FILE_NAME

    now = time.time()
    lease = Lease(
        task_id=task_id,
        worker_id=worker_id,
        claimed_at=now,
        lease_ttl_seconds=ttl_seconds,
        invariant=invariant,
        target_dir=str(Path(target_dir).resolve()),
        status="in_progress",
    )

    lease_data = json.dumps(asdict(lease), indent=2).encode("utf-8")

    # Try atomic creation first
    try:
        fd = os.open(claim_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "wb") as f:
            f.write(lease_data)
        logger.info("Claimed lease for %s by worker %s", task_id, worker_id)
        return lease
    except FileExistsError:
        pass

    # File already exists: inspect current lease
    existing = read_claim(target_dir)
    if existing is not None and not existing.is_expired:
        if existing.worker_id == worker_id and existing.task_id == task_id:
            # Re-entrant claim: renew
            return renew_lease(existing, ttl_seconds)
        rem = existing.expires_at - now
        raise LeaseContentionError(
            f"Active lease held by worker {existing.worker_id} for task {existing.task_id} "
            f"(expires in {rem:.1f}s)"
        )

    if not force_stale and existing is not None and existing.is_expired:
        raise LeaseContentionError(
            f"Stale lease exists for {existing.task_id}; force_stale=False"
        )

    # Stale or corrupted lease: write atomically via temp file replace
    tmp_path = r11n_dir / f"claim.{worker_id}.tmp"
    tmp_path.write_bytes(lease_data)
    try:
        os.replace(tmp_path, claim_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    logger.info("Reclaimed stale lease for %s by worker %s", task_id, worker_id)
    return lease


def renew_lease(lease: Lease, additional_ttl_seconds: int = DEFAULT_LEASE_TTL) -> Lease:
    """Extend the TTL of an active lease."""
    if lease.is_expired:
        raise LeaseExpiredError(f"Cannot renew expired lease for task {lease.task_id}")

    r11n_dir = get_r11n_dir(lease.target_dir)
    claim_path = r11n_dir / CLAIM_FILE_NAME

    lease.claimed_at = time.time()
    lease.lease_ttl_seconds = additional_ttl_seconds

    lease_data = json.dumps(asdict(lease), indent=2).encode("utf-8")
    tmp_path = r11n_dir / f"claim.{lease.worker_id}.tmp"
    tmp_path.write_bytes(lease_data)
    os.replace(tmp_path, claim_path)

    logger.debug("Renewed lease %s for +%ds", lease.task_id, additional_ttl_seconds)
    return lease


def release_lease(lease: Lease) -> bool:
    """Release an active lease by removing the claim file."""
    claim_path = Path(lease.target_dir) / R11N_DIR_NAME / CLAIM_FILE_NAME
    if not claim_path.exists():
        return True

    existing = read_claim(lease.target_dir)
    # Only releasing worker can remove its own lease (unless expired)
    if existing and existing.worker_id == lease.worker_id:
        try:
            claim_path.unlink()
            logger.info("Released lease %s for worker %s", lease.task_id, lease.worker_id)
            return True
        except Exception as e:
            logger.warning("Error releasing lease: %s", e)
            return False
    return False


def record_blocked(
    target_dir: str | Path,
    task_id: str,
    worker_id: str,
    reason: str,
    details: dict[str, Any] | None = None,
) -> Path:
    """Drop a blocked pheromone marker to halt spinning and escalate to human."""
    r11n_dir = get_r11n_dir(target_dir)
    blocked_path = r11n_dir / BLOCKED_FILE_NAME

    payload = {
        "task_id": task_id,
        "worker_id": worker_id,
        "blocked_at": time.time(),
        "reason": reason,
        "details": details or {},
    }
    blocked_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.error("Recorded BLOCKED trace in %s: %s", target_dir, reason)
    return blocked_path
