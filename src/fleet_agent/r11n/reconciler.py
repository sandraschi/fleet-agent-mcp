"""The Reconciliation (r11n) Control Loop.

Implements the fundamental Observe -> Diff -> Act -> Verify -> Record cycle.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .invariants import Invariant, InvariantResult
from .lease import (
    DEFAULT_LEASE_TTL,
    LeaseContentionError,
    claim_lease,
    record_blocked,
    release_lease,
)

logger = logging.getLogger("fleet_agent.r11n.reconciler")


@dataclass
class ReconciliationResult:
    """Outcome of a reconciliation cycle."""

    status: str  # "already_satisfied", "reconciled", "contention", "action_failed", "blocked"
    verified: bool
    retries: int = 0
    message: str = ""
    initial_eval: InvariantResult | None = None
    final_eval: InvariantResult | None = None
    details: dict[str, Any] = field(default_factory=dict)


class ReconciliationCycle:
    """Executes an autonomous reconciliation loop on a target directory."""

    def __init__(
        self,
        worker_id: str = "fritz-reconciler",
        lease_ttl_seconds: int = DEFAULT_LEASE_TTL,
        max_retries: int = 3,
    ) -> None:
        self.worker_id = worker_id
        self.lease_ttl_seconds = lease_ttl_seconds
        self.max_retries = max_retries

    def run(
        self,
        target_dir: str | Path,
        invariant: Invariant,
        action_fn: Callable[[Path, InvariantResult], bool],
        task_id: str | None = None,
    ) -> ReconciliationResult:
        """Run a full reconciliation cycle.

        Args:
            target_dir: Repository or target directory.
            invariant: Invariant rule to satisfy.
            action_fn: Callable taking (target_path, eval_result) returning True on success.
            task_id: Optional custom task identifier.

        Returns:
            ReconciliationResult summary.
        """
        p = Path(target_dir).resolve()
        tid = task_id or f"r11n-{invariant.name}"

        # 1. Observe
        initial_eval = invariant.evaluate(p)
        if initial_eval.is_satisfied:
            logger.info("Invariant %s already satisfied on %s", invariant.name, p)
            return ReconciliationResult(
                status="already_satisfied",
                verified=True,
                retries=0,
                message=f"Invariant {invariant.name} is already satisfied.",
                initial_eval=initial_eval,
                final_eval=initial_eval,
            )

        # 2. Claim Lease
        try:
            lease = claim_lease(
                target_dir=p,
                task_id=tid,
                worker_id=self.worker_id,
                ttl_seconds=self.lease_ttl_seconds,
                invariant=invariant.name,
            )
        except LeaseContentionError as e:
            logger.warning("Lease contention on %s: %s", p, e)
            return ReconciliationResult(
                status="contention",
                verified=False,
                message=str(e),
                initial_eval=initial_eval,
            )

        # 3. Remediation Loop
        last_eval = initial_eval
        for attempt in range(1, self.max_retries + 1):
            logger.info(
                "Reconciling %s (attempt %d/%d)...",
                invariant.name,
                attempt,
                self.max_retries,
            )
            try:
                action_ok = action_fn(p, last_eval)
            except Exception as e:
                logger.error("Exception during action_fn on %s: %s", p, e)
                action_ok = False

            if not action_ok:
                logger.warning("Action reported failure on attempt %d", attempt)

            # 4. Verify
            last_eval = invariant.evaluate(p)
            if last_eval.is_satisfied:
                logger.info("Successfully reconciled %s on attempt %d", invariant.name, attempt)
                release_lease(lease)
                return ReconciliationResult(
                    status="reconciled",
                    verified=True,
                    retries=attempt,
                    message=f"Invariant {invariant.name} reconciled after {attempt} attempt(s).",
                    initial_eval=initial_eval,
                    final_eval=last_eval,
                )

        # 5. Circuit Breaker / Escalation
        reason = (
            f"Max retries ({self.max_retries}) exceeded for invariant "
            f"{invariant.name} without convergence."
        )
        record_blocked(
            target_dir=p,
            task_id=tid,
            worker_id=self.worker_id,
            reason=reason,
            details={
                "initial_state": initial_eval.actual_state,
                "final_state": last_eval.actual_state,
            },
        )
        release_lease(lease)

        return ReconciliationResult(
            status="blocked",
            verified=False,
            retries=self.max_retries,
            message=reason,
            initial_eval=initial_eval,
            final_eval=last_eval,
        )
