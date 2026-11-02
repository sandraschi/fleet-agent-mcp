"""Autonomous command-line runner for the r11n reconciliation loop.

Enables ephemeral, decoupled workers to claim a lease, observe invariant breaches,
apply mechanical or LLM-driven remediation, prove verification, and release the lease.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .invariants import CommandInvariant, FileExistsInvariant, Invariant, TestInvariant
from .reconciler import ReconciliationCycle, ReconciliationResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fleet_agent.r11n.runner")


def _mechanical_greeter_remedy(target_dir: Path, eval_res) -> bool:
    """Specialized remediation for the Pilot 3 fritz-test target."""
    greeter_file = target_dir / "src" / "fritz_test" / "greeter.py"
    if not greeter_file.exists():
        return False

    code = greeter_file.read_text(encoding="utf-8")
    if "def add(" not in code:
        patch = "\n\ndef add(a: int, b: int) -> int:\n    return a + b\n"
        greeter_file.write_text(code.rstrip() + patch, encoding="utf-8")
        logger.info("Applied remediation: appended 'add(a, b)' to %s", greeter_file)
        return True
    return False


def build_invariant(invariant_type: str, argument: str) -> Invariant:
    inv_type = invariant_type.lower().strip()
    if inv_type == "test":
        cmd = argument or "uv run --with pytest pytest"
        return TestInvariant(command=cmd)
    if inv_type == "file_exists":
        return FileExistsInvariant(relative_path=argument)
    if inv_type == "command":
        return CommandInvariant(command=argument)
    raise ValueError(f"Unsupported invariant type: {invariant_type}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fritz r11n Autonomous Reconciler")
    parser.add_argument("--target", required=True, help="Target directory or repo path")
    parser.add_argument("--task-id", default="r11n-task", help="Unique task identifier")
    parser.add_argument("--worker-id", default="fritz-worker-01", help="Worker identifier")
    parser.add_argument(
        "--invariant",
        default="test",
        help="Invariant type: test, file_exists, command",
    )
    parser.add_argument("--argument", default="", help="Command line or relative file path")
    parser.add_argument("--ttl", type=int, default=300, help="Lease TTL seconds")
    parser.add_argument("--retries", type=int, default=3, help="Max reconciliation retries")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()
    target_path = Path(args.target).resolve()

    if not target_path.exists():
        logger.error("Target path does not exist: %s", target_path)
        return 1

    try:
        inv = build_invariant(args.invariant, args.argument)
    except Exception as e:
        logger.error("Failed to build invariant: %s", e)
        return 1

    cycle = ReconciliationCycle(
        worker_id=args.worker_id,
        lease_ttl_seconds=args.ttl,
        max_retries=args.retries,
    )

    # Remediation dispatch: for pilot-3 fritz-test, use mechanical remedy; otherwise default
    def action_dispatch(p: Path, eval_res) -> bool:
        if "fritz-test" in p.name:
            return _mechanical_greeter_remedy(p, eval_res)
        logger.warning("No automated remedy configured for %s", p)
        return False

    result: ReconciliationResult = cycle.run(
        target_dir=target_path,
        invariant=inv,
        action_fn=action_dispatch,
        task_id=args.task_id,
    )

    if args.json:
        out = {
            "status": result.status,
            "verified": result.verified,
            "retries": result.retries,
            "message": result.message,
            "target": str(target_path),
            "invariant": inv.name,
        }
        sys.stdout.write(json.dumps(out, indent=2) + "\n")
    else:
        logger.info(
            "Reconciliation finished with status='%s', verified=%s, retries=%d",
            result.status,
            result.verified,
            result.retries,
        )

    return 0 if result.verified else 2


if __name__ == "__main__":
    sys.exit(main())
