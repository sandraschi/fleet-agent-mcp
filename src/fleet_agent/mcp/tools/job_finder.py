"""Job-finder: an improved version of gogetajob's issue classification.

gogetajob's classifyIssue() is pure label/keyword matching (see analysis in
memory 2026-09-08) - it never reads the actual issue content, never looks
at comments, and never uses age as a signal despite fetching it. This module
replaces that with real LLM analysis (local models only - see
[[fritz-local-llm-only]]) plus an explicit age/maintainer-engagement signal,
and adds a case gogetajob has no answer for at all: a well-regarded repo
that simply doesn't run ruff/biome, so real problems never become filed
issues in the first place.

Design principles (2026-09-08, Sandra's explicit calls):
- Every analysis decision is logged to analysis_log for later postmortem,
  not just the outcomes we acted on - so "why did Fritz skip this" is
  always answerable later, not just "what did Fritz do."
- Never call a cloud LLM. chat_completion() only ever tries local Ollama/
  LM Studio (see llm_client.py's hardcoded _PROVIDER_CHAIN) - this module
  must never route around that.
- For repos we don't own: analysis is always read-only/report-only. Filing
  an issue or opening a PR on someone else's repo is a separate, explicit
  step a human triggers - never automatic, and never more than one
  self-found issue per repo without a human choosing to continue (see
  _MAX_UNPROMPTED_ISSUES_PER_REPO) - a repo we're a guest in doesn't need
  five issues from us in one visit.
- Friendly, humble tone in anything we file - see FRIENDLY_ISSUE_SYSTEM_PROMPT.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from ...llm_client import chat_completion
from ...settings_store import get_settings_store
from ..registry import mcp
from .contribute import REPOS_ROOT, RUFF_EXE, _own_gh_user, _sh, _sh_shell

logger = logging.getLogger("fleet_agent.tools.job_finder")

# Don't self-file more than this many issues on a repo we don't own in one
# analysis pass, even if we found more. A guest doesn't open five issues on
# the first visit - come back another day, or let a human ask for more.
_MAX_UNPROMPTED_ISSUES_PER_REPO = 1

LINT_MARKERS = {
    "ruff": ["ruff", "[tool.ruff]"],
    "flake8": ["flake8"],
    "eslint": ["eslint"],
    "biome": ["biome"],
}


# ── Step 1: age + maintainer-engagement signal (no LLM, pure heuristic) ──


def compute_age_signal(created_at: str, comments: list[dict]) -> dict[str, Any]:
    """Combine issue age with maintainer engagement into one of four
    quadrants. gogetajob fetches createdAt and comment count but never
    actually uses age for anything - this is the missing piece.
    """
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        age_days = (datetime.now(UTC) - created).days
    except (ValueError, AttributeError):
        age_days = -1

    maintainer_engaged = len(comments) > 0

    if age_days < 0:
        quadrant = "unknown"
    elif age_days <= 30 and not maintainer_engaged:
        quadrant = "fresh_quiet"  # good target
    elif age_days <= 30 and maintainer_engaged:
        quadrant = "fresh_engaged"  # promising, maintainer responsive
    elif age_days > 30 and maintainer_engaged:
        quadrant = "stale_engaged"  # someone's likely already on it - skip
    else:
        quadrant = "stale_quiet"  # possibly abandoned, worth a shot but temper expectations

    return {
        "age_days": age_days,
        "comment_count": len(comments),
        "maintainer_engaged": maintainer_engaged,
        "quadrant": quadrant,
    }


# ── Step 2: real LLM analysis of an existing issue (local model only) ──

_ANALYSIS_SYSTEM_PROMPT = """You are evaluating a GitHub issue to decide whether an AI contributor should attempt to fix it. Be honest and skeptical - most issues are NOT good targets. Consider:

- Is the issue actually well-specified enough to act on, or vague/needs-discussion?
- Does it look like something requiring deep repo-specific context you won't have from just the issue text?
- Do the comments suggest someone (maintainer or another contributor) is already working on it?
- Is the age/quiet-vs-engaged signal given to you consistent with this being abandoned, actively worked, or fresh?

Output ONLY valid JSON, no markdown:
{"tractability": "easy"|"medium"|"hard", "confidence": 0.0-1.0, "reasoning": "1-2 sentences", "likely_duplicate_effort": true|false, "recommendation": "attempt"|"skip", "why_skip": "string or null"}"""


async def analyze_issue_llm(
    issue: dict[str, Any], age_signal: dict[str, Any]
) -> dict[str, Any]:
    """LLM-based issue analysis - local model only (chat_completion never
    calls a cloud provider). Replaces gogetajob's label-only classifyIssue().
    """
    comments_text = "\n".join(
        f"- {c.get('author', {}).get('login', '?')}: {c.get('body', '')[:300]}"
        for c in issue.get("comments", [])[:5]
    ) or "(no comments)"

    user_prompt = (
        f"Title: {issue.get('title', '')}\n"
        f"Body:\n{issue.get('body', '')[:1500]}\n\n"
        f"Comments:\n{comments_text}\n\n"
        f"Age signal: {age_signal['quadrant']} "
        f"({age_signal['age_days']} days old, {age_signal['comment_count']} comments)\n"
        f"Labels: {', '.join(issue.get('labels', []))}"
    )

    settings = get_settings_store()
    llm_provider = settings.get("provider", "ollama")

    try:
        raw = await chat_completion(
            [
                {"role": "system", "content": _ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        result = json.loads(raw.strip())
    except Exception as e:
        logger.warning("Issue analysis LLM call failed: %s", e)
        result = {
            "tractability": "unknown",
            "confidence": 0.0,
            "reasoning": f"LLM analysis failed: {e}",
            "likely_duplicate_effort": False,
            "recommendation": "skip",
            "why_skip": "analysis failed - not attempting blind",
        }

    result["llm_provider"] = llm_provider
    return result


# ── Step 3: unlinted-repo detection - the case gogetajob has no answer for ──


def detect_lint_instrumentation(work_dir: Path) -> dict[str, Any]:
    """Check whether the repo actually runs ruff/flake8/eslint/biome anywhere
    (CI workflows or config files) - a well-regarded repo with no linting
    instrumented won't have real problems filed as issues at all, since
    nobody's found them yet.
    """
    found: set[str] = set()

    workflows_dir = work_dir / ".github" / "workflows"
    if workflows_dir.is_dir():
        for wf in workflows_dir.glob("*.y*ml"):
            text = wf.read_text(encoding="utf-8", errors="ignore").lower()
            for tool, markers in LINT_MARKERS.items():
                if any(m in text for m in markers):
                    found.add(tool)

    config_checks = {
        "ruff": ["ruff.toml", ".ruff.toml"],
        "flake8": [".flake8", "setup.cfg", "tox.ini"],
        "eslint": [".eslintrc", ".eslintrc.json", ".eslintrc.js", ".eslintrc.cjs"],
        "biome": ["biome.json", "biome.jsonc"],
    }
    for tool, names in config_checks.items():
        if any((work_dir / n).exists() for n in names):
            found.add(tool)

    pyproject = work_dir / "pyproject.toml"
    if pyproject.exists() and "[tool.ruff]" in pyproject.read_text(
        encoding="utf-8", errors="ignore"
    ):
        found.add("ruff")

    is_python = (work_dir / "pyproject.toml").exists() or any(work_dir.glob("*.py"))
    is_js = (work_dir / "package.json").exists()

    relevant_tools = set()
    if is_python:
        relevant_tools |= {"ruff", "flake8"}
    if is_js:
        relevant_tools |= {"eslint", "biome"}

    return {
        "instrumented_tools": sorted(found),
        "is_python": is_python,
        "is_js": is_js,
        "fully_instrumented": bool(relevant_tools) and bool(relevant_tools & found),
    }


def _repo_relative(work_dir: Path, raw_path: str) -> str:
    """Repo-relative, forward-slash path for anything going into an issue
    title/body. Absolute Windows paths (a) leak our local machine's
    directory layout into someone else's public tracker for no reason, and
    (b) their backslashes get mangled into escape sequences (\\D, \\r, \\t...)
    somewhere in the gh/subprocess pipeline - confirmed the hard way when a
    filed issue title came back reading "...for-testing-a" with the rest
    silently eaten as escapes.
    """
    if not raw_path:
        return raw_path
    try:
        return Path(raw_path).relative_to(work_dir).as_posix()
    except ValueError:
        return Path(raw_path).name


def own_lint_scan(work_dir: Path, is_python: bool, is_js: bool) -> list[dict[str, Any]]:
    """Run our own ruff/biome scan when the repo isn't instrumented -
    surfacing things the maintainer never had a chance to see. Read-only:
    returns findings, does not fix or file anything.
    """
    findings: list[dict[str, Any]] = []

    if is_python:
        src = work_dir / "src" if (work_dir / "src").is_dir() else work_dir
        out = _sh(
            [RUFF_EXE, "check", str(src), "--output-format", "json"],
            timeout=30,
            allow_nonzero=True,
        )
        if out and not out.startswith("<error"):
            try:
                for f in json.loads(out)[:20]:
                    findings.append(
                        {
                            "tool": "ruff",
                            "file": _repo_relative(work_dir, f.get("filename", "")),
                            "line": f.get("location", {}).get("row", 0),
                            "code": f.get("code", ""),
                            "message": f.get("message", ""),
                        }
                    )
            except json.JSONDecodeError:
                pass

    if is_js:
        out = _sh(
            ["npx", "--yes", "@biomejs/biome", "check", str(work_dir), "--reporter=json"],
            timeout=60,
            allow_nonzero=True,
        )
        if out and not out.startswith("<error"):
            try:
                data = json.loads(out)
                for d in data.get("diagnostics", [])[:20]:
                    findings.append(
                        {
                            "tool": "biome",
                            "file": _repo_relative(
                                work_dir, d.get("location", {}).get("path", {}).get("file", "")
                            ),
                            "line": 0,
                            "code": d.get("category", ""),
                            "message": d.get("description", ""),
                        }
                    )
            except json.JSONDecodeError:
                pass

    return findings


# ── Step 4: friendly issue tone - never sound like a smartypants ──

FRIENDLY_ISSUE_SYSTEM_PROMPT = """Write a GitHub issue body reporting a finding. This is being filed by an AI on someone else's project - be humble and genuinely helpful, never preachy or condescending.

Rules:
- Open with brief, human context ("Was looking through the codebase and noticed..."), not a report header.
- Never use absolute/accusatory language ("this is broken", "you should"). Prefer "might be worth a look", "wanted to flag in case it's useful".
- Explicitly invite the maintainer to close it if it's already known, intentional, or not a priority - "feel free to close if this isn't relevant."
- Describe the finding concretely (file, what you saw) without lecturing about why it matters - trust the maintainer to know their own project.
- Keep it short - 3-5 sentences plus the concrete detail. No bullet-point checklists, no emoji, no "Summary/Impact/Recommendation" headers.
- Sign off naturally, e.g. "Happy to open a PR for this if it'd be welcome." - never "Sincerely" or a signature block.

Output ONLY the issue body text, nothing else - no title, no JSON, no markdown code fence."""


async def friendly_issue_body(finding_summary: str) -> str:
    """Generate a warm, humble issue body for a self-found finding
    (unlinted-repo scan result, badge oopsie, etc) - local model only.
    """
    try:
        return (
            await chat_completion(
                [
                    {"role": "system", "content": FRIENDLY_ISSUE_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Finding: {finding_summary}"},
                ]
            )
        ).strip()
    except Exception as e:
        logger.warning("Friendly issue body generation failed: %s", e)
        return (
            f"Noticed the following while looking through the codebase: {finding_summary}\n\n"
            "Might be worth a look - feel free to close if this isn't relevant or already known."
        )


# ── Step 5: duplicate-issue courtesy check ──


def _looks_like_duplicate(owner: str, repo: str, query_terms: str) -> bool:
    """Cheap courtesy check before filing: is there already an open or
    recently-closed issue that looks like this one? Filing a duplicate on
    someone else's tracker is exactly the kind of cheeky/careless move
    Sandra flagged wanting to avoid.
    """
    out = _sh(
        [
            "gh",
            "search",
            "issues",
            "--repo",
            f"{owner}/{repo}",
            "--json",
            "title",
            f"-L5",
            "--",
            query_terms,
        ],
        timeout=10,
    )
    if not out or out.startswith("<error"):
        return False
    try:
        return len(json.loads(out)) > 0
    except json.JSONDecodeError:
        return False


# ── Orchestrator: read-only analysis, never acts ──


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def fritz_analyze_repo(
    repo_url: Annotated[str, Field(description="Full GitHub repo URL to analyze")],
    max_issues: Annotated[
        int, Field(description="Max open issues to LLM-analyze", ge=1, le=20)
    ] = 5,
) -> dict[str, Any]:
    """Analyze a repo for contribution opportunities - read-only, never
    files anything. Improves on gogetajob's classifyIssue() with real LLM
    analysis (local model only) instead of label matching, an age +
    maintainer-engagement signal gogetajob fetches but never uses, and a
    proactive scan for repos that simply don't run ruff/biome (so real
    problems were never filed as issues at all).

    Every issue considered - attempted or skipped - is logged to
    analysis_log with the reasoning, for later postmortem review.

    Returns a report; use fritz_act_on_finding to actually file anything.

    ## Return Format
    {"success": bool, "repo": str, "instrumentation": dict, "existing_issues": [...],
     "self_found": [...], "message": str}

    ## Examples
    fritz_analyze_repo(repo_url="https://github.com/kovidgoyal/calibre")
    """
    from ...engine.sqlite_store import get_store

    store = get_store()
    repo_name = repo_url.rstrip("/").split("/")[-1]
    owner = repo_url.rstrip("/").split("/")[-2]
    work_dir = REPOS_ROOT / f"{repo_name}-analyze"

    _sh_shell(f"rmdir /s /q {work_dir} 2>nul")
    clone_out = _sh(["git", "clone", "--depth", "50", repo_url, str(work_dir)], timeout=120)
    if not work_dir.is_dir():
        return {
            "success": False,
            "repo": f"{owner}/{repo_name}",
            "instrumentation": {},
            "existing_issues": [],
            "self_found": [],
            "message": f"Clone failed, nothing analyzed: {clone_out}",
        }

    instrumentation = detect_lint_instrumentation(work_dir)

    # Existing open issues, LLM-analyzed
    existing_analyzed: list[dict[str, Any]] = []
    issue_list_raw = _sh(
        [
            "gh",
            "issue",
            "list",
            "-R",
            f"{owner}/{repo_name}",
            "--state",
            "open",
            "--limit",
            str(max_issues),
            "--json",
            "number,title,body,labels,createdAt",
        ],
        timeout=15,
    )
    try:
        issue_summaries = json.loads(issue_list_raw) if issue_list_raw else []
    except json.JSONDecodeError:
        issue_summaries = []

    for summary in issue_summaries:
        number = summary.get("number")
        detail_raw = _sh(
            [
                "gh",
                "issue",
                "view",
                str(number),
                "-R",
                f"{owner}/{repo_name}",
                "--json",
                "title,body,createdAt,comments,labels",
            ],
            timeout=15,
        )
        try:
            issue = json.loads(detail_raw)
        except json.JSONDecodeError:
            continue
        issue["labels"] = [
            item.get("name", "") if isinstance(item, dict) else str(item)
            for item in issue.get("labels", [])
        ]

        age_signal = compute_age_signal(issue.get("createdAt", ""), issue.get("comments", []))
        analysis = await analyze_issue_llm(issue, age_signal)

        store.analysis_log_add(
            repo=f"{owner}/{repo_name}",
            source="existing_issue",
            issue_number=str(number),
            issue_url=f"https://github.com/{owner}/{repo_name}/issues/{number}",
            age_signal=age_signal["quadrant"],
            tractability=analysis.get("tractability", "unknown"),
            confidence=float(analysis.get("confidence", 0.0)),
            reasoning=analysis.get("reasoning", ""),
            recommendation=analysis.get("recommendation", "skip"),
            llm_provider=analysis.get("llm_provider", ""),
        )

        existing_analyzed.append(
            {
                "number": number,
                "title": issue.get("title", ""),
                "url": f"https://github.com/{owner}/{repo_name}/issues/{number}",
                "age_signal": age_signal,
                "analysis": analysis,
            }
        )

    # Self-found findings when the repo isn't instrumented
    self_found: list[dict[str, Any]] = []
    if not instrumentation["fully_instrumented"]:
        raw_findings = own_lint_scan(
            work_dir, instrumentation["is_python"], instrumentation["is_js"]
        )
        for f in raw_findings[:_MAX_UNPROMPTED_ISSUES_PER_REPO]:
            self_found.append(f)
            store.analysis_log_add(
                repo=f"{owner}/{repo_name}",
                source=f"self_found_{f['tool']}",
                reasoning=f"{f['code']}: {f['message']} ({f['file']}:{f['line']})",
                recommendation="issue_only",
            )

    _sh_shell(f"rmdir /s /q {work_dir} 2>nul")

    return {
        "success": True,
        "repo": f"{owner}/{repo_name}",
        "instrumentation": instrumentation,
        "existing_issues": existing_analyzed,
        "self_found": self_found,
        "message": (
            f"{len(existing_analyzed)} existing issue(s) analyzed, "
            f"{len(self_found)} self-found finding(s) "
            f"({'instrumented' if instrumentation['fully_instrumented'] else 'NOT lint-instrumented'})"
        ),
    }


def _search_candidate_repos(
    *,
    language: str = "",
    min_stars: int = 5,
    max_stars: int = 5000,
    active_days: int = 90,
    topic: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """gh-search-based repo discovery, same query shape as gogetajob's
    searchRepos() (topic must precede numeric qualifiers or GitHub silently
    drops it - verified against gogetajob's own source comment on this).
    """
    query_parts = []
    if topic:
        query_parts.append(f"topic:{topic}")
    query_parts.append(f"stars:{min_stars}..{max_stars}")
    if active_days:
        since = (datetime.now(UTC) - timedelta(days=active_days)).strftime("%Y-%m-%d")
        query_parts.append(f"pushed:>={since}")

    args = [
        "gh",
        "search",
        "repos",
        " ".join(query_parts),
        "--sort",
        "stars",
        "--order",
        "desc",
        "--limit",
        str(limit),
        "--json",
        "owner,name,description,stargazersCount,pushedAt",
    ]
    if language:
        args.extend(["--language", language])

    out = _sh(args, timeout=15)
    if not out or out.startswith("<error"):
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    return [
        {
            "owner": d.get("owner", {}).get("login", ""),
            "repo": d.get("name", ""),
            "description": d.get("description", ""),
            "stars": d.get("stargazersCount", 0),
            "pushed_at": d.get("pushedAt", ""),
        }
        for d in data
        if d.get("owner") and d.get("name")
    ]


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def fritz_discover_and_analyze(
    language: Annotated[str, Field(description="Language filter, e.g. 'Python'")] = "",
    min_stars: Annotated[int, Field(description="Minimum stars", ge=0)] = 5,
    max_stars: Annotated[int, Field(description="Maximum stars", ge=1)] = 5000,
    active_days: Annotated[
        int, Field(description="Only repos pushed within this many days", ge=1)
    ] = 90,
    topic: Annotated[str, Field(description="GitHub topic filter, e.g. 'ai-agent'")] = "",
    repo_limit: Annotated[
        int, Field(description="Max candidate repos to analyze", ge=1, le=10)
    ] = 3,
) -> dict[str, Any]:
    """Auto-crawler: find candidate repos via GitHub search, then run
    fritz_analyze_repo on each. Same underlying query shape as gogetajob's
    `discover` (stars range, topic, language, activity recency), but each
    candidate gets real LLM issue analysis instead of gogetajob just
    listing repos by star count. Read-only - never files or PRs anything;
    review the report and call fritz_act_on_finding for what's worth it.

    Defaults are deliberately narrow (5-5000 stars, pushed within 90 days,
    3 repos) to keep a single crawl fast and reviewable rather than a huge
    unfocused sweep.

    ## Return Format
    {"success": bool, "candidates": [...], "reports": [...], "message": str}
    """
    candidates = _search_candidate_repos(
        language=language,
        min_stars=min_stars,
        max_stars=max_stars,
        active_days=active_days,
        topic=topic,
        limit=repo_limit,
    )
    if not candidates:
        return {
            "success": True,
            "candidates": [],
            "reports": [],
            "message": "No candidate repos matched the search criteria.",
        }

    reports = []
    for c in candidates:
        repo_url = f"https://github.com/{c['owner']}/{c['repo']}"
        try:
            report = await fritz_analyze_repo(repo_url=repo_url, max_issues=3)
            reports.append({**c, "report": report})
        except Exception as e:
            logger.warning("Crawl analysis failed for %s: %s", repo_url, e)
            reports.append({**c, "report": {"success": False, "message": str(e)}})

    return {
        "success": True,
        "candidates": candidates,
        "reports": reports,
        "message": f"{len(candidates)} candidate repo(s) found and analyzed.",
    }


@mcp.tool(version="0.1.0")
async def fritz_act_on_finding(
    repo_url: Annotated[str, Field(description="Full GitHub repo URL")],
    action: Annotated[str, Field(description="'issue' or 'pr'")],
    summary: Annotated[str, Field(description="What was found, for the friendly issue body")],
    issue_number: Annotated[
        str, Field(description="Existing issue number if commenting/attempting one")
    ] = "",
) -> dict[str, Any]:
    """File a friendly issue (or, for own repos, hand off to fritz_contribute
    for a PR) for a finding from fritz_analyze_repo. Separate, explicit step
    from analysis on purpose - analysis never files anything by itself.

    Own repos: 'pr' is allowed (fritz_contribute already only pushes to
    origin, never merges). Repos we don't own: 'pr' is refused for now -
    file an issue and let a human decide whether to build the fix. This is
    deliberately conservative while the pipeline is still fleet-tested; see
    memory note on why (Sandra: "test on our fleet more, to avoid
    overconfidence/cheekiness").

    ## Return Format
    {"success": bool, "issue_url": str, "message": str}
    """
    repo_name = repo_url.rstrip("/").split("/")[-1]
    owner = repo_url.rstrip("/").split("/")[-2]
    own_repo = owner.lower() == _own_gh_user().lower()

    if action == "pr" and not own_repo:
        return {
            "success": False,
            "message": (
                f"Refusing to auto-PR {owner}/{repo_name} - not an own repo. "
                "File an issue instead, or build the fix yourself and open the PR."
            ),
        }

    if _looks_like_duplicate(owner, repo_name, summary[:60]):
        return {
            "success": False,
            "message": "A similar issue already looks to exist on this repo - not filing a duplicate.",
        }

    body = await friendly_issue_body(summary)
    title = summary[:80]

    issue_url = _sh(
        [
            "gh",
            "issue",
            "create",
            "--repo",
            f"{owner}/{repo_name}",
            "--title",
            title,
            "--body",
            body,
        ],
        timeout=15,
    )

    issue_filed = bool(issue_url) and not issue_url.startswith("<error")

    from ...engine.sqlite_store import get_store

    get_store().analysis_log_add(
        repo=f"{owner}/{repo_name}",
        source="fritz_act_on_finding",
        issue_number=issue_number,
        issue_url=issue_url if issue_filed else "",
        recommendation=action,
        action_taken="filed_issue" if issue_filed else "failed",
        reasoning=summary[:300] if issue_filed else f"{summary[:250]} | gh issue create failed: {issue_url}",
    )

    if not issue_filed:
        return {
            "success": False,
            "issue_url": "",
            "message": f"gh issue create failed: {issue_url}",
        }

    if action == "pr" and own_repo:
        from .contribute import fritz_contribute

        pr_result = await fritz_contribute(repo_url=repo_url, dry_run=False)
        return {
            "success": pr_result.get("success", False),
            "issue_url": issue_url,
            "pr_url": pr_result.get("pr_url", ""),
            "message": f"Issue filed, PR attempt: {pr_result.get('message', '')}",
        }

    return {"success": True, "issue_url": issue_url, "message": "Friendly issue filed."}
