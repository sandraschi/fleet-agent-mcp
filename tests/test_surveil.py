"""Tests for fritz_surveil fleet-domain triage (P3)."""

from __future__ import annotations

from fleet_agent.coworker.surveil import DEFAULT_RULES, evaluate_server


def test_healthy_server_is_informational():
    severity, rule, text = evaluate_server(
        "calibre-mcp",
        last_status="healthy",
        total_checks=50,
        uptime_pct=100.0,
        restarts_recent=0,
    )
    assert severity == "informational"
    assert rule == ""


def test_restart_loop_is_urgent():
    severity, rule, text = evaluate_server(
        "plex-mcp",
        last_status="healthy",
        total_checks=50,
        uptime_pct=100.0,
        restarts_recent=4,
    )
    assert severity == "urgent"
    assert rule == "restart_loop"


def test_single_restart_not_flagged():
    severity, _, _ = evaluate_server(
        "plex-mcp", last_status="healthy", total_checks=50, uptime_pct=100.0, restarts_recent=1
    )
    assert severity == "informational"


def test_unreachable_never_healthy_is_informational():
    severity, _, _ = evaluate_server(
        "alexa-mcp",
        last_status="unreachable",
        total_checks=40,
        uptime_pct=0.0,
        restarts_recent=0,
        was_healthy=False,
    )
    assert severity == "informational"


def test_unreachable_notice_and_urgent():
    severity, rule, _ = evaluate_server(
        "alexa-mcp", last_status="unreachable", total_checks=15, uptime_pct=0.0, restarts_recent=0
    )
    assert severity == "notice"
    assert rule == "unreachable"

    severity, _, _ = evaluate_server(
        "alexa-mcp", last_status="unreachable", total_checks=40, uptime_pct=0.0, restarts_recent=0
    )
    assert severity == "urgent"


def test_unreachable_few_checks_informational():
    severity, _, _ = evaluate_server(
        "alexa-mcp", last_status="unreachable", total_checks=3, uptime_pct=0.0, restarts_recent=0
    )
    assert severity == "informational"


def test_degraded_uptime_notice_and_urgent():
    severity, rule, _ = evaluate_server(
        "aiwatcher-mcp", last_status="healthy", total_checks=30, uptime_pct=80.0, restarts_recent=0
    )
    assert severity == "notice"
    assert rule == "degraded"

    severity, _, _ = evaluate_server(
        "aiwatcher-mcp", last_status="healthy", total_checks=30, uptime_pct=40.0, restarts_recent=0
    )
    assert severity == "urgent"


def test_custom_rules_override():
    custom = {
        **DEFAULT_RULES,
        "restart_loop": {"window_minutes": 10, "min_restarts": 5, "severity": "urgent"},
    }
    severity, _, _ = evaluate_server(
        "x-mcp",
        last_status="healthy",
        total_checks=10,
        uptime_pct=100.0,
        restarts_recent=4,
        rules=custom,
    )
    assert severity == "informational"
