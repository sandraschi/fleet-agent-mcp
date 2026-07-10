"""Mechanical Gate Engine — zero-LLM gate enforcement for fleet-agent-mcp.

Ported concepts from OPC (One Person Company) by iamtouchskyer:
  https://github.com/iamtouchskyer/opc

Core axiom: "the agent that builds never evaluates." Every critical output
MUST have an independent verification path, and verdicts are computed by
CODE, not by asking an LLM whether a finding is "important enough."

Usage:
    from fleet_agent.harness.gate_engine import synthesize, lint_criteria
    verdict = synthesize(evals)
    if verdict.verdict == "FAIL":
        ...
"""

from fleet_agent.harness.gate_engine import (
    EvalReport,
    Finding,
    GateVerdict,
    IndependenceResult,
    OscillationResult,
    TierCoverageResult,
    check_independence,
    check_tier_coverage,
    detect_oscillation,
    lint_criteria,
    synthesize,
)

__all__ = [
    "Finding",
    "EvalReport",
    "GateVerdict",
    "IndependenceResult",
    "OscillationResult",
    "TierCoverageResult",
    "synthesize",
    "check_independence",
    "detect_oscillation",
    "lint_criteria",
    "check_tier_coverage",
]
