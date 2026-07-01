"""GitHub PR pipeline tools — branch, commit, push, PR creation.

Delegates git operations to git-github-mcp when available,
falls back to subprocess git for local operations.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Annotated, Any

from pydantic import Field

from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.github")

GIT_GITHUB_URL = "http://127.0.0.1:10702/mcp"


def _git(repo_path: str, *args: str) -> str:
    """Run a git command in the repo and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


async def _call_git_server(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Call a tool on git-github-mcp via HTTP."""
    import httpx
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool, "arguments": args},
        "id": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(GIT_GITHUB_URL, json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("git-github-mcp call failed (%s), falling back to local git: %s", tool, e)
        return {"error": str(e)}


@mcp.tool(version="0.1.0")
async def github_create_branch(
    repo_path: Annotated[str, Field(description="Absolute path to the local repo")],
    branch_name: Annotated[str, Field(description="Name for the new branch")],
    base_branch: Annotated[str, Field(description="Branch to fork from")] = "main",
) -> dict[str, Any]:
    """Create a new git branch and check it out.

    ## Return Format
    {"success": bool, "branch": str, "message": str}
    """
    try:
        _git(repo_path, "checkout", base_branch)
        _git(repo_path, "pull", "origin", base_branch)
        _git(repo_path, "checkout", "-b", branch_name)
        msg = f"Created branch {branch_name} from {base_branch}"
        return {"success": True, "branch": branch_name, "message": msg}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}


@mcp.tool(version="0.1.0")
async def github_commit(
    repo_path: Annotated[str, Field(description="Absolute path to the local repo")],
    message: Annotated[str, Field(description="Commit message")],
    files: Annotated[list[str] | None, Field(description="Files to stage (omit for all changed)")] = None,
) -> dict[str, Any]:
    """Stage files and commit with a message.

    ## Return Format
    {"success": bool, "commit_hash": str, "files_changed": int, "message": str}
    """
    try:
        if files:
            _git(repo_path, "add", *files)
        else:
            _git(repo_path, "add", "-A")
        _git(repo_path, "commit", "-m", message)
        sha = _git(repo_path, "rev-parse", "HEAD")
        count = (
            len(_git(repo_path, "diff", "--cached", "--name-only").splitlines())
            if not files else len(files)
        )
        msg = f"Committed {count} files: {sha[:8]}"
        return {"success": True, "commit_hash": sha, "files_changed": count, "message": msg}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}


@mcp.tool(version="0.1.0")
async def github_push(
    repo_path: Annotated[str, Field(description="Absolute path to the local repo")],
    remote: Annotated[str, Field(description="Remote name")] = "origin",
    branch: Annotated[str | None, Field(description="Branch to push. Omit for current.")] = None,
    force: Annotated[bool, Field(description="Force push")] = False,
) -> dict[str, Any]:
    """Push commits to remote.

    ## Return Format
    {"success": bool, "message": str}
    """
    try:
        args = ["push", remote]
        if branch:
            args.append(branch)
        if force:
            args.append("--force")
        _git(repo_path, *args)
        return {"success": True, "message": f"Pushed to {remote}/{branch or 'current'}"}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}


@mcp.tool(version="0.1.0")
async def github_create_pr(
    owner: Annotated[str, Field(description="Repository owner (user or org)")],
    repo: Annotated[str, Field(description="Repository name")],
    title: Annotated[str, Field(description="PR title")],
    body: Annotated[str, Field(description="PR description body")],
    head: Annotated[str, Field(description="Source branch name")],
    base: Annotated[str, Field(description="Target branch")] = "main",
    draft: Annotated[bool, Field(description="Create as draft PR")] = False,
) -> dict[str, Any]:
    """Create a pull request on GitHub.

    Delegates to git-github-mcp if available. Falls back to gh CLI.

    ## Return Format
    {"success": bool, "pr_url": str, "pr_number": int, "message": str}

    ## Examples
    github_create_pr(
        owner="sandraschi",
        repo="grandorgue-mcp",
        title="Fix --load CLI flag",
        body="Adds --load <path> for loading organs at startup.",
        head="feature/load-flag",
        base="main"
    )
    """
    # Try git-github-mcp first
    result = await _call_git_server("github_ops", {
        "operation": "pr_create",
        "owner": owner,
        "repo": repo,
        "title": title,
        "body": body,
        "head_branch": head,
        "base_branch": base,
        "draft": draft,
    })
    if "error" not in result:
        return {
            "success": True,
            "pr_url": "",
            "pr_number": 0,
            "message": "PR created via git-github-mcp",
        }

    # Fallback: gh CLI
    try:
        import subprocess
        cmd = [
            "gh", "pr", "create",
            "--repo", f"{owner}/{repo}",
            "--title", title,
            "--body", body,
            "--head", head,
            "--base", base,
        ]
        if draft:
            cmd.append("--draft")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return {"success": False, "message": f"gh CLI failed: {r.stderr.strip()}"}
        url = r.stdout.strip()
        return {"success": True, "pr_url": url, "message": f"PR created: {url}"}
    except FileNotFoundError:
        msg = "gh CLI not installed. Install it or ensure git-github-mcp is running."
        return {"success": False, "message": msg}


@mcp.tool(version="0.1.0")
async def github_list_prs(
    owner: Annotated[str, Field(description="Repository owner")],
    repo: Annotated[str, Field(description="Repository name")],
    state: Annotated[str, Field(description="PR state: open, closed, all")] = "open",
    limit: Annotated[int, Field(description="Max PRs to return")] = 10,
) -> dict[str, Any]:
    """List pull requests with title, author, status, and mergeable state.

    ## Return Format
    {"success": bool, "prs": [...], "total": int}

    ## Examples
    github_list_prs(owner="sandraschi", repo="fritz-test")
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", f"{owner}/{repo}", "--state", state,
             "--json", "number,title,author,state,mergeable,headRefName,baseRefName,createdAt",
             "--limit", str(limit)],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            prs = json.loads(result.stdout)
            return {"success": True, "prs": prs, "total": len(prs)}
        return {"success": False, "message": f"gh CLI: {result.stderr.strip()}"}
    except FileNotFoundError:
        return {"success": False, "message": "gh CLI not installed"}
    except json.JSONDecodeError as e:
        return {"success": False, "message": f"gh CLI returned invalid JSON: {e}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool(version="0.1.0")
async def github_get_pr(
    owner: Annotated[str, Field(description="Repository owner")],
    repo: Annotated[str, Field(description="Repository name")],
    number: Annotated[int, Field(description="PR number")],
) -> dict[str, Any]:
    """Get detailed PR info: title, body, files changed, status checks, diff.

    ## Return Format
    {"success": bool, "pr": dict, "files": [...], "diff": str, "message": str}

    ## Examples
    github_get_pr(owner="sandraschi", repo="fritz-test", number=1)
    """
    try:
        # Get PR info
        r = subprocess.run(
            ["gh", "pr", "view", str(number), "--repo", f"{owner}/{repo}",
             "--json", "number,title,body,state,mergeable,headRefName,baseRefName,author,createdAt,mergedBy,reviews"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return {"success": False, "message": f"gh CLI: {r.stderr.strip()}"}
        pr_info = json.loads(r.stdout)

        # Get changed files
        r2 = subprocess.run(
            ["gh", "pr", "diff", str(number), "--repo", f"{owner}/{repo}", "--name-only"],
            capture_output=True, text=True, timeout=15,
        )
        files = [f for f in r2.stdout.strip().splitlines() if f.strip()] if r2.returncode == 0 else []

        # Get full diff
        r3 = subprocess.run(
            ["gh", "pr", "diff", str(number), "--repo", f"{owner}/{repo}"],
            capture_output=True, text=True, timeout=15,
        )
        diff = r3.stdout[:5000] if r3.returncode == 0 else ""

        return {
            "success": True,
            "pr": pr_info,
            "files": files,
            "diff": diff,
            "message": f"PR #{number}: {pr_info.get('title', '')}",
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool(version="0.1.0")
async def github_review_pr(
    owner: Annotated[str, Field(description="Repository owner")],
    repo: Annotated[str, Field(description="Repository name")],
    number: Annotated[int, Field(description="PR number")],
    action: Annotated[str, Field(description="Review action: approve, request-changes, comment")],
    body: Annotated[str, Field(description="Review comment body")] = "",
) -> dict[str, Any]:
    """Review a pull request: approve, request changes, or comment.

    ## Return Format
    {"success": bool, "message": str}

    ## Examples
    github_review_pr(owner="sandraschi", repo="fritz-test", number=1, action="approve", body="LGTM")
    github_review_pr(owner="sandraschi", repo="fritz-test", number=1, action="request-changes", body="Fix formatting")
    """
    try:
        cmd = ["gh", "pr", "review", str(number), "--repo", f"{owner}/{repo}", "--approve"]
        if action == "request-changes":
            cmd = ["gh", "pr", "review", str(number), "--repo", f"{owner}/{repo}", "--request-changes"]
        elif action == "comment":
            cmd = ["gh", "pr", "review", str(number), "--repo", f"{owner}/{repo}", "--comment"]
        if body:
            cmd.extend(["--body", body])
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return {"success": False, "message": f"Review failed: {r.stderr.strip()}"}
        return {"success": True, "message": f"Review '{action}' submitted on PR #{number}"}
    except FileNotFoundError:
        return {"success": False, "message": "gh CLI not installed"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool(version="0.1.0")
async def github_merge_pr(
    owner: Annotated[str, Field(description="Repository owner")],
    repo: Annotated[str, Field(description="Repository name")],
    number: Annotated[int, Field(description="PR number")],
    method: Annotated[str, Field(description="Merge method: merge, squash, rebase")] = "squash",
) -> dict[str, Any]:
    """Merge a pull request.

    ## Return Format
    {"success": bool, "message": str}

    ## Examples
    github_merge_pr(owner="sandraschi", repo="fritz-test", number=1)
    """
    try:
        cmd = ["gh", "pr", "merge", str(number), "--repo", f"{owner}/{repo}", f"--{method}"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return {"success": False, "message": f"Merge failed: {r.stderr.strip()}"}
        return {"success": True, "message": f"PR #{number} merged ({method})"}
    except FileNotFoundError:
        return {"success": False, "message": "gh CLI not installed"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool(version="0.1.0")
async def github_status(
    repo_path: Annotated[str, Field(description="Absolute path to the local repo")],
) -> dict[str, Any]:
    """Check git status of a repo — branch, changes, ahead/behind.

    ## Return Format
    {"success": bool, "branch": str, "changes": int, "ahead": int, "message": str}
    """
    try:
        branch = _git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
        status_output = _git(repo_path, "status", "--porcelain")
        lines = [x for x in status_output.splitlines() if x.strip()]
        changes = len(lines)
        msg = f"On {branch}, {changes} uncommitted changes"
        return {"success": True, "branch": branch, "changes": changes, "message": msg}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}
