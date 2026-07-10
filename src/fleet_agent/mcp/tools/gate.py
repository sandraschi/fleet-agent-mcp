"""Mechanical gate tools — zero-LLM evaluation for workflow nodes.

Exposes the harness/gate_engine.py functions as MCP tools that any fleet
orchestrator can call: gate_evaluate, gate_verify, criteria_lint.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from ...harness.gate_engine import (
    EvalReport,
    Finding,
    check_independence,
    detect_oscillation,
    lint_criteria,
    synthesize,
)
from ..registry import mcp

# ── Helpers ──────────────────────────────────────────────────────────────────


def _finding_from_dict(d: dict[str, Any]) -> Finding:
    return Finding(
        severity=d.get("severity", "info"),
        message=d.get("message", ""),
        file_ref=d.get("file_ref"),
        line=d.get("line"),
        code=d.get("code"),
    )


# ── Gate tools ───────────────────────────────────────────────────────────────


@mcp.tool(annotations={"readOnly": True}, version="0.2.0")
async def gate_evaluate(
    evaluations: Annotated[
        list[dict[str, Any]],
        Field(description=(
            "List of evaluation reports. Each dict:\n"
            "  role (str): Reviewer role name (e.g. 'security', 'frontend').\n"
            "  findings (list[dict]): Structured findings with:\n"
            "    severity (str): 'critical'🔴 | 'warning'🟡 | 'suggestion'🔵 | 'blocked'⛔ | 'info'ℹ️\n"
            "    message (str): Description.\n"
            "    file_ref (str, optional): File path reference.\n"
            "    line (int, optional): Line number.\n"
            "    code (str, optional): Rule/category code.\n"
            "  summary (str, optional): One-line summary.\n"
            "  raw_text (str, optional): Markdown text for emoji-severity parsing."
        )),
    ],
) -> dict[str, Any]:
    """Compute a mechanical gate verdict from evaluation reports.

    No LLM involved — verdict is computed by code from severity levels:
      - Any 🔴 critical → FAIL
      - Any 🟡 warning → ITERATE
      - All clear → PASS
      - Any ⛔ blocked → BLOCKED

    ## Return Format
    {"success": bool, "verdict": str, "summary": str,
     "findings_breakdown": dict, "detail": str, "message": str}

    ## Examples
    gate_evaluate(evaluations=[
        {"role": "security", "findings": [
            {"severity": "warning", "message": "Missing input validation", "file_ref": "auth.py", "line": 42}
        ]}
    ])
    gate_evaluate(evaluations=[
        {"role": "frontend", "raw_text": "🔴 Critical: XSS in search form\\n🟡 Warning: ARIA labels missing"}
    ])
    """
    evals: list[EvalReport] = []
    for e in evaluations:
        findings = [_finding_from_dict(f) for f in e.get("findings", [])]
        evals.append(EvalReport(
            role=e.get("role", "unknown"),
            findings=findings,
            summary=e.get("summary", ""),
            raw_text=e.get("raw_text", ""),
        ))

    result = synthesize(evals)
    return {
        "success": True,
        "verdict": result.verdict,
        "summary": result.summary,
        "findings_breakdown": result.findings_breakdown,
        "failures": [
            {"severity": f.severity, "message": f.message,
             "file_ref": f.file_ref, "line": f.line, "code": f.code}
            for f in result.failures
        ],
        "warnings": [
            {"severity": f.severity, "message": f.message,
             "file_ref": f.file_ref, "line": f.line, "code": f.code}
            for f in result.warnings
        ],
        "detail": result.detail,
        "message": f"{result.verdict}: {result.summary}",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.2.0")
async def gate_verify(
    evaluations: Annotated[
        list[dict[str, Any]],
        Field(description="Same format as gate_evaluate evaluations."),
    ],
    previous_verdict: Annotated[
        str | None,
        Field(description="Verdict from the previous gate round for oscillation detection."),
    ] = None,
    tier: Annotated[
        str | None,
        Field(description="Quality tier: 'functional', 'polished', or 'delightful'."),
    ] = None,
    artifact_types: Annotated[
        list[str] | None,
        Field(description="Artifact types produced (e.g. ['screenshot', 'test-result'])."),
    ] = None,
) -> dict[str, Any]:
    """Full gate verification: independence + synthesize + oscillation + tier.

    Runs the complete mechanical gate pipeline in one call:
      1. Review independence check (≥2 evals, no identical content)
      2. Synthesize verdict from severities
      3. Oscillation detection against previous round
      4. Tier coverage check (polished needs screenshots, etc.)

    ## Return Format
    {"success": bool, "verdict": str, "independence": dict,
     "oscillation": dict, "tier_coverage": dict, "message": str}

    ## Examples
    gate_verify(evaluations=[...])
    gate_verify(evaluations=[...], previous_verdict="ITERATE",
                tier="polished", artifact_types=["screenshot", "test-result"])
    """
    evals: list[EvalReport] = []
    for e in evaluations:
        findings = [_finding_from_dict(f) for f in e.get("findings", [])]
        evals.append(EvalReport(
            role=e.get("role", "unknown"),
            findings=findings,
            summary=e.get("summary", ""),
            raw_text=e.get("raw_text", ""),
        ))

    # 1. Independence
    ind_result = check_independence(evals)

    # 2. Synthesize
    syn_result = synthesize(evals, tier=tier)

    # 3. Oscillation (simulate previous verdict from string)
    from ...harness.gate_engine import GateVerdict
    prev = None
    if previous_verdict and previous_verdict in ("PASS", "FAIL", "ITERATE", "BLOCKED"):
        prev = GateVerdict(verdict=previous_verdict, summary="")
    osc_result = detect_oscillation(syn_result, prev)

    # 4. Tier coverage
    from ...harness.gate_engine import check_tier_coverage as _tier_check
    tier_result = _tier_check(artifact_types or [], tier or "functional")

    return {
        "success": True,
        "verdict": syn_result.verdict,
        "independence": {
            "passed": ind_result.passed,
            "eval_count": ind_result.eval_count,
            "message": ind_result.message,
            "overlap_warning": ind_result.overlap_warning,
        },
        "results": {
            "findings_breakdown": syn_result.findings_breakdown,
            "failures": [f.message for f in syn_result.failures],
            "warnings": [f.message for f in syn_result.warnings],
        },
        "oscillation": {
            "oscillating": osc_result.oscillating,
            "pattern": osc_result.pattern,
            "message": osc_result.message,
        },
        "tier_coverage": {
            "passed": tier_result.passed,
            "tier": tier_result.tier,
            "covered": tier_result.covered,
            "missing": tier_result.missing,
            "message": tier_result.message,
        },
        "message": f"Gate: {syn_result.verdict} | Independence: {'PASS' if ind_result.passed else 'FAIL'} | "
        f"Oscillation: {'WARN' if osc_result.oscillating else 'OK'} | "
        f"Tier: {'PASS' if tier_result.passed else 'FAIL'}",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.2.0")
async def criteria_lint(
    criteria_text: Annotated[
        str,
        Field(description="Acceptance criteria markdown text to validate."),
    ],
    strict: Annotated[
        bool,
        Field(description="If true, warnings also block pipeline start (default false)."),
    ] = False,
) -> dict[str, Any]:
    """Mechanically validate acceptance criteria before pipeline starts.

    Checks:
      - Required sections present (Return Format, Examples)
      - No deferral language ('deferred', 'next sprint', etc.)
      - At least one bullet-point criterion
      - No empty bullet points

    ## Return Format
    {"success": bool, "passed": bool, "errors": list[str],
     "warnings": list[str], "criteria_count": int, "message": str}

    ## Examples
    criteria_lint(criteria_text="## Acceptance Criteria\\n- Search returns results in 2s\\n## Return Format\\n...")
    """
    result = lint_criteria(criteria_text)

    if strict and result.warnings and result.passed:
        result.passed = False
        result.errors.extend(result.warnings)

    return {
        "success": True,
        "passed": result.passed,
        "errors": result.errors,
        "warnings": result.warnings,
        "criteria_count": result.criteria_count,
        "message": result.message,
    }
