"""Public Intel Hub site generator - funnel-facing, PUBLIC-SAFE data only.

The Tailscale funnel exposes this page to the public internet. Everything it
renders MUST be derived from genuinely public sources or sanitized aggregates:

  - GitHub: public repo metadata from the sandraschi user (name, description,
    stars, language, last push) - public by definition.
  - Dev diary (vla_mcp notebooks): ONLY per-repo aggregates (repo tag, latest
    category + date, entry counts, per-category counts, per-day totals). Never
    titles, bodies, or authors.
  - AIWatcher: ONLY counts (items in the last window, feed totals, feed error
    counts). Never item titles, URLs, summaries, or tags.

No hostnames, IPs, filesystem paths, API keys, or personal identifiers ever
reach this page.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
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

    sem = asyncio.Semaphore(8)
    summaries = await asyncio.gather(*(_readme_summary(r["name"], sem) for r in repos))
    for repo, summary in zip(repos, summaries, strict=True):
        repo["readme_summary"] = summary

    return repos


def _extract_summary(readme_text: str, max_chars: int = 320) -> str:
    """Pull the first real paragraph out of a README (skip headings, badges, blanks).

    Stops at the first blank line after prose has started, so this is a single
    paragraph - roughly 3-4 lines once wrapped in the table cell, not the whole file.
    """
    paragraph: list[str] = []
    for raw_line in readme_text.splitlines():
        line = raw_line.strip()
        if not line:
            if paragraph:
                break
            continue
        if line.startswith(("#", "<", ">", "|", "![", "[![", "---", "***", "===")):
            continue
        paragraph.append(line)
    summary = " ".join(paragraph)
    # Strip inline markdown so the public page shows plain prose, not raw syntax.
    summary = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", summary)  # [text](url) -> text
    summary = re.sub(r"(\*\*|__)(.*?)\1", r"\2", summary)  # bold
    summary = re.sub(r"(?<!\w)[*_](.*?)[*_](?!\w)", r"\1", summary)  # italic
    summary = summary.replace("`", "")
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0] + "..."
    return summary


async def _readme_summary(name: str, sem: asyncio.Semaphore) -> str:
    """Fetch a repo's README and return a short public-safe summary paragraph.

    Best-effort: repos with no README, a fetch error, or undecodable content
    just yield "" and the caller falls back to the GitHub description field.
    """
    async with sem:
        proc = await asyncio.create_subprocess_exec(
            "gh",
            "api",
            f"/repos/{_GH_USER}/{name}/readme",
            "--jq",
            ".content",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await proc.communicate()
    if proc.returncode != 0 or not out.strip():
        return ""
    try:
        raw = base64.b64decode(out.strip().replace(b"\n", b"")).decode("utf-8", errors="replace")
    except (ValueError, UnicodeDecodeError):
        return ""
    return _extract_summary(raw)


def _parse_tags(tags_raw: str) -> list[str]:
    """Parse vla notebook tags into a clean list.

    vla_mcp stores tags as a JSON array (e.g. '["repo:vla-mcp", "spec"]'), but
    tolerate legacy comma-separated strings so the per-repo aggregation is not
    silently swallowed into "other".
    """
    raw = (tags_raw or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return [str(t).strip() for t in parsed if str(t).strip()]
    return [t.strip() for t in raw.split(",") if t.strip()]


def diary_digest() -> dict[str, Any]:
    """Per-repo aggregates from the vla_mcp dev diary (public-safe subset).

    Returns repo tag, latest category, latest date, entry counts, per-category
    counts per repo, and a per-day timeline - never titles, bodies, or authors.
    """
    result: dict[str, Any] = {
        "repos": {},
        "total_entries": 0,
        "by_category": {},
        "categories": [],
        "timeline": {},
    }
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

    day_cat: dict[str, dict[str, int]] = {}

    for tags_raw, category, created_at in rows:
        category = (category or "").strip() or "note"
        tags = _parse_tags(tags_raw)
        repo_tag = next((t for t in tags if t.startswith("repo:")), None)
        repo = repo_tag[5:].strip() if repo_tag else "other"
        entry = result["repos"].setdefault(
            repo,
            {
                "repo": repo,
                "entries": 0,
                "latest_category": None,
                "latest_at": None,
                "by_category": {},
            },
        )
        entry["entries"] += 1
        entry["by_category"][category] = entry["by_category"].get(category, 0) + 1
        result["total_entries"] += 1
        result["by_category"][category] = result["by_category"].get(category, 0) + 1
        if not entry["latest_at"] or (created_at or "") > entry["latest_at"]:
            entry["latest_at"] = created_at
            entry["latest_category"] = category

        day = (created_at or "")[:10]
        if day:
            day_bucket = day_cat.setdefault(day, {})
            day_bucket[category] = day_bucket.get(category, 0) + 1

    result["categories"] = sorted(
        result["by_category"].keys(), key=lambda k: -result["by_category"][k]
    )

    # Keep the most recent 14 days of activity, oldest -> newest for display.
    recent_days = sorted(day_cat, reverse=True)[:14]
    result["timeline"] = {day: day_cat[day] for day in reversed(recent_days)}

    result["repos"] = dict(
        sorted(result["repos"].items(), key=lambda kv: kv[1].get("latest_at") or "", reverse=True)
    )
    return result


async def aiwatcher_stats() -> dict[str, Any]:
    """Sanitized AIWatcher counts - never item content."""
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

    repo_data_json = json.dumps(
        [
            {
                "name": r.get("name") or "",
                "url": r.get("html_url") or "#",
                "desc": r.get("readme_summary") or (r.get("description") or "")[:320],
                "lang": r.get("language") or "",
                "stars": r.get("stargazers_count", 0),
                "pushed": r.get("pushed_at") or "",
            }
            for r in repos
        ]
    ).replace("</", "<\\/")

    diary_json = json.dumps(diary).replace("</", "<\\/")
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
<title>Sandrafleet - Public</title>
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
  th, td {{ text-align:left; padding:.45rem .6rem; border-bottom:1px solid #1f1f23;
            vertical-align:top; }}
  th {{ color:#a1a1aa; font-weight:500; }}
  .desc {{ max-width:34ch; line-height:1.4; color:#c4c4c9; }}
  .mono {{ font-family:ui-monospace,monospace; font-size:.8rem; }}
  .right {{ text-align:right; }}
  a {{ color:#818cf8; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .badge {{ display:inline-block; background:#18181b; border:1px solid #27272a;
            border-radius:999px; padding:.2rem .6rem; font-size:.75rem; margin:.1rem .2rem; }}
  .controls {{ display:flex; align-items:center; gap:.4rem; margin:.75rem 0 1rem; flex-wrap:wrap; }}
  .controls-label {{ color:#71717a; font-size:.8rem; margin-right:.2rem; }}
  .controls button {{ background:#18181b; border:1px solid #27272a; color:#c4c4c9;
            border-radius:6px; padding:.35rem .75rem; font-size:.8rem; cursor:pointer;
            font-family:inherit; }}
  .controls button:hover {{ border-color:#3f3f46; }}
  .controls button.active {{ background:#312e81; border-color:#4338ca; color:#e0e7ff; }}
  #group-toggle {{ margin-left:.5rem; }}
  .group-head {{ background:#111114; color:#a1a1aa; font-size:.75rem; text-transform:uppercase;
            letter-spacing:.04em; padding:.5rem .6rem; border-bottom:1px solid #27272a; }}
  .diary-toggle {{ background:none; border:none; color:#818cf8; cursor:pointer;
            font-family:inherit; font-size:.8rem; padding:0; }}
  .diary-toggle:hover {{ text-decoration:underline; }}
  .diary-detail td {{ background:#0e0e11; color:#a1a1aa; }}
  footer {{ color:#71717a; font-size:.75rem; max-width:1080px; margin:0 auto;
            padding:1rem 1.5rem 3rem; }}
  .note {{ background:#101012; border:1px solid #27272a; border-radius:8px;
          padding:.8rem 1rem; color:#a1a1aa; font-size:.85rem; }}
</style>
</head>
<body>
<header>
  <h1>Sandrafleet</h1>
  <p class="sub">The sandraschi MCP fleet - public window. Generated {now}</p>
</header>
<main>
  <div class="note">Public-safe aggregates only: GitHub repo metadata, fleet dev-diary
  activity by repo, and AIWatcher pipeline counts. No private data is shown here.</div>

  <section>
    <h2>Fleet repositories <span class="sub">({len(repos)} total)</span></h2>
    <div class="controls">
      <span class="controls-label">Sort:</span>
      <button type="button" data-sort="pushed" class="active">Pushed</button>
      <button type="button" data-sort="stars">Stars</button>
      <button type="button" data-sort="name">Name</button>
      <button type="button" id="group-toggle">Group by stars</button>
    </div>
    <table>
      <thead><tr><th>Repo</th><th>Description</th><th>Language</th>
        <th class="right">★</th><th>Pushed</th></tr></thead>
      <tbody id="repo-tbody"></tbody>
    </table>
  </section>

  <section>
    <h2>Dev diary activity <span class="sub">({diary_total} entries)</span></h2>
    {cat_badges}
    <p class="sub">Per-repo activity with category drilldown - click a repo to expand.</p>
    <table>
      <thead><tr><th>Repo</th><th class="right">Entries</th><th>Latest category</th>
        <th>Last entry</th></tr></thead>
      <tbody id="diary-tbody"></tbody>
    </table>
    <h3 class="sub" style="margin-top:1.5rem">Recent activity (last 14 days)</h3>
    <table id="diary-timeline"></table>
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
<script id="repo-data" type="application/json">{repo_data_json}</script>
<script id="diary-data" type="application/json">{diary_json}</script>
<script>
(function () {{
  var data = JSON.parse(document.getElementById('repo-data').textContent);
  var tbody = document.getElementById('repo-tbody');
  var groupToggle = document.getElementById('group-toggle');
  var sortBtns = document.querySelectorAll('[data-sort]');
  var sortKey = 'pushed';
  var sortDir = 'desc';
  var grouped = false;

  function sortRows(rows, key, dir) {{
    var sorted = rows.slice().sort(function (a, b) {{
      var av = a[key], bv = b[key];
      if (key === 'name') {{ av = av.toLowerCase(); bv = bv.toLowerCase(); }}
      if (av < bv) return dir === 'asc' ? -1 : 1;
      if (av > bv) return dir === 'asc' ? 1 : -1;
      return 0;
    }});
    return sorted;
  }}

  function makeRow(r) {{
    var tr = document.createElement('tr');

    var tdName = document.createElement('td');
    tdName.className = 'mono';
    var a = document.createElement('a');
    a.href = r.url;
    a.textContent = r.name;
    tdName.appendChild(a);
    tr.appendChild(tdName);

    var tdDesc = document.createElement('td');
    tdDesc.className = 'desc';
    tdDesc.textContent = r.desc;
    tr.appendChild(tdDesc);

    var tdLang = document.createElement('td');
    tdLang.textContent = r.lang;
    tr.appendChild(tdLang);

    var tdStars = document.createElement('td');
    tdStars.className = 'right';
    tdStars.textContent = r.stars;
    tr.appendChild(tdStars);

    var tdPushed = document.createElement('td');
    tdPushed.className = 'mono';
    tdPushed.textContent = (r.pushed || '').slice(0, 10);
    tr.appendChild(tdPushed);

    return tr;
  }}

  function groupRow(label, count) {{
    var tr = document.createElement('tr');
    var td = document.createElement('td');
    td.colSpan = 5;
    td.className = 'group-head';
    td.textContent = label + ' \u2014 ' + count + ' repo' + (count === 1 ? '' : 's');
    tr.appendChild(td);
    return tr;
  }}

  function render() {{
    tbody.innerHTML = '';
    if (!grouped) {{
      sortRows(data, sortKey, sortDir).forEach(function (r) {{ tbody.appendChild(makeRow(r)); }});
      return;
    }}
    var tiers = [
      {{ label: 'High \u2605 (7+)', test: function (s) {{ return s >= 7; }} }},
      {{ label: 'Mid \u2605 (1-6)', test: function (s) {{ return s >= 1 && s < 7; }} }},
      {{ label: 'Unstarred', test: function (s) {{ return s === 0; }} }}
    ];
    tiers.forEach(function (tier) {{
      var subset = data.filter(function (r) {{ return tier.test(r.stars); }});
      if (!subset.length) return;
      tbody.appendChild(groupRow(tier.label, subset.length));
      sortRows(subset, sortKey, sortDir).forEach(function (r) {{ tbody.appendChild(makeRow(r)); }});
    }});
  }}

  sortBtns.forEach(function (btn) {{
    btn.addEventListener('click', function () {{
      var key = btn.getAttribute('data-sort');
      if (sortKey === key) {{
        sortDir = sortDir === 'asc' ? 'desc' : 'asc';
      }} else {{
        sortKey = key;
        sortDir = key === 'name' ? 'asc' : 'desc';
      }}
      sortBtns.forEach(function (b) {{ b.classList.remove('active'); }});
      btn.classList.add('active');
      render();
    }});
  }});

  groupToggle.addEventListener('click', function () {{
    grouped = !grouped;
    groupToggle.classList.toggle('active', grouped);
    groupToggle.textContent = grouped ? 'Ungroup' : 'Group by stars';
    render();
  }});

  render();
}})();
</script>
<script>
(function () {{
  var diary = JSON.parse(document.getElementById('diary-data').textContent);
  var tbody = document.getElementById('diary-tbody');
  var categories = diary.categories || [];
  var repos = Object.keys(diary.repos || {{}});

  function esc(s) {{
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }}

  function detailCell(r) {{
    var s = '';
    categories.forEach(function (cat) {{
      var n = (r.by_category && r.by_category[cat]) || 0;
      if (n > 0) s += '<span class="badge">' + esc(cat) + ': ' + n + '</span>';
    }});
    return s || '<span class="sub">no entries</span>';
  }}

  function mkRow(r) {{
    var tr = document.createElement('tr');
    var tdT = document.createElement('td');
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'diary-toggle';
    btn.textContent = r.repo;
    btn.setAttribute('aria-expanded', 'false');
    tdT.appendChild(btn);
    tr.appendChild(tdT);
    var tdE = document.createElement('td');
    tdE.className = 'right';
    tdE.textContent = r.entries;
    tr.appendChild(tdE);
    var tdC = document.createElement('td');
    tdC.textContent = esc(r.latest_category || '');
    tr.appendChild(tdC);
    var tdD = document.createElement('td');
    tdD.className = 'mono';
    tdD.textContent = esc((r.latest_at || '').slice(0, 10));
    tr.appendChild(tdD);
    return tr;
  }}

  function mkDetail(r) {{
    var tr = document.createElement('tr');
    tr.className = 'diary-detail';
    tr.style.display = 'none';
    var td = document.createElement('td');
    td.colSpan = 4;
    td.innerHTML = '<span class="sub">Categories:</span> ' + detailCell(r);
    tr.appendChild(td);
    return tr;
  }}

  repos.forEach(function (repo) {{
    var r = diary.repos[repo];
    tbody.appendChild(mkRow(r));
    tbody.appendChild(mkDetail(r));
  }});

  tbody.addEventListener('click', function (ev) {{
    var btn = ev.target.closest('.diary-toggle');
    if (!btn) return;
    var detail = btn.closest('tr').nextElementSibling;
    if (!detail || detail.className !== 'diary-detail') return;
    var open = detail.style.display !== 'none';
    detail.style.display = open ? 'none' : '';
    btn.setAttribute('aria-expanded', open ? 'false' : 'true');
  }});

  var days = Object.keys(diary.timeline || {{}}).sort();
  if (days.length) {{
    var tl = document.getElementById('diary-timeline');
    var thead = document.createElement('thead');
    var hr = document.createElement('tr');
    var hDay = document.createElement('th');
    hDay.textContent = 'Day';
    hr.appendChild(hDay);
    categories.forEach(function (cat) {{
      var th = document.createElement('th');
      th.className = 'right';
      th.textContent = cat;
      hr.appendChild(th);
    }});
    var hTot = document.createElement('th');
    hTot.className = 'right';
    hTot.textContent = 'Total';
    hr.appendChild(hTot);
    thead.appendChild(hr);
    tl.appendChild(thead);

    var tb = document.createElement('tbody');
    days.forEach(function (day) {{
      var tr = document.createElement('tr');
      var tdDay = document.createElement('td');
      tdDay.className = 'mono';
      tdDay.textContent = day;
      tr.appendChild(tdDay);
      var c = diary.timeline[day] || {{}};
      var dayTot = 0;
      categories.forEach(function (cat) {{
        var td = document.createElement('td');
        td.className = 'right';
        var n = c[cat] || 0;
        td.textContent = n || '';
        dayTot += n;
        tr.appendChild(td);
      }});
      var tdT = document.createElement('td');
      tdT.className = 'right';
      tdT.textContent = dayTot;
      tr.appendChild(tdT);
      tb.appendChild(tr);
    }});
    tl.appendChild(tb);
  }}
}})();
</script>
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
