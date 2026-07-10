"""Tests for state machine (gate-aware transitions, verdict routing, eval tracking)."""

from fleet_agent.engine.state_machine import get_state_machine, StateMachine
from fleet_agent.engine.workflow_loader import workflow_from_dict


def _reset_sm():
    from fleet_agent.engine import state_machine as sm_mod
    from fleet_agent.engine import sqlite_store as store_mod
    store_mod._store = None
    sm_mod._state_machine = StateMachine()
    return get_state_machine()


class TestGateAwareTransitions:
    def setup_method(self):
        self.sm = _reset_sm()
        data = {
            "name": "gate-test",
            "start": "review",
            "nodes": {
                "review": {
                    "task": "Review",
                    "node_type": "review",
                    "branches_map": {"PASS": "gate", "FAIL": "review", "ITERATE": "review"},
                },
                "gate": {
                    "task": "Gate check",
                    "node_type": "gate",
                    "branches_map": {"PASS": None, "FAIL": "review"},
                },
            },
        }
        wf = workflow_from_dict(data)
        self.sm._store.save_workflow(wf)

    def test_next_with_verdict_passes(self):
        self.sm.start("gate-test")
        instance = self.sm.next(verdict="PASS")
        assert instance is not None
        assert instance.current_node == "gate"

    def test_next_with_verdict_fail_loops(self):
        self.sm.start("gate-test")
        instance = self.sm.next(verdict="FAIL")
        assert instance is not None
        assert instance.current_node == "review"
        assert instance.last_verdict == "FAIL"
        assert len(instance.gate_results) == 1

    def test_next_with_verdict_iterate(self):
        self.sm.start("gate-test")
        instance = self.sm.next(verdict="ITERATE")
        assert instance.current_node == "review"
        assert instance.last_verdict == "ITERATE"

    def test_next_with_evals_in_history(self):
        self.sm.start("gate-test")
        evals = [
            {"role": "security", "findings": [
                {"severity": "warning", "message": "Missing input validation"},
            ]},
            {"role": "frontend", "findings": [
                {"severity": "suggestion", "message": "Consider ARIA labels"},
            ]},
        ]
        instance = self.sm.next(verdict="PASS", evals=evals)
        assert instance is not None
        assert len(instance.history) == 1
        entry = instance.history[0]
        assert entry["verdict"] == "PASS"
        assert len(entry["evals"]) == 2
        assert entry["evals"][0]["role"] == "security"

    def test_gate_results_tracking(self):
        self.sm.start("gate-test")
        self.sm.next(verdict="FAIL")
        self.sm.next(verdict="PASS")
        gate_results = self.sm.get_gate_results()
        assert len(gate_results) == 2
        assert gate_results[0]["verdict"] == "FAIL"
        assert gate_results[1]["verdict"] == "PASS"

    def test_gate_to_terminal(self):
        self.sm.start("gate-test")
        self.sm.next(verdict="PASS")  # review→gate
        instance = self.sm.next(verdict="PASS")  # gate→null (terminal)
        assert instance is None  # archived

    def test_get_last_verdict(self):
        self.sm.start("gate-test")
        assert self.sm.get_last_verdict() is None
        self.sm.next(verdict="FAIL")
        assert self.sm.get_last_verdict() == "FAIL"


class TestNodeTypes:
    def test_get_current_node_type(self):
        sm = _reset_sm()
        data = {
            "name": "typed-flow",
            "start": "review",
            "nodes": {
                "review": {
                    "task": "Review",
                    "node_type": "review",
                    "branches_map": {"PASS": "build"},
                },
                "build": {"task": "Build", "node_type": "build", "next": "done"},
                "done": {"task": "Done", "terminal": True},
            },
        }
        wf = workflow_from_dict(data)
        sm._store.save_workflow(wf)
        sm.start("typed-flow")
        assert sm.get_current_node_type() == "review"
        sm.next(verdict="PASS")
        assert sm.get_current_node_type() == "build"

    def test_node_type_defaults_to_build(self):
        sm = _reset_sm()
        data = {
            "name": "default-flow",
            "start": "build",
            "nodes": {"build": {"task": "Build", "next": "done"},
                      "done": {"task": "Done", "terminal": True}},
        }
        wf = workflow_from_dict(data)
        sm._store.save_workflow(wf)
        sm.start("default-flow")
        assert sm.get_current_node_type() == "build"
