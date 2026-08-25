"""Tests for external SKILL.md importer."""

import pytest
from fleet_agent.mcp.tools.memory import _parse_skill_md, import_external_skill


def test_parse_skill_md_with_yaml_frontmatter():
    sample = """---
name: k8s-deployment-debug
description: Steps for diagnosing CrashLoopBackOff
tags: [kubernetes, debug, devops]
---

# K8s Debug Guide

Step 1: Check pod logs.
"""
    meta, body = _parse_skill_md(sample)
    assert meta.get("name") == "k8s-deployment-debug"
    assert meta.get("description") == "Steps for diagnosing CrashLoopBackOff"
    assert meta.get("tags") == ["kubernetes", "debug", "devops"]
    assert "# K8s Debug Guide" in body
    assert "Step 1: Check pod logs." in body


@pytest.mark.asyncio
async def test_import_external_skill(tmp_path):
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        """---
name: test-imported-skill
description: A test skill imported from external source
tags: [test, import-demo]
---

## Action Plan
1. Step one
2. Step two
""",
        encoding="utf-8",
    )

    res = await import_external_skill(file_path=str(skill_file), tags=["custom-tag"])
    assert res["success"] is True
    card = res["card"]
    assert card["title"] == "test-imported-skill"
    assert "type:skill" in card["tags"]
    assert "created_by:import" in card["tags"]
    assert "custom-tag" in card["tags"]
    assert "A test skill imported from external source" in card["content"]
