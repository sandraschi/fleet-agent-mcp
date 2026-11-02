"""Stigmergic Swarm & Reconciliation (r11n) module for Fritz.

Provides decentralized, environment-mediated coordination primitives:
- File-based blackboard and atomic lease claims (.r11n/claim.json).
- Declarative Invariant evaluation (Observe -> Diff -> Act).
- Anti-spin circuit breaking and pheromone decay/evaporation.
"""

from .invariants import (
    CommandInvariant,
    FileExistsInvariant,
    Invariant,
    InvariantResult,
    LintInvariant,
    PortHealthInvariant,
    TestInvariant,
)
from .lease import (
    Lease,
    LeaseContentionError,
    LeaseExpiredError,
    claim_lease,
    is_lease_active,
    record_blocked,
    release_lease,
    renew_lease,
)
from .reconciler import ReconciliationCycle, ReconciliationResult

__all__ = [
    "Lease",
    "LeaseContentionError",
    "LeaseExpiredError",
    "claim_lease",
    "renew_lease",
    "release_lease",
    "record_blocked",
    "is_lease_active",
    "Invariant",
    "InvariantResult",
    "TestInvariant",
    "LintInvariant",
    "FileExistsInvariant",
    "PortHealthInvariant",
    "CommandInvariant",
    "ReconciliationCycle",
    "ReconciliationResult",
]
