"""Code generation and file-write tools for autonomous PR creation.

Generates code via fleet LLM, writes it to disk. Used by the
contribution workflow's implement node.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from ...llm_client import build_system_prompt, chat_completion
from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.codegen")


@mcp.tool(version="0.1.0")
async def code_generate(
    spec: Annotated[str, Field(description="Spec of code to write. Include file name, language, patterns.")],
    repo_path: Annotated[str, Field(description="Absolute path to the repo root")],
    file_path: Annotated[str, Field(description="Relative path from repo root (e.g. src/foo/bar.py)")],
    context: Annotated[str | None, Field(description="Conventions, relevant code, lint rules, etc.")] = None,
) -> dict[str, Any]:
    """Generate code via LLM and write it to the repo.

    Uses the fleet's configured Ollama/LMStudio model. For large
    changes, call multiple times — one file per invocation.

    ## Return Format
    {"success": bool, "file_path": str, "language": str, "lines": int}

    ## Examples
    code_generate(
        spec="Write a Python function that validates email addresses",
        repo_path="D:/Dev/repos/myproject",
        file_path="src/validators/email.py",
        context="Uses pydantic v2, follow existing patterns in src/validators/"
    )
    """
    target = Path(repo_path) / file_path
    target.parent.mkdir(parents=True, exist_ok=True)

    sys_prompt = build_system_prompt()
    lang = Path(file_path).suffix.lstrip(".")

    messages = sys_prompt + [
        {
            "role": "user",
            "content": (
                f"You are writing code for a project at {repo_path}.\n\n"
                f"## File to write\n{file_path}\n\n"
                f"## Spec\n{spec}\n\n"
                + (f"## Context\n{context}\n\n" if context else "")
                + "Output ONLY the code. No explanations, no markdown fences."
            ),
        },
    ]

    try:
        code = await chat_completion(messages)
    except RuntimeError as e:
        return {"success": False, "message": f"LLM call failed: {e}"}

    if not code.strip():
        return {"success": False, "message": "LLM returned empty code"}

    # Strip markdown fences if present
    if code.startswith("```"):
        code = code.split("\n", 1)[-1]
        code = code.rsplit("```", 1)[0]
        code = code.strip()

    target.write_text(code, encoding="utf-8")
    lines = len(code.splitlines())

    logger.info("Generated %s (%d lines) from spec: %s", file_path, lines, spec[:60])

    return {
        "success": True,
        "file_path": str(target),
        "language": lang or "text",
        "lines": lines,
        "message": f"Wrote {lines} lines to {file_path}",
    }


@mcp.tool(version="0.1.0")
async def file_write(
    path: Annotated[str, Field(description="Absolute path to the file to write")],
    content: Annotated[str, Field(description="Full file content")],
    overwrite: Annotated[bool, Field(description="Overwrite if exists")] = True,
) -> dict[str, Any]:
    """Write a file to disk. Creates parent directories if needed.

    Use for direct edits, patches, or when you already have the exact code.

    ## Return Format
    {"success": bool, "path": str, "lines": int, "message": str}

    ## Examples
    file_write(
        path="D:/Dev/repos/myproject/src/main.py",
        content="print('hello')"
    )
    """
    target = Path(path)
    if target.exists() and not overwrite:
        return {"success": False, "message": f"File exists: {path}. Set overwrite=True to replace."}

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    lines = len(content.splitlines())

    logger.info("Wrote %s (%d lines)", path, lines)

    return {
        "success": True,
        "path": str(target),
        "lines": lines,
        "message": f"Wrote {lines} lines to {path}",
    }
