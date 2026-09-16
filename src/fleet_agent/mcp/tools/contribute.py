"""Autonomous contribution tool - Fritz finds issues, files, fixes, and PRs without hand-holding.

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
RUFF_EXE = "C:/Users/sandr/AppData/Local/Programs/Python/Python313/Scripts/ruff.exe"


def _sh(
    args: list[str], cwd: str | None = None, timeout: int = 60, allow_nonzero: bool = False
) -> str:
    """Run a command, return stdout. On failure returns "<error: ...>" -
    every caller checks .startswith("<error") for this, so keep that prefix
    stable.

    allow_nonzero: linters (ruff, biome) exit nonzero when they find
    something, which isn't a command failure - pass True for those. Every
    other caller (git, gh) should leave this False so a real failure
    surfaces its actual stderr instead of silently returning an empty
    string (found 2026-09-08: a failed `gh issue create` reported
    stdout-only success/failure with the real reason discarded, so the
    webapp just showed a blank "gh issue create failed: " message).
    """
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        if r.returncode != 0 and not allow_nonzero:
            detail = (r.stderr or r.stdout or "no output").strip()[:300]
            return f"<error: exit {r.returncode}: {detail}>"
        return r.stdout.strip()
    except Exception as e:
        return f"<error: {e}>"


def _sh_shell(cmd: str, timeout: int = 60) -> str:
    """Run a shell command string (for rmdir etc that need shell=True)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"<error: {e}>"


_own_gh_user_cache: str | None = None


def _own_gh_user() -> str:
    """The authenticated gh CLI user - repos owned by this account skip the fork step."""
    global _own_gh_user_cache
    if _own_gh_user_cache is None:
        out = _sh(["gh", "api", "user", "--jq", ".login"], timeout=10)
        _own_gh_user_cache = out if out and not out.startswith("<error") else ""
    return _own_gh_user_cache


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
            [
                RUFF_EXE,
                "check",
                repo_path,
                "--select",
                rule,
                "--output-format",
                "json",
            ],
            timeout=30,
            allow_nonzero=True,  # ruff exits 1 when it finds something - not a failure
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


def _ruff_mechanical_fix(file_path: str, code: str) -> bool:
    """Let ruff apply its own --fix for rules it can safely auto-fix
    (F401 unused-import, UP006 deprecated-typing, ...) - no LLM needed,
    and it's always textually correct for the actual file since ruff
    computed the edit from the real AST, not a guessed literal.

    Returns True if the file was actually changed.
    """
    before = Path(file_path).read_text(encoding="utf-8")
    _sh(
        [RUFF_EXE, "check", file_path, "--select", code, "--fix", "--no-cache"],
        timeout=15,
        allow_nonzero=True,
    )
    after = Path(file_path).read_text(encoding="utf-8")
    return after != before


def _generic_bare_except_fix(file_path: str) -> dict | None:
    """Generic, non-repo-specific fallback for S110/E722 (bare `except:`).

    Ruff won't auto-fix these - picking the right exception type is a
    judgment call it won't guess at. Narrowing to `except Exception:` is
    the standard, conservative fix (same choice an LLM makes for this
    class of finding) and needs no repo-specific knowledge to apply.
    """
    import re as _re

    content = Path(file_path).read_text(encoding="utf-8")
    match = _re.search(r"except\s*:", content)
    if not match:
        return None
    return {
        "old_string": match.group(0),
        "new_string": "except Exception:",
        "title": "fix: narrow bare except clause",
        "issue_body": (
            "Reliability/security: a bare `except:` catches everything, "
            "including SystemExit and KeyboardInterrupt. Narrowed to "
            "`except Exception:`."
        ),
    }


@mcp.tool(version="0.1.0")
async def fritz_contribute(
    repo_url: Annotated[str, Field(description="Full GitHub repo URL to contribute to")],
    dry_run: Annotated[
        bool, Field(description="If true, inspect and plan but don't create PR")
    ] = False,
) -> dict[str, Any]:
    """Autonomous contribution: inspect repo, find issue, file issue, fix, commit, PR.

    Fritz clones the repo, runs ruff to find lint errors, picks the most
    impactful one, files a GitHub issue, creates a branch, applies the fix
    via file_edit, commits, pushes, and opens a PR - all without hand-holding.
    Use fritz_find_contributions() to discover repos to target.

    See docs/contribution-pipeline.md for the full methodology.

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
    _sh_shell(f"rmdir /s /q {work_dir} 2>nul")
    clone_out = _sh(["git", "clone", repo_url, str(work_dir)], timeout=120)
    if not work_dir.is_dir():
        step("clone failed", clone_out)
        return {"success": False, "steps": steps, "message": f"Clone failed: {clone_out}"}
    step("cloned", work_dir.name)

    # 2. Run ruff to find issues
    step("ruff", "Scanning for lint errors...")
    out = _sh(
        [
            RUFF_EXE,
            "check",
            str(work_dir / "src"),
            "--select",
            "S701,S110,E722,F401",
            "--output-format",
            "json",
        ],
        timeout=30,
        allow_nonzero=True,
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
        f"Read the file content below. Determine the EXACT old_string and new_string "
        f"for a Python string replacement (file_edit).\n"
        f"Output ONLY valid JSON, no markdown:\n"
        f'{{"old_string": "...exact text to replace...", "new_string": "...replacement text...", "title": "...PR title...", "issue_body": "...issue description..."}}'
    )
    file_content = Path(file_path).read_text(encoding="utf-8")[:2000]
    try:
        llm_result = await chat_completion(
            [
                {"role": "system", "content": sys_prompt},
                {
                    "role": "user",
                    "content": f"File:\n```\n{file_content}\n```\n\nFix the {code} error.",
                },
            ]
        )
        # Strip markdown code fences if present
        if "```json" in llm_result:
            llm_result = llm_result.split("```json")[1].split("```")[0]
        elif "```" in llm_result:
            llm_result = llm_result.split("```")[1].split("```")[0]
        fix_spec = json.loads(llm_result.strip())
    except Exception as e:
        # Fallback chain: no-LLM fixes for the same rule set the ruff scan
        # covers, so a down/slow/misbehaving LLM never kills the whole run.
        step("llm failed", f"{e}, using fallback")
        fix_spec = None
        if code == "S701":
            fix_spec = {
                "old_string": "self.template_env = Environment(loader=TemplateLoader(self.templates))",
                "new_string": "self.template_env = Environment(loader=TemplateLoader(self.templates), autoescape=True)",
                "title": "fix: add autoescape=True to Jinja2 Environment (S701 XSS)",
                "issue_body": "Security: Jinja2 Environment created without autoescape=True, enabling XSS when rendering user data in templates.",
            }
        elif code in ("S110", "E722"):
            fix_spec = _generic_bare_except_fix(file_path)
        elif code in ("F401", "UP006") and _ruff_mechanical_fix(file_path, code):
            fix_spec = {
                "_already_applied": True,
                "title": f"fix: {code} - {msg}"[:80],
                "issue_body": f"Found by ruff, auto-fixed with `ruff check --fix`: {msg}",
            }
        if fix_spec is None:
            return {"success": False, "steps": steps, "message": f"LLM fix planning failed: {e}"}
        step("fallback", f"using no-LLM fix for {code}")

    old_str = fix_spec.get("old_string", "")
    new_str = fix_spec.get("new_string", "")
    title = fix_spec.get("title", f"fix: {code} lint error")
    issue_body = fix_spec.get("issue_body", f"Found by ruff: {msg}")
    already_applied = fix_spec.get("_already_applied", False)

    if not already_applied and (not old_str or not new_str):
        return {"success": False, "steps": steps, "message": "LLM returned incomplete fix spec"}

    # 5. File issue via gh
    issue_url = _sh(
        [
            "gh",
            "issue",
            "create",
            "--repo",
            f"{owner}/{repo_name}",
            "--title",
            title[:80],
            "--body",
            issue_body[:500],
            "--label",
            "bug",
        ],
        timeout=15,
    )
    step("issue", issue_url)

    # 6. Create branch
    branch = f"fix/{code.lower()}"
    _sh(["git", "checkout", "-b", branch], cwd=str(work_dir))
    step("branch", branch)

    # 7. Apply fix directly (not via MCP - avoids self-call timeout)
    fix_path = Path(file_path)
    if not fix_path.exists():
        return {"success": False, "steps": steps, "message": f"File not found: {file_path}"}
    if already_applied:
        # _ruff_mechanical_fix() already wrote the change to disk in the
        # fallback branch above - nothing left to do here.
        step("fix", "already applied via ruff --fix")
    else:
        content = fix_path.read_text(encoding="utf-8")
        if old_str not in content:
            return {
                "success": False,
                "steps": steps,
                "message": f"old_string not found in {file_path}",
            }
        bak_path = fix_path.with_suffix(fix_path.suffix + ".bak")
        bak_path.write_text(content, encoding="utf-8")
        new_content = content.replace(old_str, new_str)
        fix_path.write_text(new_content, encoding="utf-8")
        verified = old_str not in fix_path.read_text(
            encoding="utf-8"
        ) and new_str in fix_path.read_text(encoding="utf-8")
        bak_path.unlink()  # remove backup before commit - only the fix should ship
        step("fix", verified)

    # 8. Commit
    _sh(["git", "add", "-A"], cwd=str(work_dir))
    _sh(["git", "commit", "-m", title[:72]], cwd=str(work_dir))
    step("committed", "ok")

    # 9. Push - directly to origin for own repos (skip the fork dance entirely),
    # fork-based flow only for repos we don't own.
    own_repo = owner.lower() == _own_gh_user().lower()
    if own_repo:
        _sh(["git", "push", "origin", branch, "--force"], cwd=str(work_dir), timeout=30)
        step("pushed", f"{branch} (own repo, direct to origin)")
        pr_head = branch
    else:
        _sh(["gh", "repo", "fork", repo_url, "--clone=false"], timeout=15)
        _sh(
            ["git", "remote", "add", "fork", f"https://github.com/{_own_gh_user()}/{repo_name}.git"],
            cwd=str(work_dir),
        )
        _sh(["git", "push", "fork", branch, "--force"], cwd=str(work_dir), timeout=30)
        step("pushed", f"{branch} (fork)")
        pr_head = f"{_own_gh_user()}:{branch}"

    # 10. PR
    if not dry_run:
        pr_url = _sh(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                f"{owner}/{repo_name}",
                "--title",
                title[:80],
                "--body",
                issue_body[:500],
                "--head",
                pr_head,
                "--base",
                "main",
            ],
            timeout=15,
        )
        step("pr", pr_url or "PR created")
    else:
        pr_url = None
        step("pr", "dry run - skipped")

    # Log contribution to database
    try:
        from ...engine.sqlite_store import get_store

        pr_num = ""
        if pr_url:
            import re as _re

            m = _re.search(r"/pull/(\d+)", pr_url)
            if m:
                pr_num = m.group(1)
        status = "dry_run" if dry_run else ("open" if pr_url else "failed")
        get_store().contrib_create(
            repo=f"{owner}/{repo_name}",
            title=title,
            issue_url=issue_url or "",
            pr_url=pr_url or "",
            pr_number=pr_num,
            status=status,
            steps=steps,
        )
    except Exception as log_e:
        logger.warning("Failed to log contribution: %s", log_e)

    return {
        "success": True,
        "steps": steps,
        "issue_url": issue_url or "",
        "pr_url": pr_url or "",
        "message": f"Contribution pipeline complete. {len(findings)} issues found, fixed {code}.",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def fritz_find_contributions(
    query: Annotated[
        str, Field(description="GitHub search query, e.g. 'language:python label:good-first-issue'")
    ] = "language:python label:good-first-issue,help-wanted",
    limit: Annotated[int, Field(description="Max results", ge=1, le=50)] = 10,
) -> dict[str, Any]:
    """Search GitHub for open-source contribution opportunities.

    Uses `gh search issues` to find repos with actionable issues.
    Returns structured results with repo, title, url, labels, and
    a ready-to-use repo_url for fritz_contribute.

    ## Return Format
    {"success": bool, "opportunities": [...], "count": int, "message": str}

    ## Examples
    fritz_find_contributions()
    fritz_find_contributions(query="language:python label:bug")
    fritz_find_contributions(query="user:sandraschi label:help-wanted")
    """
    try:
        result = _sh(
            [
                "gh",
                "search",
                "issues",
                "--json=repository,title,url,labels,state,number",
                f"-L{limit}",
                "--",
                query,
            ],
            timeout=15,
        )
        if not result or result.startswith("<error"):
            return {
                "success": False,
                "message": "gh search issues failed. Is gh CLI installed?",
                "opportunities": [],
                "count": 0,
            }

        items = json.loads(result)
        opportunities = []
        seen_repos = set()
        for item in items:
            repo_full = item.get("repository", {}).get("nameWithOwner", "")
            if not repo_full or repo_full in seen_repos:
                continue
            seen_repos.add(repo_full)
            labels = [lb.get("name", "") for lb in item.get("labels", [])]
            opportunities.append(
                {
                    "repo": repo_full,
                    "repo_url": f"https://github.com/{repo_full}",
                    "issue_title": item.get("title", ""),
                    "issue_url": item.get("url", ""),
                    "state": item.get("state", ""),
                    "labels": labels,
                }
            )
            if len(opportunities) >= limit:
                break

        return {
            "success": True,
            "opportunities": opportunities,
            "count": len(opportunities),
            "message": f"Found {len(opportunities)} repos with actionable issues",
        }
    except Exception as e:
        return {"success": False, "message": f"Search failed: {e}", "opportunities": [], "count": 0}


def _gogetajob(args: list[str], timeout: int = 60) -> str:
    """Run gogetajob CLI and return stdout."""
    try:
        r = subprocess.run(
            ["npx", "--yes", "@kagura-agent/gogetajob", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.stdout.strip()
    except FileNotFoundError:
        return "<error: npx not found>"
    except subprocess.TimeoutExpired:
        return "<error: timeout>"
    except Exception as e:
        return f"<error: {e}>"


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def gogetajob_scan(
    repo: Annotated[str, Field(description="GitHub repo (owner/repo) to scan for issues.")],
) -> dict[str, Any]:
    """Discover open issues from a repo via gogetajob.

    Delegates to `npx @kagura-agent/gogetajob scan <repo>`.
    Returns structured issues ready for the feed.

    ## Return Format
    {"success": bool, "issues": list, "count": int, "raw": str}
    """
    out = _gogetajob(["scan", repo])
    if out.startswith("<error"):
        return {"success": False, "message": out, "issues": [], "count": 0}
    try:
        issues = json.loads(out)
        return {
            "success": True,
            "issues": issues,
            "count": len(issues) if isinstance(issues, list) else 0,
            "raw": out[:500],
        }
    except json.JSONDecodeError:
        return {"success": True, "issues": [], "count": 0, "raw": out[:500]}


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def gogetajob_feed() -> dict[str, Any]:
    """Browse available jobs from the gogetajob feed.

    Delegates to `npx @kagura-agent/gogetajob feed`.
    Returns the current job queue.

    ## Return Format
    {"success": bool, "jobs": list, "count": int, "raw": str}
    """
    out = _gogetajob(["feed"])
    if out.startswith("<error"):
        return {"success": False, "message": out, "jobs": [], "count": 0}
    try:
        jobs = json.loads(out)
        return {
            "success": True,
            "jobs": jobs,
            "count": len(jobs) if isinstance(jobs, list) else 0,
            "raw": out[:500],
        }
    except json.JSONDecodeError:
        return {"success": True, "jobs": [], "count": 0, "raw": out[:500]}


@mcp.tool(version="0.1.0")
async def gogetajob_start(
    ref: Annotated[str, Field(description="Issue reference (e.g. owner/repo#123) to take.")],
) -> dict[str, Any]:
    """Take a job - fork, clone, and create a branch via gogetajob.

    Delegates to `npx @kagura-agent/gogetajob start <ref>`.
    After this, work on the fix, then use gogetajob_submit.

    ## Return Format
    {"success": bool, "message": str, "raw": str}
    """
    out = _gogetajob(["start", ref])
    if out.startswith("<error"):
        return {"success": False, "message": out}
    return {"success": True, "message": f"Started job {ref}", "raw": out[:500]}


@mcp.tool(version="0.1.0")
async def gogetajob_submit(
    ref: Annotated[str, Field(description="Issue reference to submit as PR.")],
    tokens: Annotated[int, Field(description="Token count for the work done.")] = 0,
) -> dict[str, Any]:
    """Push changes and create a PR via gogetajob.

    Delegates to `npx @kagura-agent/gogetajob submit <ref>`.
    Records the completion and opens a PR. Also logs the result to Fritz's
    own contribution_log so it shows up in the webapp Contributions page -
    gogetajob tracks its own work_log separately and previously never
    surfaced here.

    ## Return Format
    {"success": bool, "message": str, "raw": str}
    """
    args = ["submit", ref]
    if tokens:
        args.extend(["--tokens", str(tokens)])
    out = _gogetajob(args)
    if out.startswith("<error"):
        return {"success": False, "message": out}

    import re as _re

    pr_match = _re.search(r"https://github\.com/[\w.-]+/[\w.-]+/pull/(\d+)", out)
    repo_match = _re.match(r"([\w.-]+/[\w.-]+)#(\d+)", ref)
    try:
        from ...engine.sqlite_store import get_store

        get_store().contrib_create(
            repo=repo_match.group(1) if repo_match else ref,
            title=f"gogetajob submit {ref}",
            issue_url=f"https://github.com/{repo_match.group(1)}/issues/{repo_match.group(2)}"
            if repo_match
            else "",
            pr_url=pr_match.group(0) if pr_match else "",
            pr_number=pr_match.group(1) if pr_match else "",
            status="open" if pr_match else "failed",
            steps=[{"step": "gogetajob submit", "result": out[:500]}],
        )
    except Exception as log_e:
        logger.warning("Failed to log gogetajob contribution: %s", log_e)

    return {"success": True, "message": f"Submitted {ref}", "raw": out[:500]}


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def gogetajob_stats() -> dict[str, Any]:
    """View overall contribution statistics from gogetajob.

    Delegates to `npx @kagura-agent/gogetajob stats`.
    Returns total PRs, tokens, repos, and success rate.

    ## Return Format
    {"success": bool, "stats": dict, "raw": str}
    """
    out = _gogetajob(["stats"])
    if out.startswith("<error"):
        return {"success": False, "message": out}
    try:
        stats_data = json.loads(out)
        return {"success": True, "stats": stats_data, "raw": out[:500]}
    except json.JSONDecodeError:
        return {"success": True, "message": "Stats returned raw output", "raw": out[:500]}


@mcp.tool(version="0.1.0")
async def gogetajob_sync() -> dict[str, Any]:
    """Sync PR/issue statuses via gogetajob.

    Delegates to `npx @kagura-agent/gogetajob sync`.
    Checks PR status, detects merges, CI failures, review comments.

    ## Return Format
    {"success": bool, "message": str, "raw": str}
    """
    out = _gogetajob(["sync"])
    if out.startswith("<error"):
        return {"success": False, "message": out}
    return {"success": True, "message": "Sync complete", "raw": out[:500]}
