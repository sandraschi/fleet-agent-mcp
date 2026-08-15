"""Public Intel Hub site generator — funnel-facing, PUBLIC-SAFE data only.

The Tailscale funnel exposes this page to the public internet. Everything it
renders MUST be derived from genuinely public sources or sanitized aggregates:

  - GitHub: public repo metadata from the sandraschi user (name, description,
    stars, language, last push) — public by definition.
  - Dev diary (vla_mcp notebooks): ONLY per-repo aggregates (repo tag, latest
    category + date, entry counts). Never titles, bodies, or authors.
  - AIWatcher: ONLY counts (items in the last window, feed totals, feed error
    counts). Never item titles, URLs, summaries, or tags.

No hostnames, IPs, filesystem paths, API keys, or personal identifiers ever
reach this page.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

_PUBLIC_OUT = Path.home() / ".fleet-intel" / "public"
_VLA_NOTEBOOKS = Path("D:/Dev/repos/vla-mcp/data/notebooks/notebooks.sqlite3")
_GH_USER = "sandraschi"
_AIWATCHER_BASE = "http://127.0.0.1:10946"

GENERATED_AT_LABEL = "fleet-intel-public-v1"


async def github_repos() -> list[dict[str, Any]]:
    """Fetch public repo metadata for the sandraschi user (paginated)."""
    repos: list[dict[str, Any]] = []
    page = 1
    while page <= 3:
        proc = await asyncio.create_subprocess_exec(
            "gh",
            "api",
            f"/users/{_GH_USER}/repos?per_page=100&sort=updated&page={page}",
            "--jq",
            ".[] | {name, description, stargazers_count, language, pushed_at, html_url, fork}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await proc.communicate()
        if proc.returncode != 0 or not out.strip():
            break
        # gh api --jq emits NDJSON (one object per line) for array inputs.
        batch = []
        for line in out.splitlines():
            if not line.strip():
                continue
            try:
                batch.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def diary_digest() -> dict[str, Any]:
    """Per-repo aggregates from the vla_mcp dev diary (public-safe subset).

    Returns only repo tag, latest category, latest date, and counts — never
    titles, bodies, or authors.
    """
    result: dict[str, Any] = {"repos": {}, "total_entries": 0, "by_category": {}}
    if not _VLA_NOTEBOOKS.is_file():
        return result
    try:
        conn = sqlite3.connect(f"file:{_VLA_NOTEBOOKS}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT tags, category, created_at FROM notebook_entries WHERE notebook='dev'"
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return result

    for tags_raw, category, created_at in rows:
        tags = tags_raw.split(",") if tags_raw else []
        repo_tag = next((t.strip() for t in tags if t.strip().startswith("repo:")), None)
        repo = repo_tag[5:] if repo_tag else "other"
        entry = result["repos"].setdefault(
            repo, {"repo": repo, "entries": 0, "latest_category": None, "latest_at": None}
        )
        entry["entries"] += 1
        result["total_entries"] += 1
        result["by_category"][category] = result["by_category"].get(category, 0) + 1
        if not entry["latest_at"] or (created_at or "") > entry["latest_at"]:
            entry["latest_at"] = created_at
            entry["latest_category"] = category

    result["repos"] = dict(
        sorted(result["repos"].items(), key=lambda kv: kv[1].get("latest_at") or "", reverse=True)
    )
    return result


async def aiwatcher_stats() -> dict[str, Any]:
    """Sanitized AIWatcher counts — never item content."""
    out: dict[str, Any] = {"reachable": False}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            stats_resp = await client.get(f"{_AIWATCHER_BASE}/api/stats")
            if stats_resp.status_code == 200:
                stats = stats_resp.json()
                out["reachable"] = True
                if isinstance(stats, dict):
                    out["stats"] = {
                        k: v
                        for k, v in stats.items()
                        if k in ("total_items", "total_feeds", "pending", "last_poll", "bundles")
                    }
            feeds_resp = await client.get(f"{_AIWATCHER_BASE}/api/feeds")
            if feeds_resp.status_code == 200:
                feeds = (
                    feeds_resp.json().get("feeds", [])
                    if isinstance(feeds_resp.json(), dict)
                    else []
                )
                out["feed_total"] = len(feeds)
                out["feed_errors"] = sum(
                    1 for f in feeds if isinstance(f, dict) and f.get("failure_count", 0) > 0
                )
    except httpx.HTTPError:
        pass
    return out


def _escape(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(repos: list[dict[str, Any]], diary: dict[str, Any], aiw: dict[str, Any]) -> str:
    """Assemble a self-contained dark-themed public page."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    repo_rows = "".join(
        f"""
        <tr>
          <td class="mono"><a href="{_escape(r.get("html_url", "#"))}">
            {_escape(r.get("name"))}</a></td>
          <td>{_escape((r.get("description") or "")[:120])}</td>
          <td>{_escape(r.get("language") or "")}</td>
          <td class="right">{r.get("stargazers_count", 0)}</td>
          <td class="mono">{_escape((r.get("pushed_at") or "")[:10])}</td>
        </tr>"""
        for r in repos
    )

    diary_rows = "".join(
        f"""
        <tr>
          <td class="mono">{_escape(v["repo"])}</td>
          <td>{_escape(v["latest_category"] or "")}</td>
          <td>{v["entries"]}</td>
          <td class="mono">{_escape((v["latest_at"] or "")[:10])}</td>
        </tr>"""
        for v in list(diary.get("repos", {}).values())[:24]
    )
    diary_total = diary.get("total_entries", 0)
    cat_badges = "".join(
        f'<span class="badge">{_escape(k)}: {v}</span>'
        for k, v in sorted(diary.get("by_category", {}).items(), key=lambda kv: -kv[1])
    )

    aiw_line = "offline"
    if aiw.get("reachable"):
        s = aiw.get("stats", {})
        parts = [f"{s.get('total_items', '?')} items tracked"]
        if aiw.get("feed_total") is not None:
            errs = aiw.get("feed_errors", 0)
            parts.append(f"{aiw['feed_total']} feeds ({errs} erroring)")
        aiw_line = " · ".join(parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Sandrafleet — Public</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin:0; background:#09090b; color:#e4e4e7; font-family:system-ui,sans-serif; }}
  header {{ padding:2.5rem 1.5rem 1.5rem; max-width:1080px; margin:0 auto; }}
  h1 {{ font-size:1.6rem; margin:0 0 .25rem; }}
  .sub {{ color:#a1a1aa; font-size:.9rem; }}
  main {{ max-width:1080px; margin:0 auto; padding:0 1.5rem 3rem; }}
  section {{ margin-top:2rem; }}
  h2 {{ font-size:1.1rem; border-bottom:1px solid #27272a; padding-bottom:.4rem; }}
  table {{ width:100%; border-collapse:collapse; font-size:.85rem; }}
  th, td {{ text-align:left; padding:.45rem .6rem; border-bottom:1px solid #1f1f23; }}
  th {{ color:#a1a1aa; font-weight:500; }}
  .mono {{ font-family:ui-monospace,monospace; font-size:.8rem; }}
  .right {{ text-align:right; }}
  a {{ color:#818cf8; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .badge {{ display:inline-block; background:#18181b; border:1px solid #27272a;
            border-radius:999px; padding:.2rem .6rem; font-size:.75rem; margin:.1rem .2rem; }}
  footer {{ color:#71717a; font-size:.75rem; max-width:1080px; margin:0 auto;
            padding:1rem 1.5rem 3rem; }}
  .note {{ background:#101012; border:1px solid #27272a; border-radius:8px;
          padding:.8rem 1rem; color:#a1a1aa; font-size:.85rem; }}
</style>
</head>
<body>
<header>
  <h1>Sandrafleet</h1>
  <p class="sub">The sandraschi MCP fleet — public window. Generated {now}</p>
</header>
<main>
  <div class="note">Public-safe aggregates only: GitHub repo metadata, fleet dev-diary
  activity by repo, and AIWatcher pipeline counts. No private data is shown here.</div>

  <section>
    <h2>Fleet repositories <span class="sub">({len(repos)} shown, updated first)</span></h2>
    <table>
      <thead><tr><th>Repo</th><th>Description</th><th>Language</th>
        <th class="right">★</th><th>Pushed</th></tr></thead>
      <tbody>{repo_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>Dev diary activity <span class="sub">({diary_total} entries)</span></h2>
    {cat_badges}
    <table>
      <thead><tr><th>Repo</th><th>Latest category</th><th>Entries</th>
        <th>Last entry</th></tr></thead>
      <tbody>{diary_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>AIWatcher pipeline</h2>
    <p class="sub">{_escape(aiw_line)}</p>
  </section>
</main>
<footer>
  Data: github.com/{_GH_USER} (public) · fleet dev diary aggregates · AIWatcher counts.
  Sign in with credentials for the full Intel Reports Hub.
</footer>
</body>
</html>"""


async def generate_public_site() -> dict[str, Any]:
    """Fetch public-safe data, render the site, and persist it for the hub."""
    repos = await github_repos()
    diary = diary_digest()
    aiw = await aiwatcher_stats()
    html = render_html(repos, diary, aiw)

    _PUBLIC_OUT.mkdir(parents=True, exist_ok=True)
    out_path = _PUBLIC_OUT / "index.html"
    out_path.write_text(html, encoding="utf-8")

    return {
        "success": True,
        "path": str(out_path),
        "repos": len(repos),
        "diary_entries": diary.get("total_entries", 0),
        "aiwatcher_reachable": aiw.get("reachable", False),
        "generated_at": datetime.now(UTC).isoformat(),
        "message": (
            f"Public site written to {out_path} "
            f"({len(repos)} repos, {diary.get('total_entries', 0)} diary entries)."
        ),
    }
