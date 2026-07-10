"""Mechanical gate engine — deterministic verdicts from structured evaluations.

Inspired by OPC's `opc-harness synthesize`: reads eval artifacts, counts
severities, and computes a verdict WITHOUT an LLM. The gate never asks an
LLM "is this finding important enough" — it applies mechanical rules:

  Any 🔴 (critical)   → FAIL
  Any 🟡 (warning)    → ITERATE
  All 🔵/LGTM         → PASS
  Any BLOCKED         → BLOCKED

The agent that builds must NEVER be the agent that evaluates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

# ── Data types ──────────────────────────────────────────────────────────────

Severity = Literal["critical", "warning", "suggestion", "blocked", "info"]


@dataclass
class Finding:
    """A single finding from an evaluation.

    Fields:
        severity: critical=🔴, warning=🟡, suggestion=🔵, blocked=⛔, info=ℹ️
        message: Human-readable description of the finding.
        file_ref: Optional file path the finding relates to.
        line: Optional line number.
        code: Optional rule/category code (e.g. "S701", "a11y-missing-label").
    """

    severity: Severity
    message: str
    file_ref: str | None = None
    line: int | None = None
    code: str | None = None


SEVERITY_EMOJI: dict[Severity, str] = {
    "critical": "🔴",
    "warning": "🟡",
    "suggestion": "🔵",
    "blocked": "⛔",
    "info": "ℹ️",
}


@dataclass
class EvalReport:
    """Output from a single evaluator agent (one role's review).

    Fields:
        role: Which agent produced this (e.g. "frontend", "security").
        findings: Structured findings list.
        summary: One-line summary of the evaluation.
        raw_text: Optional full markdown for parsing-based extract.
    """

    role: str
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    raw_text: str = ""


@dataclass
class GateVerdict:
    """The mechanical verdict computed from one or more EvalReports.

    Fields:
        verdict: PASS | ITERATE | FAIL | BLOCKED
        summary: Short description of why this verdict was reached.
        findings_breakdown: Severity → count mapping.
        failures: List of critical findings that caused FAIL.
        warnings: List of warning findings that caused ITERATE.
        detail: Full narrative report for human consumption.
    """

    verdict: Literal["PASS", "ITERATE", "FAIL", "BLOCKED"]
    summary: str
    findings_breakdown: dict[str, int] = field(default_factory=dict)
    failures: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)
    detail: str = ""


@dataclass
class IndependenceResult:
    """Result of review independence check.

    At least 2 independent evaluations required. Identical content rejected.
    """

    passed: bool
    eval_count: int
    message: str
    overlap_warning: str | None = None


@dataclass
class OscillationResult:
    """Result of comparing two consecutive gate verdicts.

    Detects A→B→A feedback loops where iterating is not converging.
    """

    oscillating: bool
    pattern: list[str] | None = None
    message: str = ""


@dataclass
class TierCoverageResult:
    """Result of quality tier coverage check.

    Polished/delightful tiers require specific artifact types.
    """

    passed: bool
    tier: str
    covered: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    message: str = ""


# ── Core: synthesize ─────────────────────────────────────────────────────────


def _findings_breakdown(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


def synthesize(
    evals: list[EvalReport],
    tier: str | None = None,
) -> GateVerdict:
    """Compute a deterministic gate verdict from evaluation reports.

    OPC-derived priority:
      1. Any BLOCKED → BLOCKED (hard stop)
      2. Any critical (🔴) → FAIL
      3. Any warning (🟡) → ITERATE
      4. All suggestion/info → PASS

    Args:
        evals: Evaluation reports from one or more reviewer agents.
        tier: Optional quality tier ("functional" | "polished" | "delightful").

    Returns:
        GateVerdict with verdict, summary, and detailed breakdown.
    """
    all_findings: list[Finding] = []
    lines: list[str] = []
    flattened = _flatten_artifacts(evals)

    for report in evals:
        all_findings.extend(report.findings)
        if report.raw_text:
            parsed, errors = _parse_eval_markdown(report.raw_text)
            all_findings.extend(parsed)
            lines.append(f"  [{report.role}] {report.summary or _summarize(parsed)}")
            for err in errors:
                lines.append(f"    parse warning: {err}")
        else:
            lines.append(f"  [{report.role}] {report.summary}")

    breakdown = _findings_breakdown(all_findings)
    failures = [f for f in all_findings if f.severity == "critical"]
    warnings_list = [f for f in all_findings if f.severity == "warning"]
    blocked = [f for f in all_findings if f.severity == "blocked"]

    # ── Verdict computation ──
    if blocked:
        detail_lines = ["⛔ BLOCKED — hard blocker found:"]
        for b in blocked:
            loc = f"{b.file_ref}:{b.line}" if b.file_ref and b.line else (b.file_ref or "")
            detail_lines.append(f"  ⛔ {b.message}  {loc}".strip())
            if b.code:
                detail_lines.append(f"     code: {b.code}")
        report = "\n".join(detail_lines)
        return GateVerdict(
            verdict="BLOCKED",
            summary=f"{len(blocked)} blocker(s) — pipeline cannot proceed",
            findings_breakdown=breakdown,
            failures=failures,
            warnings=warnings_list,
            detail=report,
        )

    if failures:
        detail_lines = [f"🔴 FAIL — {len(failures)} critical finding(s):"]
        for f in failures:
            loc = f"{f.file_ref}:{f.line}" if f.file_ref and f.line else (f.file_ref or "")
            detail_lines.append(f"  🔴 {f.message}  {loc}".strip())
            if f.code:
                detail_lines.append(f"     code: {f.code}")
        report = "\n".join(detail_lines)
        return GateVerdict(
            verdict="FAIL",
            summary=f"{len(failures)} critical finding(s) — changes required",
            findings_breakdown=breakdown,
            failures=failures,
            warnings=warnings_list,
            detail=report,
        )

    if warnings_list:
        detail_lines = [f"🟡 ITERATE — {len(warnings_list)} warning(s):"]
        for f in warnings_list:
            loc = f"{f.file_ref}:{f.line}" if f.file_ref and f.line else (f.file_ref or "")
            detail_lines.append(f"  🟡 {f.message}  {loc}".strip())
            if f.code:
                detail_lines.append(f"     code: {f.code}")
        report = "\n".join(detail_lines)
        return GateVerdict(
            verdict="ITERATE",
            summary=f"{len(warnings_list)} warning(s) — address before proceeding",
            findings_breakdown=breakdown,
            failures=failures,
            warnings=warnings_list,
            detail=report,
        )

    detail = "✅ PASS — all checks clear\n" + "\n".join(lines)
    return GateVerdict(
        verdict="PASS",
        summary=f"{len(evals)} evaluation(s), all clear",
        findings_breakdown=breakdown,
        detail=detail,
    )


# ── Review independence ─────────────────────────────────────────────────────


def check_independence(evals: list[EvalReport]) -> IndependenceResult:
    """Verify review independence: ≥2 evals, no identical content.

    Ported from OPC's review independence guard: at least 2 independent
    eval files must exist. If 2+ have identical findings (same severity,
    same message text), they are flagged as non-independent.

    Returns:
        IndependenceResult with pass/fail and optional overlap warning.
    """
    if len(evals) < 2:
        return IndependenceResult(
            passed=False,
            eval_count=len(evals),
            message=f"Need at least 2 independent evaluations, got {len(evals)}",
        )

    # Check for identical content (same finding messages across roles)
    seen_pairs: set[tuple[str, str]] = set()
    for report in evals:
        for finding in report.findings:
            key = (finding.severity, finding.message.strip().lower())
            if key in seen_pairs:
                return IndependenceResult(
                    passed=False,
                    eval_count=len(evals),
                    message=f"Non-independent evaluation detected: identical finding '{key[1]}' appears across multiple roles",
                    overlap_warning=f"Duplicate '{key[1]}' flagged as potential role collusion",
                )
            seen_pairs.add(key)

    # Line overlap warning (same file+line mentioned by different roles)
    refs: dict[tuple[str, int], list[str]] = {}
    for report in evals:
        for finding in report.findings:
            if finding.file_ref and finding.line:
                key = (finding.file_ref, finding.line)
                if key not in refs:
                    refs[key] = []
                refs[key].append(report.role)

    overlapping = {k: v for k, v in refs.items() if len(v) > 1}
    overlap_warning: str | None = None
    if overlapping:
        samples = [f"{f[0]}:{f[1]} (by {', '.join(r)})" for f, r in list(overlapping.items())[:3]]
        overlap_warning = f"Line overlap detected: {'; '.join(samples)}"

    return IndependenceResult(
        passed=True,
        eval_count=len(evals),
        message=f"{len(evals)} independent evaluations",
        overlap_warning=overlap_warning,
    )


# ── Oscillation detection ────────────────────────────────────────────────────


def detect_oscillation(
    current: GateVerdict,
    previous: GateVerdict | None,
) -> OscillationResult:
    """Detect A→B→A oscillation between consecutive gate rounds.

    Ported from OPC's oscillation detection: if the verdict alternates
    between non-PASS states (e.g. FAIL → ITERATE → FAIL), the pipeline
    is stuck in a feedback loop.

    Args:
        current: Current gate verdict.
        previous: Previous gate verdict, or None if first round.

    Returns:
        OscillationResult with oscillating bool and pattern description.
    """
    if previous is None:
        return OscillationResult(oscillating=False)

    pattern = [previous.verdict, current.verdict]

    # Detect FAIL→ITERATE→FAIL pattern (3-round minimum for oscillation)
    if len(pattern) >= 2 and pattern[-1] == pattern[-2]:
        return OscillationResult(
            oscillating=False,
            pattern=pattern,
            message=f"Consecutive {pattern[-1]} — converging",
        )

    # Flag if we see reverse of previous verdict
    opposites = {"FAIL": "ITERATE", "ITERATE": "FAIL", "PASS": None, "BLOCKED": None}
    if len(pattern) >= 2 and opposites.get(pattern[-2]) == pattern[-1]:
        return OscillationResult(
            oscillating=True,
            pattern=pattern,
            message=f"Oscillation detected: {pattern[-2]} → {pattern[-1]}. "
            f"Pipeline is not converging toward PASS.",
        )

    return OscillationResult(
        oscillating=False,
        pattern=pattern,
        message=f"Stable: {' → '.join(pattern)}",
    )


# ── Criteria lint ────────────────────────────────────────────────────────────


@dataclass
class CriteriaLintResult:
    """Result of mechanical acceptance criteria validation.

    Ported from OPC's criteria-lint: single-pass structure + content checks
    that run BEFORE any pipeline work starts. If lint fails, init is blocked.
    """

    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    criteria_count: int = 0
    message: str = ""


_CRITERIA_EXPECTED_SECTIONS = [
    "return format",
    "examples",
]

_DEFERRAL_PATTERNS = re.compile(
    r"(deferred|next (loop|version|sprint)|future work|"
    r"follow.up (loop|work)|punted|later loop|todo:? next)",
    re.IGNORECASE,
)


def lint_criteria(text: str) -> CriteriaLintResult:
    """Mechanically lint acceptance criteria text.

    Checks:
      - Required sections present (Return Format, Examples)
      - No deferral language
      - At least one concrete, testable criterion
      - No empty criteria bullet points

    Returns:
        CriteriaLintResult with pass/fail and detailed errors.
    """
    errors: list[str] = []
    warnings: list[str] = []
    lower = text.lower()

    # ── Required sections ──
    missing_sections = [s for s in _CRITERIA_EXPECTED_SECTIONS if s not in lower]
    for s in missing_sections:
        errors.append(f"Missing required section: '{s}'")

    # ── Deferral language ──
    deferral_matches = _DEFERRAL_PATTERNS.findall(text)
    matched_terms = {m[0].strip() if isinstance(m, tuple) else str(m).strip() for m in deferral_matches}
    matched_terms = {t for t in matched_terms if t}
    if matched_terms:
        warnings.append(
            f"Deferral language detected ({', '.join(sorted(matched_terms))}). "
            f"Criteria should define what DONE looks like, not what to defer."
        )

    # ── Criterion count ──
    bullet_criteria = re.findall(r"^[-*]\s+\S", text, re.MULTILINE)
    criteria_count = len(bullet_criteria)
    if criteria_count == 0:
        errors.append("No criteria found. Add at least one bullet-point criterion.")
    elif criteria_count < 2:
        warnings.append(f"Only {criteria_count} criterion. Consider adding more for clarity.")

    # ── Empty bullet check ──
    empty_bullets = re.findall(r"^[-*]\s*$", text, re.MULTILINE)
    if empty_bullets:
        errors.append(f"Found {len(empty_bullets)} empty bullet point(s).")

    # ── Verdict ──
    status = "PASS" if not errors else "FAIL"
    parts = [status]
    if errors:
        parts.append(f"{len(errors)} error(s)")
    if warnings:
        parts.append(f"{len(warnings)} warning(s)")
    parts.append(f"{criteria_count} criteria")

    return CriteriaLintResult(
        passed=not errors,
        errors=errors,
        warnings=warnings,
        criteria_count=criteria_count,
        message=" | ".join(parts),
    )


# ── Tier coverage ────────────────────────────────────────────────────────────


_TIER_REQUIREMENTS: dict[str, set[str]] = {
    "functional": set(),
    "polished": {"screenshot", "test-result"},
    "delightful": {"screenshot", "test-result", "cli-output"},
}


def check_tier_coverage(
    artifacts: list[str],
    tier: str,
) -> TierCoverageResult:
    """Verify that execute-node artifacts meet quality tier requirements.

    Ported from OPC's quality tier coverage checks. Polished requires
    screenshots; delightful requires screenshots + test results.

    Args:
        artifacts: List of artifact type strings (e.g. "screenshot", "test-result").
        tier: Quality tier: "functional" | "polished" | "delightful".

    Returns:
        TierCoverageResult with covered/missing artifact types.
    """
    if tier not in _TIER_REQUIREMENTS:
        return TierCoverageResult(
            passed=True,
            tier=tier,
            message=f"Unknown tier '{tier}', skipping coverage check",
        )

    required = _TIER_REQUIREMENTS[tier]
    artifact_set = set(artifacts)
    covered = list(required & artifact_set)
    missing = list(required - artifact_set)

    if not missing:
        return TierCoverageResult(
            passed=True,
            tier=tier,
            covered=covered,
            message=f"{tier} tier: {len(covered)}/{len(required)} artifact types covered",
        )

    return TierCoverageResult(
        passed=False,
        tier=tier,
        covered=covered,
        missing=missing,
        message=f"{tier} tier: missing {missing}",
    )


# ── Internal helpers ─────────────────────────────────────────────────────────


_EMOJI_SEVERITY: dict[str, Severity] = {
    "🔴": "critical",
    "🟡": "warning",
    "🔵": "suggestion",
    "⛔": "blocked",
    "ℹ️": "info",
}

_EVAL_LINE_PATTERN = re.compile(
    r"^(?P<emoji>[🔴🟡🔵⛔ℹ️])\s*(?P<message>.+)"
)


def _parse_eval_markdown(text: str) -> tuple[list[Finding], list[str]]:
    """Parse OPC-style evaluation markdown into structured findings.

    Accepts lines prefixed with severity emoji:
      🔴 Critical: XSS vulnerability in login form
      🟡 Warning: Missing error handling in edge case
      🔵 Suggestion: Consider renaming for clarity

    Supports optional trailing file:line references:
      🔴 Hardcoded secret in config.py:42
    """
    findings: list[Finding] = []
    errors: list[str] = []

    file_line_re = re.compile(r"^(.+?):(\d+)$")

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        m = _EVAL_LINE_PATTERN.match(line)
        if not m:
            # Check for severity keyword prefixes
            for prefix, sev in [("critical:", "critical"), ("warning:", "warning"),
                                ("suggestion:", "suggestion"), ("blocked:", "blocked"),
                                ("info:", "info")]:
                if line.lower().startswith(prefix):
                    rest = line[len(prefix):].strip()
                    file_ref = None
                    line_num = None
                    code = None

                    # Check for trailing file:line
                    parts = rest.rsplit(" ", 1)
                    if len(parts) == 2:
                        flm = file_line_re.match(parts[1])
                        if flm:
                            file_ref = flm.group(1)
                            line_num = int(flm.group(2))
                            rest = parts[0]

                    findings.append(Finding(
                        severity=sev,
                        message=rest,
                        file_ref=file_ref,
                        line=line_num,
                        code=code,
                    ))
                    break
            continue

        emoji = m.group("emoji")
        message = m.group("message").strip()
        severity = _EMOJI_SEVERITY.get(emoji, "info")

        file_ref = None
        line_num = None
        code = None

        # Check for code prefix like "[S701]"
        code_m = re.match(r"^\[([A-Z0-9]+)\]\s*(.*)", message)
        if code_m:
            code = code_m.group(1)
            message = code_m.group(2)

        # Check for trailing file:line
        parts = message.rsplit(" ", 1)
        if len(parts) == 2:
            flm = file_line_re.match(parts[1])
            if flm:
                file_ref = flm.group(1)
                line_num = int(flm.group(2))
                message = parts[0]

        findings.append(Finding(
            severity=severity,
            message=message,
            file_ref=file_ref,
            line=line_num,
            code=code,
        ))

    return findings, errors


def _summarize(findings: list[Finding]) -> str:
    """Generate a one-line summary from findings."""
    counts = _findings_breakdown(findings)
    parts = [f"{v}×{k}" for k, v in sorted(counts.items())]
    return f"{len(findings)} finding(s): {', '.join(parts)}" if parts else "no findings"


def _flatten_artifacts(evals: list[EvalReport]) -> list[dict[str, Any]]:
    """Flatten eval reports to a machine-readable artifact list."""
    artifacts = []
    for report in evals:
        for finding in report.findings:
            artifacts.append({
                "role": report.role,
                "severity": finding.severity,
                "message": finding.message,
                "file_ref": finding.file_ref,
                "line": finding.line,
                "code": finding.code,
            })
    return artifacts
