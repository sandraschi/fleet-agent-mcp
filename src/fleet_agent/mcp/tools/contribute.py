"""Autonomous contribution tool — Fritz finds issues, files, fixes, and PRs without hand-holding.

One tool that orchestrates the full pipeline:
  inspect -> issue -> branch -> fix -> commit -> push -> PR
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from ...llm_client import chat_completion
from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.contribute")

REPOS_ROOT = Path("D:/Dev/repos")
FRITZ_MCP = "http://127.0.0.1:10996/mcp/"
H = {"Accept": "application/json, text/event-stream"}


def _sh(args: list[str], cwd: str | None = None, timeout: int = 60) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.stdout.strip()
    except Exception as e:
        return f"<error: {e}>"


def _mcp(tool: str, args: dict) -> dict:
    """Call a Fritz MCP tool. Falls back to dict with error."""
    import httpx
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool, "arguments": args},
        "id": 1,
    }
    try:
        r = httpx.post(FRITZ_MCP, json=payload, headers=H, timeout=180)
        r.raise_for_status()
        for line in r.text.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:]).get("result", {}).get("structuredContent", {})
        return {"error": "no data"}
    except Exception as e:
        return {"error": str(e)}


def _pick_lint_target(repo_path: str, severity: str = "S701,S110,E722,F401") -> dict | None:
    """Run ruff, pick the most impactful fix. Returns {file, line, code, old, new} or None."""
    rules = severity.split(",")
    for rule in rules:
        out = _sh(
            ["C:/Users/sandr/AppData/Local/Programs/Python/Python313/Scripts/ruff.exe", "check", repo_path, "--select", rule, "--output-format", "json"],
            timeout=30,
        )
        if not out or out.startswith("<error"):
            continue
        try:
            findings = json.loads(out)
        except json.JSONDecodeError:
            continue
        if findings:
            f = findings[0]
            return {
                "file": f.get("filename", ""),
                "line": f.get("location", {}).get("row", 0),
                "code": f.get("code", rule),
                "message": f.get("message", ""),
                "fix": f.get("fix"),
            }
    return None


def _pick_fix_strategy(findings: list[dict], repo_path: str) -> dict | None:
    """Analyze lint findings and pick the best fix to make."""
    for rule in ["S701", "S110", "E722", "F401", "UP006"]:
        for f in findings:
            if f.get("code") == rule:
                return {"file": f["filename"], "code": rule, "message": f.get("message", "")}
    return None


@mcp.tool(version="0.1.0")
async def fritz_contribute(
    repo_url: Annotated[str, Field(description="Full GitHub repo URL to contribute to")],
    dry_run: Annotated[bool, Field(description="If true, inspect and plan but don't create PR")] = False,
) -> dict[str, Any]:
    """Autonomous contribution: inspect repo, find issue, file issue, fix, commit, PR.

    Fritz clones the repo, runs ruff to find lint errors, picks the most
    impactful one, files a GitHub issue, creates a branch, applies the fix
    via file_edit, commits, pushes, and opens a PR — all without hand-holding.

    ## Return Format
    {"success": bool, "steps": [...], "issue_url": str, "pr_url": str, "message": str}

    ## Examples
    fritz_contribute(repo_url="https://github.com/StephanSchipal/edge-bookmark-mcp-server")
    """
    steps = []
    repo_name = repo_url.rstrip("/").split("/")[-1]
    owner = repo_url.rstrip("/").split("/")[-2]
    work_dir = REPOS_ROOT / f"{repo_name}-work"

    def step(name: str, result: Any):
        steps.append({"step": name, "result": str(result)[:200]})
        logger.info("  %s: %s", name, str(result)[:100])

    # 1. Clone
    step("clone", f"Cloning {repo_url}")
    _sh(["rmdir", "/s", "/q", str(work_dir)], shell=True)
    _sh(["git", "clone", repo_url, str(work_dir)], timeout=120)
    step("cloned", work_dir.name)

    # 2. Run ruff to find issues
    step("ruff", "Scanning for lint errors...")
    out = _sh(
        ["C:/Users/sandr/AppData/Local/Programs/Python/Python313/Scripts/ruff.exe", "check", str(work_dir / "src"), "--select", "S701,S110,E722,F401", "--output-format", "json"],
        timeout=30,
    )
    findings = json.loads(out) if out and not out.startswith("<error") else []
    step("findings", f"{len(findings)} issues found")

    if not findings:
        return {"success": True, "steps": steps, "message": "No issues found."}

    # 3. Pick best target
    target = _pick_fix_strategy(findings, str(work_dir))
    if not target:
        return {"success": True, "steps": steps, "message": "No suitable fix target found."}

    file_path = target["file"]
    code = target["code"]
    msg = target["message"]
    step("target", f"{code} in {file_path}")

    # 4. Compute fix via LLM
    step("plan", "Computing fix...")
    sys_prompt = (
        f"You are fixing a {code} lint error in {file_path}.\n"
        f"Error: {msg}\n\n"
        f"Read the file content and determine the EXACT old_string and new_string "
        f"for a file_edit call (exact string replacement).\n"
        f"Output JSON: {{\"old_string\": \"...\", \"new_string\": \"...\", \"title\": \"...\", \"issue_body\": \"...\"}}"
    )
    (work_dir / "src").is_dir()  # ensure path exists
    file_content = Path(file_path).read_text(encoding="utf-8")[:2000]
    try:
        llm_result = await chat_completion([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"File content:\n```\n{file_content}\n```\n\nThe error is on a specific line. Output the fix JSON."},
        ])
        fix_spec = json.loads(llm_result)
    except Exception as e:
        return {"success": False, "steps": steps, "message": f"LLM fix planning failed: {e}"}

    old_str = fix_spec.get("old_string", "")
    new_str = fix_spec.get("new_string", "")
    title = fix_spec.get("title", f"fix: {code} lint error")
    issue_body = fix_spec.get("issue_body", f"Found by ruff: {msg}")

    if not old_str or not new_str:
        return {"success": False, "steps": steps, "message": "LLM returned incomplete fix spec"}

    # 5. File issue via gh
    issue_url = _sh([
        "gh", "issue", "create", "--repo", f"{owner}/{repo_name}",
        "--title", title[:80],
        "--body", issue_body[:500],
        "--label", "bug",
    ], timeout=15)
    step("issue", issue_url)

    # 6. Create branch
    branch = f"fix/{code.lower()}"
    _sh(["git", "checkout", "-b", branch], cwd=str(work_dir))
    step("branch", branch)

    # 7. Apply fix via file_edit
    fix_result = _mcp("file_edit", {
        "path": file_path.replace("\\", "/"),
        "old_string": old_str,
        "new_string": new_str,
    })
    step("fix", fix_result.get("verified", fix_result.get("success", False)))

    if not fix_result.get("verified"):
        return {"success": False, "steps": steps, "message": f"file_edit failed: {fix_result}"}

    # 8. Commit
    _sh(["git", "add", "-A"], cwd=str(work_dir))
    _sh(["git", "commit", "-m", title[:72]], cwd=str(work_dir))
    step("committed", "ok")

    # 9. Push to fork
    _sh(["gh", "repo", "fork", repo_url, "--clone=false"], timeout=15)
    _sh(["git", "remote", "add", "fork", f"https://github.com/sandraschi/{repo_name}.git"], cwd=str(work_dir))
    _sh(["git", "push", "fork", branch, "--force"], cwd=str(work_dir), timeout=30)
    step("pushed", branch)

    # 10. PR
    if not dry_run:
        pr_url = _sh([
            "gh", "pr", "create", "--repo", f"{owner}/{repo_name}",
            "--title", title[:80],
            "--body", issue_body[:500],
            "--head", f"sandraschi:{branch}",
            "--base", "main",
        ], timeout=15)
        step("pr", pr_url or "PR created")
    else:
        pr_url = None
        step("pr", "dry run - skipped")

    return {
        "success": True,
        "steps": steps,
        "issue_url": issue_url or "",
        "pr_url": pr_url or "",
        "message": f"Contribution pipeline complete. {len(findings)} issues found, fixed {code}.",
    }
