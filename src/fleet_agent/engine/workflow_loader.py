"""YAML workflow loader.

Workflows are auto-discovered from:
  1. ./workflows/ in the project directory
  2. ~/.fleet-agent/workflows/ in the user home directory
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Branch:
    condition: str
    next: str


@dataclass
class WorkflowNode:
    task: str
    next_node: str | None = None
    branches: list[Branch] = field(default_factory=list)
    terminal: bool = False

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"task": self.task}
        if self.next_node:
            d["next"] = self.next_node
        if self.branches:
            d["branches"] = [
                {"condition": b.condition, "next": b.next} for b in self.branches
            ]
        if self.terminal:
            d["terminal"] = True
        return d


@dataclass
class Workflow:
    name: str
    description: str
    start: str
    nodes: dict[str, WorkflowNode]
    source_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "start": self.start,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "source_path": self.source_path,
        }


def load_workflow(yaml_path: str) -> Workflow:
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {yaml_path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    name = data.get("name", path.stem)
    description = data.get("description", "")
    start = data["start"]
    nodes_data = data.get("nodes", {})

    nodes: dict[str, WorkflowNode] = {}
    for node_name, node_config in nodes_data.items():
        task = node_config.get("task", "")
        next_node = node_config.get("next")
        terminal = node_config.get("terminal", False)

        branches: list[Branch] = []
        raw_branches = node_config.get("branches", [])
        if raw_branches:
            for b in raw_branches:
                branches.append(Branch(condition=b["condition"], next=b["next"]))

        nodes[node_name] = WorkflowNode(
            task=task.strip(),
            next_node=next_node,
            branches=branches,
            terminal=terminal,
        )

    return Workflow(
        name=name,
        description=description,
        start=start,
        nodes=nodes,
        source_path=str(path.resolve()),
    )


def discover_workflows(project_root: Path) -> list[str]:
    paths: list[str] = []
    for search_dir in [
        project_root / "workflows",
        Path.home() / ".fleet-agent" / "workflows",
    ]:
        if search_dir.exists():
            for yf in sorted(search_dir.glob("*.yaml")):
                paths.append(str(yf))
            for yf in sorted(search_dir.glob("*.yml")):
                paths.append(str(yf))
    return paths
