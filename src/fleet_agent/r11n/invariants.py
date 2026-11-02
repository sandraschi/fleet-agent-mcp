"""Declarative invariant evaluators for reconciliation (r11n)."""

from __future__ import annotations

import logging
import subprocess
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("fleet_agent.r11n.invariants")


@dataclass
class InvariantResult:
    """The result of an invariant evaluation."""

    is_satisfied: bool
    actual_state: str
    details: dict[str, Any] = field(default_factory=dict)
    severity: str = "ok"  # "ok", "warning", "critical"


class Invariant(ABC):
    """Abstract base class for all fleet invariants."""

    name: str = "base_invariant"

    @abstractmethod
    def evaluate(self, target_dir: Path) -> InvariantResult:
        """Evaluate the invariant against the target directory."""


class CommandInvariant(Invariant):
    """Evaluates an invariant by running a shell command and inspecting the return code."""

    def __init__(
        self,
        command: str,
        name: str = "command_check",
        timeout_seconds: int = 60,
    ) -> None:
        self.command = command
        self.name = name
        self.timeout_seconds = timeout_seconds

    def evaluate(self, target_dir: Path) -> InvariantResult:
        try:
            res = subprocess.run(
                self.command,
                cwd=str(target_dir),
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            passed = res.returncode == 0
            return InvariantResult(
                is_satisfied=passed,
                actual_state="passed" if passed else f"failed (rc={res.returncode})",
                details={
                    "command": self.command,
                    "returncode": res.returncode,
                    "stdout": res.stdout[-2000:] if res.stdout else "",
                    "stderr": res.stderr[-2000:] if res.stderr else "",
                },
                severity="ok" if passed else "critical",
            )
        except subprocess.TimeoutExpired as e:
            return InvariantResult(
                is_satisfied=False,
                actual_state=f"timeout after {self.timeout_seconds}s",
                details={"command": self.command, "error": str(e)},
                severity="critical",
            )
        except Exception as e:
            return InvariantResult(
                is_satisfied=False,
                actual_state=f"error: {e}",
                details={"command": self.command, "error": str(e)},
                severity="critical",
            )


class TestInvariant(CommandInvariant):
    """Checks that the test suite passes."""

    __test__ = False  # Inform pytest this is not a test suite class

    def __init__(
        self,
        command: str = "uv run pytest tests/ -q",
        timeout_seconds: int = 120,
    ) -> None:
        super().__init__(
            command=command,
            name="test_suite_passing",
            timeout_seconds=timeout_seconds,
        )


class LintInvariant(CommandInvariant):
    """Checks that ruff linting passes."""

    def __init__(
        self,
        command: str = "uv run ruff check .",
        timeout_seconds: int = 60,
    ) -> None:
        super().__init__(
            command=command,
            name="lint_passing",
            timeout_seconds=timeout_seconds,
        )


class FileExistsInvariant(Invariant):
    """Checks that a mandatory file exists in the target directory."""

    def __init__(self, relative_path: str) -> None:
        self.relative_path = relative_path
        self.name = f"file_exists_{relative_path.replace('/', '_')}"

    def evaluate(self, target_dir: Path) -> InvariantResult:
        target_file = target_dir / self.relative_path
        exists = target_file.is_file()
        return InvariantResult(
            is_satisfied=exists,
            actual_state="present" if exists else "missing",
            details={"file": str(target_file)},
            severity="ok" if exists else "warning",
        )


class PortHealthInvariant(Invariant):
    """Checks that an HTTP service is responding on the specified port."""

    def __init__(
        self,
        port: int,
        endpoint: str = "/api/health",
        timeout_seconds: int = 3,
    ) -> None:
        self.port = port
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.name = f"port_health_{port}"

    def evaluate(self, target_dir: Path) -> InvariantResult:
        url = f"http://127.0.0.1:{self.port}{self.endpoint}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Fritz-r11n-Reconciler"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                status = resp.status
                is_ok = 200 <= status < 300
                return InvariantResult(
                    is_satisfied=is_ok,
                    actual_state=f"http_{status}",
                    details={"url": url, "status_code": status},
                    severity="ok" if is_ok else "critical",
                )
        except Exception as e:
            return InvariantResult(
                is_satisfied=False,
                actual_state=f"unreachable ({e})",
                details={"url": url, "error": str(e)},
                severity="critical",
            )
