"""Tests for the mechanical gate engine (harness/gate_engine.py)."""

from fleet_agent.harness.gate_engine import (
    EvalReport,
    Finding,
    check_independence,
    check_tier_coverage,
    detect_oscillation,
    lint_criteria,
    synthesize,
)


def test_synthesize_pass():
    evals = [
        EvalReport(
            role="security",
            findings=[Finding(severity="suggestion", message="Consider adding rate limiting")],
            summary="No issues found",
        ),
        EvalReport(
            role="frontend",
            findings=[Finding(severity="info", message="LGTM")],
            summary="Looks good",
        ),
    ]
    result = synthesize(evals)
    assert result.verdict == "PASS"
    assert "all clear" in result.summary


def test_synthesize_fail_on_critical():
    evals = [
        EvalReport(
            role="security",
            findings=[
                Finding(
                    severity="critical",
                    message="Hardcoded API key in config.py",
                    file_ref="config.py",
                    line=42,
                )
            ],
            summary="Critical issue found",
        ),
    ]
    result = synthesize(evals)
    assert result.verdict == "FAIL"
    assert len(result.failures) == 1
    assert result.failures[0].file_ref == "config.py"


def test_synthesize_iterate_on_warning():
    evals = [
        EvalReport(
            role="backend",
            findings=[
                Finding(severity="warning", message="Missing error handling on line 88"),
            ],
            summary="Minor concerns",
        ),
    ]
    result = synthesize(evals)
    assert result.verdict == "ITERATE"
    assert len(result.warnings) == 1


def test_synthesize_blocked():
    evals = [
        EvalReport(
            role="compliance",
            findings=[
                Finding(severity="blocked", message="GDPR audit required before deployment"),
            ],
            summary="Blocked",
        ),
    ]
    result = synthesize(evals)
    assert result.verdict == "BLOCKED"


def test_mixed_severity_fail_wins():
    """Critical beat warning and suggestion."""
    evals = [
        EvalReport(
            role="reviewer",
            findings=[
                Finding(severity="critical", message="Remote code execution in parser"),
                Finding(severity="warning", message="Minor formatting"),
                Finding(severity="suggestion", message="Rename for clarity"),
            ],
            summary="Mixed findings",
        ),
    ]
    result = synthesize(evals)
    assert result.verdict == "FAIL"
    assert len(result.failures) == 1
    assert len(result.warnings) == 1
    assert result.findings_breakdown.get("critical") == 1
    assert result.findings_breakdown.get("warning") == 1


def test_empty_evals_pass():
    evals = [EvalReport(role="none", findings=[], summary="Nothing to review")]
    result = synthesize(evals)
    assert result.verdict == "PASS"


def test_check_independence_pass():
    evals = [
        EvalReport(role="frontend", findings=[
            Finding(severity="warning", message="Missing ARIA labels"),
        ]),
        EvalReport(role="security", findings=[
            Finding(severity="critical", message="XSS in search form"),
        ]),
    ]
    result = check_independence(evals)
    assert result.passed
    assert result.eval_count == 2


def test_check_independence_fail_single():
    evals = [EvalReport(role="frontend", findings=[], summary="ok")]
    result = check_independence(evals)
    assert not result.passed
    assert "2 independent" in result.message


def test_check_independence_identical_content():
    evals = [
        EvalReport(role="frontend", findings=[
            Finding(severity="warning", message="Same issue"),
        ]),
        EvalReport(role="backend", findings=[
            Finding(severity="warning", message="Same issue"),
        ]),
    ]
    result = check_independence(evals)
    assert not result.passed
    assert "identical" in result.message.lower()


def test_lint_criteria_pass():
    text = """## Acceptance Criteria

- Search returns results within 2 seconds
- Empty state shows helpful message
- Error state shows retry button

## Return Format
{"success": bool, "data": list}

## Examples
search("query")
"""
    result = lint_criteria(text)
    assert result.passed
    assert result.criteria_count >= 3


def test_lint_criteria_no_criteria():
    text = "Some vague description without bullet points."
    result = lint_criteria(text)
    assert not result.passed
    assert any("No criteria" in e for e in result.errors)


def test_lint_criteria_deferral_language():
    text = """- Implement basic search
- Defer advanced filtering to next sprint

## Return Format
{"success": bool}

## Examples
search()
"""
    result = lint_criteria(text)
    assert result.passed  # no hard error, just a warning
    assert len(result.warnings) > 0


def test_lint_criteria_empty_bullets():
    text = """- 
- This one has content

## Return Format
{"ok": true}

## Examples
test()
"""
    result = lint_criteria(text)
    assert not result.passed
    assert any("empty bullet" in e.lower() for e in result.errors)


def test_lint_criteria_missing_sections():
    text = "- Do the thing"
    result = lint_criteria(text)
    assert not result.passed
    assert any("return format" in e.lower() for e in result.errors)


def test_oscillation_no_previous():
    verdict = synthesize([], tier="functional")
    result = detect_oscillation(verdict, None)
    assert not result.oscillating


def test_oscillation_stable():
    v1 = synthesize([EvalReport(role="x", findings=[
        Finding(severity="warning", message="Fix this"),
    ])])
    v2 = synthesize([EvalReport(role="x", findings=[
        Finding(severity="warning", message="Fix this"),
        Finding(severity="warning", message="Also this"),
    ])])
    result = detect_oscillation(v2, v1)
    # Both ITERATE → not oscillating
    assert not result.oscillating


def test_oscillation_detected():
    """FAIL → ITERATE is a reversal, but needs 3-round for true oscillation."""
    v1 = synthesize([EvalReport(role="x", findings=[
        Finding(severity="critical", message="Security issue"),
    ])])
    v2 = synthesize([EvalReport(role="x", findings=[
        Finding(severity="warning", message="Minor issue"),
    ])])
    result = detect_oscillation(v2, v1)
    assert result.oscillating
    assert "FAIL" in result.message or "ITERATE" in result.message


def test_tier_coverage_functional():
    result = check_tier_coverage([], "functional")
    assert result.passed


def test_tier_coverage_polished_missing_screenshot():
    result = check_tier_coverage(["test-result"], "polished")
    assert not result.passed
    assert "screenshot" in str(result.missing)


def test_tier_coverage_delightful_pass():
    result = check_tier_coverage(["screenshot", "test-result", "cli-output"], "delightful")
    assert result.passed


def test_tier_coverage_unknown_tier():
    result = check_tier_coverage([], "unknown")
    assert result.passed


def test_parse_eval_markdown():
    from fleet_agent.harness.gate_engine import _parse_eval_markdown
    md = """🔴 Critical: Hardcoded secret in config.py:42
🟡 Warning: Missing input validation on line 88
🔵 Suggestion: Rename for clarity
⛔ Blocked: Compliance review needed
"""
    findings, errors = _parse_eval_markdown(md)
    assert len(findings) == 4
    severities = {f.severity for f in findings}
    assert severities == {"critical", "warning", "suggestion", "blocked"}
    assert findings[0].file_ref == "config.py"
    assert findings[0].line == 42
