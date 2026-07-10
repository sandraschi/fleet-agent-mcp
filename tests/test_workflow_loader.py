"""Tests for workflow loader (JSON flow templates, node types, gate support)."""

import json
import tempfile
from pathlib import Path

import pytest

from fleet_agent.engine.workflow_loader import (
    WorkflowNode,
    workflow_from_dict,
    load_workflow_from_json,
    discover_workflows,
)


class TestJsonFlowTemplates:
    def test_load_minimal_json(self):
        data = {
            "name": "test-flow",
            "description": "A test flow",
            "start": "build",
            "nodes": {
                "build": {"task": "Build it", "next": "done"},
                "done": {"task": "Finish", "terminal": True},
            },
        }
        wf = workflow_from_dict(data)
        assert wf.name == "test-flow"
        assert wf.start == "build"
        assert len(wf.nodes) == 2

    def test_node_types_from_json(self):
        data = {
            "name": "gate-flow",
            "start": "review",
            "nodes": {
                "review": {
                    "task": "Review code",
                    "node_type": "review",
                    "branches_map": {"PASS": "gate", "FAIL": "build"},
                },
                "build": {"task": "Fix issues", "node_type": "build", "next": "review"},
                "gate": {
                    "task": "Quality gate",
                    "node_type": "gate",
                    "branches_map": {"PASS": None, "FAIL": "review"},
                },
            },
        }
        wf = workflow_from_dict(data)
        assert wf.nodes["review"].node_type == "review"
        assert wf.nodes["build"].node_type == "build"
        assert wf.nodes["gate"].node_type == "gate"
        assert wf.nodes["gate"].branches_map == {"PASS": None, "FAIL": "review"}

    def test_branches_map_verdict_routing(self):
        data = {
            "name": "review-gate",
            "start": "review",
            "nodes": {
                "review": {
                    "task": "Review",
                    "node_type": "review",
                    "branches_map": {"PASS": "done", "FAIL": "review", "ITERATE": "review"},
                },
                "done": {"task": "Done", "terminal": True},
            },
        }
        wf = workflow_from_dict(data)
        assert wf.nodes["review"].branches[0].condition == "PASS"
        assert wf.nodes["review"].branches[0].next == "done"
        assert wf.nodes["review"].branches[1].condition == "FAIL"
        assert wf.nodes["review"].branches[2].condition == "ITERATE"

    def test_context_schema(self):
        data = {
            "name": "schema-flow",
            "start": "build",
            "nodes": {"build": {"task": "Build", "terminal": True}},
            "context_schema": {
                "build": {
                    "required": ["projectDir"],
                    "rules": {"projectDir": "non-empty-string"},
                }
            },
        }
        wf = workflow_from_dict(data)
        assert wf.context_schema is not None
        assert wf.context_schema["build"]["required"] == ["projectDir"]

    def test_soft_evidence(self):
        data = {
            "name": "soft-flow",
            "start": "exec",
            "nodes": {"exec": {"task": "Execute", "node_type": "execute", "next": "done"},
                      "done": {"task": "Done", "terminal": True}},
            "soft_evidence": True,
        }
        wf = workflow_from_dict(data)
        assert wf.soft_evidence is True


class TestWorkflowValidation:
    def test_invalid_node_type_raises(self):
        data = {
            "name": "bad-flow",
            "start": "build",
            "nodes": {"build": {"task": "Build", "node_type": "invalid_type", "next": "done"},
                      "done": {"task": "Done", "terminal": True}},
        }
        with pytest.raises(ValueError, match="Invalid node_type"):
            workflow_from_dict(data)

    def test_missing_start_raises(self):
        with pytest.raises(ValueError, match="start"):
            workflow_from_dict({"nodes": {"a": {"task": "A"}}})

    def test_missing_nodes_raises(self):
        with pytest.raises(ValueError, match="nodes"):
            workflow_from_dict({"start": "build"})

    def test_bad_edge_target_raises(self):
        data = {
            "name": "bad-edge",
            "start": "build",
            "nodes": {"build": {"task": "Build", "next": "nonexistent"}},
        }
        with pytest.raises(ValueError, match="nonexistent"):
            workflow_from_dict(data)

    def test_bad_branch_target_raises(self):
        data = {
            "name": "bad-branch",
            "start": "review",
            "nodes": {
                "review": {
                    "task": "Review",
                    "node_type": "review",
                    "branches_map": {"PASS": "fake_dest"},
                },
            },
        }
        with pytest.raises(ValueError, match="fake_dest"):
            workflow_from_dict(data)

    def test_prototype_pollution_rejected(self):
        data = {
            "name": "pollute",
            "start": "build",
            "nodes": {
                "build": {"task": "Build", "next": "done"},
                "done": {"task": "Done", "terminal": True},
                "__proto__": {"task": "Inject", "next": "build"},
            },
        }
        with pytest.raises(ValueError, match="__proto__"):
            workflow_from_dict(data)


class TestJsonFileLoading:
    def test_load_from_json_file(self):
        data = {
            "name": "file-test",
            "start": "build",
            "nodes": {"build": {"task": "Build", "next": "done"},
                      "done": {"task": "Done", "terminal": True}},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            fpath = f.name

        try:
            wf = load_workflow_from_json(fpath)
            assert wf.name == "file-test"
            assert wf.source_path == fpath
        finally:
            Path(fpath).unlink(missing_ok=True)


class TestDiscoverWorkflows:
    def test_discover_json_and_yaml(self, tmp_path):
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        (wf_dir / "wf1.yaml").write_text("name: yaml-flow\nstart: build\nnodes:\n  build:\n    task: Build\n    terminal: true\n")
        (wf_dir / "wf2.json").write_text('{"name": "json-flow", "start": "build", "nodes": {"build": {"task": "Build", "terminal": true}}}')
        (wf_dir / "ignore.txt").write_text("not a workflow")

        paths = discover_workflows(tmp_path)
        names = [Path(p).stem for p in paths]
        assert "wf1" in names
        assert "wf2" in names
        assert "ignore" not in names
