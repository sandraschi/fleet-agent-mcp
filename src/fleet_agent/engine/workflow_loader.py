"""Workflow loader — YAML + JSON flow templates with mechanical gate support.

Workflows are auto-discovered from:
  1. ./workflows/ in the project directory
  2. ~/.fleet-agent/workflows/ in the user home directory

Supports OPC-style JSON flow templates with node types, gate verdict routing,
and optional contextSchema validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

NodeType = Literal["discussion", "build", "review", "execute", "gate"]

# Node types that require eval artifacts before advancement
GATE_NODE_TYPES: set[NodeType] = {"review", "gate"}


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
    node_type: NodeType | None = None
    branches_map: dict[str, str] = field(default_factory=dict)

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
        if self.node_type:
            d["node_type"] = self.node_type
        if self.branches_map:
            d["branches_map"] = self.branches_map
        return d


@dataclass
class Workflow:
    name: str
    description: str
    start: str
    nodes: dict[str, WorkflowNode]
    source_path: str = ""
    context_schema: dict[str, Any] | None = None
    soft_evidence: bool = False

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "start": self.start,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "source_path": self.source_path,
        }
        if self.context_schema:
            d["context_schema"] = self.context_schema
        if self.soft_evidence:
            d["soft_evidence"] = True
        return d


# ── YAML loader ─────────────────────────────────────────────────────────────


def _build_node(node_name: str, node_config: dict[str, Any]) -> WorkflowNode:
    task = node_config.get("task", "")
    next_node = node_config.get("next")
    terminal = node_config.get("terminal", False)
    node_type_str = node_config.get("node_type")
    node_type: NodeType | None = None
    if node_type_str and node_type_str in ("discussion", "build", "review", "execute", "gate"):
        node_type = node_type_str  # type: ignore[assignment]

    branches: list[Branch] = []
    branches_map: dict[str, str] = {}

    # OPC-style branches_map (verdict → next)
    raw_map = node_config.get("branches_map", {})
    if raw_map:
        for verdict, target in raw_map.items():
            if verdict in ("PASS", "FAIL", "ITERATE", "BLOCKED"):
                branches_map[verdict] = target
                branches.append(Branch(condition=verdict, next=target))

    # YAML-style branches list
    raw_branches = node_config.get("branches", [])
    if raw_branches:
        for b in raw_branches:
            cond = b["condition"]
            target = b["next"]
            branches.append(Branch(condition=cond, next=target))
            if cond in ("PASS", "FAIL", "ITERATE", "BLOCKED"):
                branches_map[cond] = target

    return WorkflowNode(
        task=task.strip(),
        next_node=next_node,
        branches=branches,
        terminal=terminal,
        node_type=node_type,
        branches_map=branches_map,
    )


def load_workflow(yaml_path: str) -> Workflow:
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {yaml_path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return workflow_from_dict(data, source_path=str(path.resolve()))


# ── JSON loader ──────────────────────────────────────────────────────────────

# Valid node types for JSON flow templates
_VALID_NODE_TYPES = frozenset({"discussion", "build", "review", "execute", "gate"})
_RESERVED_NAMES = frozenset({"__proto__", "constructor", "prototype"})


def load_workflow_from_json(json_path: str) -> Workflow:
    """Load an OPC-style JSON flow template.

    Schema:
    ```json
    {
      "name": "my-flow",
      "description": "...",
      "start": "build",
      "nodes": {
        "build": {
          "task": "Implement feature",
          "node_type": "build",
          "next": "review"
        },
        "review": {
          "task": "Review implementation",
          "node_type": "review",
          "branches_map": {"PASS": "gate", "FAIL": "build"}
        },
        "gate": {
          "task": "Final quality check",
          "node_type": "gate",
          "branches_map": {"PASS": null, "FAIL": "build"}
        }
      },
      "limits": {"maxTotalSteps": 20, "maxLoopsPerEdge": 3},
      "context_schema": {...},
      "soft_evidence": false
    }
    ```
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Flow template not found: {json_path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return workflow_from_dict(data, source_path=str(path.resolve()))


def workflow_from_dict(
    data: dict[str, Any],
    source_path: str = "",
) -> Workflow:
    """Construct a Workflow from a parsed dict (YAML or JSON)."""
    name = data.get("name") or data.get("workflow_name", "")
    if not name and source_path:
        name = Path(source_path).stem
    description = data.get("description", "")
    start = data.get("start", "")
    nodes_data = data.get("nodes", {})

    if not start:
        raise ValueError("Workflow must specify a 'start' node")
    if not nodes_data:
        raise ValueError("Workflow must specify 'nodes'")

    # Validate node names for prototype pollution
    for node_name in nodes_data:
        if node_name in _RESERVED_NAMES:
            raise ValueError(f"Invalid node name: '{node_name}'")

    nodes: dict[str, WorkflowNode] = {}
    has_gate = False

    for node_name, node_config in nodes_data.items():
        node = _build_node(node_name, node_config)
        nodes[node_name] = node
        if node.node_type == "gate" or node_config.get("node_type") == "gate":
            has_gate = True

        # Validate node_type
        nt = node_config.get("node_type")
        if nt and nt not in _VALID_NODE_TYPES:
            raise ValueError(f"Invalid node_type '{nt}' in node '{node_name}'")

    # Validate all edge targets
    for node_name, node in nodes.items():
        if node.next_node and node.next_node not in nodes and node.next_node is not None:
            raise ValueError(
                f"Node '{node_name}' has next='{node.next_node}' which does not exist"
            )
        for b in node.branches:
            if b.next not in nodes and b.next is not None:
                raise ValueError(
                    f"Node '{node_name}' branch '{b.condition}' "
                    f"targets '{b.next}' which does not exist"
                )
        for verdict, target in node.branches_map.items():
            if target not in nodes and target is not None:
                raise ValueError(
                    f"Node '{node_name}' '{verdict}' targets '{target}' which does not exist"
                )

    # Parse optional OPC-style fields
    context_schema = data.get("context_schema") or data.get("contextSchema")
    soft_evidence = data.get("soft_evidence") or data.get("softEvidence", False)

    return Workflow(
        name=name,
        description=description,
        start=start,
        nodes=nodes,
        source_path=source_path,
        context_schema=context_schema,
        soft_evidence=soft_evidence,
    )


# ── Discovery ────────────────────────────────────────────────────────────────


def discover_workflows(project_root: Path) -> list[str]:
    paths: list[str] = []
    for search_dir in [
        project_root / "workflows",
        Path.home() / ".fleet-agent" / "workflows",
    ]:
        if search_dir.exists():
            for ext in ("*.yaml", "*.yml", "*.json"):
                for f in sorted(search_dir.glob(ext)):
                    paths.append(str(f))
    return paths
