"""Tests for the state machine engine."""

import tempfile
from pathlib import Path

import pytest
import yaml

from fleet_agent.engine.sqlite_store import SqliteStore
from fleet_agent.engine.state_machine import StateMachine
from fleet_agent.engine.workflow_loader import load_workflow


@pytest.fixture
def temp_db() -> SqliteStore:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    store = SqliteStore(db_path=db_path)
    yield store
    try:
        db_path.unlink(missing_ok=True)
        for sfx in ["-wal", "-shm"]:
            Path(str(db_path) + sfx).unlink(missing_ok=True)
    except PermissionError:
        pass  # Windows SQLite lock may still be held briefly


@pytest.fixture
def sm(temp_db: SqliteStore) -> StateMachine:
    # Override the singleton with test store
    import fleet_agent.engine.state_machine as sm_module
    machine = StateMachine()
    machine._store = temp_db
    sm_module._state_machine = machine
    return machine


@pytest.fixture
def sample_workflow_yaml(tmp_path: Path) -> Path:
    wf = {
        "name": "test-workflow",
        "description": "A test workflow",
        "start": "step1",
        "nodes": {
            "step1": {"task": "Do step 1", "next": "step2"},
            "step2": {
                "task": "Decide next step",
                "branches": [
                    {"condition": "success", "next": "step3"},
                    {"condition": "failure", "next": "step1"},
                ],
            },
            "step3": {"task": "Final step", "terminal": True},
        },
    }
    path = tmp_path / "test.yaml"
    path.write_text(yaml.dump(wf), encoding="utf-8")
    return path


def test_load_workflow(sample_workflow_yaml):
    wf = load_workflow(str(sample_workflow_yaml))
    assert wf.name == "test-workflow"
    assert wf.description == "A test workflow"
    assert wf.start == "step1"
    assert len(wf.nodes) == 3
    assert wf.nodes["step1"].task == "Do step 1"
    assert wf.nodes["step1"].next_node == "step2"
    assert wf.nodes["step2"].branches[0].condition == "success"
    assert wf.nodes["step2"].branches[0].next == "step3"
    assert wf.nodes["step3"].terminal is True


def test_register_and_list(sm, sample_workflow_yaml):
    wf = sm.register_workflow(str(sample_workflow_yaml))
    assert wf.name == "test-workflow"

    wfs = sm.list_workflows()
    assert len(wfs) == 1
    assert wfs[0]["name"] == "test-workflow"


def test_start_and_status(sm, sample_workflow_yaml):
    sm.register_workflow(str(sample_workflow_yaml))
    instance = sm.start("test-workflow")
    assert instance.workflow_name == "test-workflow"
    assert instance.current_node == "step1"

    status = sm.status()
    assert status is not None
    assert status.current_node == "step1"

    task = sm.get_current_task()
    assert task == "Do step 1"


def test_next_linear(sm, sample_workflow_yaml):
    sm.register_workflow(str(sample_workflow_yaml))
    sm.start("test-workflow")

    instance = sm.next()
    assert instance is not None
    assert instance.current_node == "step2"

    task = sm.get_current_task()
    assert task == "Decide next step"


def test_next_branch(sm, sample_workflow_yaml):
    sm.register_workflow(str(sample_workflow_yaml))
    sm.start("test-workflow")

    # Advance from step1 → step2
    sm.next()

    # At step2, take branch 0 (success → step3)
    instance = sm.next(branch=0)
    assert instance.current_node == "step3"
    assert sm.get_current_task() == "Final step"


def test_next_terminal(sm, sample_workflow_yaml):
    sm.register_workflow(str(sample_workflow_yaml))
    sm.start("test-workflow")
    sm.next()  # step1 → step2
    sm.next(branch=0)  # step2 → step3 (terminal)

    # Terminal — should complete and archive
    result = sm.next()
    assert result is None  # Workflow completed
    assert sm.status() is None  # No active instance


def test_next_branch_fail_loop(sm, sample_workflow_yaml):
    sm.register_workflow(str(sample_workflow_yaml))
    sm.start("test-workflow")
    sm.next()  # step1 → step2

    # Take branch 1 (failure → step1)
    instance = sm.next(branch=1)
    assert instance.current_node == "step1"
    assert sm.get_current_task() == "Do step 1"


def test_history(sm, sample_workflow_yaml):
    sm.register_workflow(str(sample_workflow_yaml))
    sm.start("test-workflow")
    sm.next()  # step1 → step2
    sm.next(branch=0)  # step2 → step3

    history = sm.log()
    assert len(history) == 2
    assert history[0]["from_node"] == "step1"
    assert history[0]["to_node"] == "step2"
    assert history[1]["from_node"] == "step2"
    assert history[1]["to_node"] == "step3"
    assert history[1]["branch"] == "success"


def test_reset(sm, sample_workflow_yaml):
    sm.register_workflow(str(sample_workflow_yaml))
    sm.start("test-workflow")
    sm.next()  # step1 → step2

    # Reset
    instance = sm.reset()
    assert instance.current_node == "step1"

    # Old instance should be archived
    active = sm.list_active()
    assert len([a for a in active if a["current_node"] == "step1"]) == 1


def test_start_unregistered(sm):
    with pytest.raises(ValueError, match="not registered"):
        sm.start("nonexistent")


def test_branches_info(sm, sample_workflow_yaml):
    sm.register_workflow(str(sample_workflow_yaml))
    sm.start("test-workflow")
    sm.next()  # step1 → step2

    branches = sm.get_current_branches()
    assert branches is not None
    assert len(branches) == 2
    assert branches[0]["condition"] == "success"
    assert branches[0]["next"] == "step3"
    assert branches[1]["condition"] == "failure"
    assert branches[1]["next"] == "step1"


def test_to_dict(sm, sample_workflow_yaml):
    sm.register_workflow(str(sample_workflow_yaml))
    instance = sm.start("test-workflow")
    d = instance.to_dict()
    assert d["workflow_name"] == "test-workflow"
    assert d["current_node"] == "step1"
    assert "history" in d
