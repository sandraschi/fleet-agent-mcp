"""Tests for workflow YAML loading."""

from pathlib import Path

import pytest
import yaml

from fleet_agent.engine.workflow_loader import discover_workflows, load_workflow


@pytest.fixture
def temp_workflows_dir(tmp_path: Path) -> Path:
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()

    # Create a test workflow
    wf1 = {
        "name": "test-daily",
        "description": "Daily routine",
        "start": "morning",
        "nodes": {
            "morning": {"task": "Check emails", "next": "afternoon"},
            "afternoon": {"task": "Write code", "terminal": True},
        },
    }
    (wf_dir / "daily.yaml").write_text(yaml.dump(wf1), encoding="utf-8")

    # Create another
    wf2 = {
        "name": "test-review",
        "description": "Code review workflow",
        "start": "review",
        "nodes": {
            "review": {
                "task": "Review code",
                "branches": [
                    {"condition": "approved", "next": "merge"},
                    {"condition": "rejected", "next": "fix"},
                ],
            },
            "fix": {"task": "Fix issues", "next": "review"},
            "merge": {"task": "Merge PR", "terminal": True},
        },
    }
    (wf_dir / "review.yml").write_text(yaml.dump(wf2), encoding="utf-8")

    return tmp_path


def test_discover_workflows(temp_workflows_dir: Path):
    paths = discover_workflows(temp_workflows_dir)
    assert len(paths) == 2
    assert any("daily" in p for p in paths)
    assert any("review" in p for p in paths)


def test_load_both_discovered(temp_workflows_dir: Path):
    paths = discover_workflows(temp_workflows_dir)
    for path in paths:
        wf = load_workflow(path)
        assert wf.name.startswith("test-")
        assert len(wf.nodes) >= 2


def test_branching_workflow(temp_workflows_dir: Path):
    paths = discover_workflows(temp_workflows_dir)
    review_path = [p for p in paths if "review" in p][0]
    wf = load_workflow(review_path)
    assert wf.name == "test-review"
    assert len(wf.nodes["review"].branches) == 2
    assert wf.nodes["review"].branches[0].condition == "approved"
    assert wf.nodes["review"].branches[0].next == "merge"


def test_load_nonexistent():
    with pytest.raises(FileNotFoundError):
        load_workflow("/nonexistent/path.yaml")


def test_morning_brief_workflow_loads():
    """WF-001 shipped workflow must parse and register."""
    root = Path(__file__).resolve().parents[1]
    path = root / "workflows" / "morning_brief.yaml"
    wf = load_workflow(str(path))
    assert wf.name == "morning_brief"
    assert wf.start == "glance"
    assert wf.nodes["memops"].terminal is True
    assert "glance" in wf.nodes["glance"].task


def test_workflow_to_dict(temp_workflows_dir: Path):
    paths = discover_workflows(temp_workflows_dir)
    daily_path = [p for p in paths if "daily" in p][0]
    wf = load_workflow(daily_path)
    d = wf.to_dict()
    assert d["name"] == "test-daily"
    assert "nodes" in d
    assert d["nodes"]["morning"]["task"] == "Check emails"
