# Fritz Contribution Pipeline

## How it works

There are two complementary approaches to contributing to open-source repos:

### Option A: Native Fritz — Static analysis find-and-fix (Python)

Fritz discovers issues by scanning source code directly, not by reading existing tickets.

```
1. fritz_find_contributions()
   → gh search issues "language:python label:good-first-issue,help-wanted"
   → returns [{repo, issue_title, issue_url, labels}, ...]

2. fritz_contribute("https://github.com/owner/repo")
   → clone repo
   → run ruff --select S701,S110,E722,F401
   → pick most severe finding (e.g. S701 = XSS security)
   → LLM computes old_string/new_string fix
   → gh issue create --label bug
   → git checkout -b fix/s701
   → apply fix via file_edit
   → git commit + push fork
   → gh pr create
```

Fritz finds its OWN issues — no dependency on repo maintainers tagging things.

### Option B: gogetajob — Work through EXISTING issue backlogs (multi-language)

gogetajob reads existing open issues from a repo and lets you claim them.

```
1. gogetajob_scan("owner/repo")
   → npx @kagura-agent/gogetajob scan owner/repo
   → reads EXISTING open issues
   → returns issues with labels, descriptions, difficulty

2. gogetajob_feed()
   → shows the job queue from the local gogetajob database

3. gogetajob_start("owner/repo#123")
   → takes issue #123 (fork + clone + branch)

4. (Do the fix — manually via other tools)

5. gogetajob_submit("owner/repo#123", tokens=5000)
   → git push + gh pr create
   → records the work + token count
```

### When to use which

| Approach | Best for | How it finds work |
|----------|----------|-------------------|
| Native Fritz | Python repos, security/style lint | `ruff` static analysis |
| gogetajob | Any language, existing issue queues | Reads repo's open issues |

### Real example (what Kagura does)

```
gogetajob scan NVIDIA/NemoClaw
→ "NemoClaw has 12 open good-first-issues"

gogetajob start NVIDIA/NemoClaw#42
→ fork, clone, branch created

Sub-agent: read issue #42, implement fix

gogetajob submit NVIDIA/NemoClaw#42 --tokens 8500
→ PR created, work logged
```

### 1. Discover opportunities
`fritz_find_contributions(query, limit)`

Searches GitHub via `gh search issues` for repos with fixable issues.
Default query: `language:python label:good-first-issue,help-wanted`

Returns structured results:
```
{
  "opportunities": [
    {
      "repo": "owner/repo",
      "repo_url": "https://github.com/owner/repo",
      "issue_title": "...",
      "issue_url": "https://github.com/owner/repo/issues/123",
      "state": "open",
      "labels": ["good-first-issue", "bug"]
    }
  ]
}
```

### 2. Contribute
`fritz_contribute(repo_url, dry_run)`

Clones the target repo, runs `ruff` to find lint errors (S701, S110, E722, F401),
files a GitHub issue, creates a branch, computes a fix via LLM, applies it,
commits, pushes to a fork, and opens a PR.

```
Pipeline: clone → ruff scan → prioritize → LLM fix → file issue →
branch → apply fix → commit → push fork → PR
```

### How repos are selected (kagura-agent approach)

Inspired by [kagura-agent/gogetajob](https://github.com/kagura-agent/gogetajob), the
selection strategy:

1. **Start with known targets** — Repos in the fleet ecosystem, dependencies, related tools
2. **GitHub search** — `language:python label:good-first-issue`, `label:help-wanted`, etc.
3. **Prioritize by impact** — Security fixes (S701 XSS) > error-handling (S110) > style (F401)
4. **Filter by fixability** — Only targets that `ruff` can detect and the LLM can fix

### Real shipped PRs

| Repo | PR | Fix |
|------|----|-----|
| discord-mcp | #2, #4 | S110, E722 error handling |
| GrandOrgue | #2497, #2498 | S701 XSS, S110 exception handling |
| edge-bookmark-mcp-server | #5 | F401 unused imports |

### Current limitations

- Python-only (ruff-based lint scanning)
- Requires `gh` CLI authenticated with GitHub
- Requires a configured LLM for fix computation
- Fork push assumes `sandraschi` GitHub user
- Only targets `src/` directory for lint scanning

## gogetajob integration

Fritz also wraps [gogetajob](https://github.com/kagura-agent/gogetajob) (npm: `@kagura-agent/gogetajob`),
Kagura's open-source contribution CLI. This gives Fritz access to the full gogetajob workflow:

| Tool | Delegates to | Purpose |
|------|-------------|---------|
| `gogetajob_scan(repo)` | `gogetajob scan` | Discover issues in a repo |
| `gogetajob_feed()` | `gogetajob feed` | Browse available jobs |
| `gogetajob_start(ref)` | `gogetajob start` | Take a job, fork/clone/branch |
| `gogetajob_submit(ref)` | `gogetajob submit` | Push + create PR |
| `gogetajob_stats()` | `gogetajob stats` | View contribution stats |
| `gogetajob_sync()` | `gogetajob sync` | Check PR statuses |

The two pipelines can be mixed: use `fritz_find_contributions` to discover targets,
`gogetajob_start` to set up the workspace, `fritz_contribute` for the fix, and
`gogetajob_submit` to ship it.

