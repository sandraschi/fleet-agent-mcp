"""Finite state machine for workflow execution.

Inspired by kagura-agent/flowforge: YAML-defined, SQLite-persisted,
enforced step-by-step execution that prevents agents from skipping steps.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .sqlite_store import get_store
from .workflow_loader import Workflow, load_workflow


@dataclass
class WorkflowInstance:
    workflow_name: str
    current_node: str
    started_at: str
    updated_at: str
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "current_node": self.current_node,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "history": self.history,
        }


class StateMachine:
    def __init__(self) -> None:
        self._store = get_store()

    def register_workflow(self, yaml_path: str) -> Workflow:
        wf = load_workflow(yaml_path)
        self._store.save_workflow(wf)
        return wf

    def list_workflows(self) -> list[dict[str, Any]]:
        return self._store.list_workflows()

    def get_workflow(self, name: str) -> Workflow | None:
        return self._store.get_workflow(name)

    def start(self, workflow_name: str) -> WorkflowInstance:
        wf = self._store.get_workflow(workflow_name)
        if wf is None:
            raise ValueError(
                f"Workflow '{workflow_name}' not registered. Use workflow_define first."
            )

        now = datetime.now(UTC).isoformat()
        instance = WorkflowInstance(
            workflow_name=workflow_name,
            current_node=wf.start,
            started_at=now,
            updated_at=now,
        )
        self._store.save_instance(instance)
        return instance

    def status(self) -> WorkflowInstance | None:
        return self._store.get_active_instance()

    def list_active(self) -> list[dict[str, Any]]:
        return self._store.list_active_instances()

    def next(self, branch: int | None = None) -> WorkflowInstance | None:
        instance = self._store.get_active_instance()
        if instance is None:
            return None

        wf = self._store.get_workflow(instance.workflow_name)
        if wf is None:
            return None

        node = wf.nodes.get(instance.current_node)
        if node is None:
            return None

        next_node: str | None = None
        branch_label: str | None = None

        if node.terminal:
            self._store.archive_instance(instance)
            return None

        if node.branches and branch is not None:
            if 0 <= branch < len(node.branches):
                next_node = node.branches[branch].next
                branch_label = node.branches[branch].condition
        elif node.next_node:
            next_node = node.next_node

        if next_node is None:
            return None

        history_entry = {
            "from_node": instance.current_node,
            "to_node": next_node,
            "branch": branch_label,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        instance.history.append(history_entry)
        instance.current_node = next_node
        instance.updated_at = datetime.now(UTC).isoformat()

        self._store.save_instance(instance)
        return instance

    def log(self) -> list[dict[str, Any]]:
        instance = self._store.get_active_instance()
        if instance is None:
            return []
        return instance.history

    def reset(self) -> WorkflowInstance | None:
        instance = self._store.get_active_instance()
        if instance is None:
            return None
        self._store.archive_instance(instance)
        return self.start(instance.workflow_name)

    def get_current_task(self) -> str | None:
        instance = self._store.get_active_instance()
        if instance is None:
            return None
        wf = self._store.get_workflow(instance.workflow_name)
        if wf is None:
            return None
        node = wf.nodes.get(instance.current_node)
        if node is None:
            return None
        return node.task

    def get_current_branches(self) -> list[dict[str, Any]] | None:
        instance = self._store.get_active_instance()
        if instance is None:
            return None
        wf = self._store.get_workflow(instance.workflow_name)
        if wf is None:
            return None
        node = wf.nodes.get(instance.current_node)
        if node is None:
            return None
        if not node.branches:
            return None
        return [
            {"index": i, "condition": b.condition, "next": b.next}
            for i, b in enumerate(node.branches)
        ]

    def execution_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._store.get_execution_log(limit)


_state_machine: StateMachine | None = None


def get_state_machine() -> StateMachine:
    global _state_machine
    if _state_machine is None:
        _state_machine = StateMachine()
    return _state_machine
