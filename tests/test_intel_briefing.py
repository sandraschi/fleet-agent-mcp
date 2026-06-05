"""Intel briefing hot-item selection (CROSS-4)."""

from __future__ import annotations

from fleet_agent.coworker.intel_briefing import (
    READLY_RELEVANCE_PULSE_THRESHOLD,
    URGENCY_PULSE_THRESHOLD,
    _is_readly_longform,
    qualifies_for_pulse_task,
)


def test_is_readly_longform_by_feed_type():
    assert _is_readly_longform({"feed_type": "readly", "source": "Readly: Wired"}) is True


def test_is_readly_longform_by_source_prefix():
    assert _is_readly_longform({"source": "Readly: New Scientist"}) is True


def test_is_readly_longform_by_tags():
    assert _is_readly_longform({"tags": ["longform"], "source": "rss"}) is True


def test_qualifies_on_high_urgency():
    item = {"urgency": 8.5, "relevance": 3.0, "source": "HN"}
    assert qualifies_for_pulse_task(item) is True


def test_qualifies_on_readly_relevance_not_urgency():
    item = {
        "urgency": 4.0,
        "relevance": READLY_RELEVANCE_PULSE_THRESHOLD,
        "source": "Readly: Nature",
        "feed_type": "readly",
    }
    assert qualifies_for_pulse_task(item) is True


def test_skips_low_readly_relevance():
    item = {
        "urgency": 5.0,
        "relevance": READLY_RELEVANCE_PULSE_THRESHOLD - 0.1,
        "source": "Readly: Wired",
        "feed_type": "readly",
    }
    assert qualifies_for_pulse_task(item) is False


def test_skips_non_readly_low_urgency():
    item = {"urgency": 7.0, "relevance": 9.0, "source": "TechCrunch"}
    assert qualifies_for_pulse_task(item, urgency_threshold=URGENCY_PULSE_THRESHOLD) is False
