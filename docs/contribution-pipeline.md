# Fritz Contribution Pipeline

## How it works

Fritz can autonomously contribute to open-source repos through a two-tool pipeline:

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
