"""HTML rendering for intel reports — iPad-friendly, mobile-first."""

from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any


def markdown_to_html(md: str) -> str:
    """Lightweight markdown → HTML (no extra deps)."""
    lines = md.splitlines()
    out: list[str] = []
    in_list = False
    in_code = False
    code_buf: list[str] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_buf)) + "</code></pre>")
                code_buf = []
                in_code = False
            else:
                close_list()
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        if line.startswith("### "):
            close_list()
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            close_list()
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            close_list()
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            body = _inline_md(line[2:])
            out.append(f"<li>{body}</li>")
        elif not line.strip():
            close_list()
            out.append("<br>")
        else:
            close_list()
            out.append(f"<p>{_inline_md(line)}</p>")

    close_list()
    if in_code and code_buf:
        out.append("<pre><code>" + html.escape("\n".join(code_buf)) + "</code></pre>")
    return "\n".join(out)


def _inline_md(text: str) -> str:
    s = html.escape(text)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"_([^_]+)_", r"<em>\1</em>", s)
    return s


_BASE_CSS = """
:root {
  --bg: #0f1419;
  --card: #1a2332;
  --text: #e8edf4;
  --muted: #8b9cb3;
  --accent: #5b9fd4;
  --fritz: #e8a838;
  --aiwatcher: #3dd6c6;
  --border: #2a3548;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.55;
  min-height: 100vh;
  -webkit-text-size-adjust: 100%;
}
.wrap { max-width: 720px; margin: 0 auto; padding: 1.25rem 1rem 3rem; }
header {
  padding: 1.5rem 0 1rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.5rem;
}
header h1 { font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; }
header p { color: var(--muted); font-size: 0.9rem; margin-top: 0.35rem; }
.badge {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  margin-right: 0.4rem;
}
.badge-fritz { background: rgba(232,168,56,0.2); color: var(--fritz); }
.badge-aiwatcher { background: rgba(61,214,198,0.2); color: var(--aiwatcher); }
.badge-other { background: rgba(91,159,212,0.2); color: var(--accent); }
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1rem 1.1rem;
  margin-bottom: 0.75rem;
  text-decoration: none;
  color: inherit;
  display: block;
  transition: border-color 0.15s;
}
.card:active, .card:hover { border-color: var(--accent); }
.card h2 { font-size: 1.05rem; font-weight: 600; margin-bottom: 0.35rem; }
.card .meta { font-size: 0.8rem; color: var(--muted); }
.card .summary { font-size: 0.88rem; color: var(--muted); margin-top: 0.5rem; }
article { font-size: 1rem; }
article h1 { font-size: 1.5rem; margin: 1.2rem 0 0.6rem; }
article h2 { font-size: 1.2rem; margin: 1.1rem 0 0.5rem; color: var(--accent); }
article h3 { font-size: 1.05rem; margin: 0.9rem 0 0.4rem; }
article p { margin: 0.5rem 0; }
article ul { margin: 0.5rem 0 0.5rem 1.2rem; }
article li { margin: 0.25rem 0; }
article code {
  background: #243044;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  font-size: 0.88em;
}
article pre {
  background: #121820;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.85rem;
  overflow-x: auto;
  margin: 0.75rem 0;
  font-size: 0.85rem;
}
.back {
  display: inline-block;
  color: var(--accent);
  text-decoration: none;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}
.footer {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  font-size: 0.75rem;
  color: var(--muted);
}
.empty { color: var(--muted); text-align: center; padding: 2rem 0; }
"""


def _source_badge(source: str) -> str:
    key = source.lower()
    if key in ("fritz", "fleet-agent", "fleet-agent-mcp"):
        cls = "badge-fritz"
        label = "Fritz"
    elif key in ("aiwatcher", "aiwatcher-mcp"):
        cls = "badge-aiwatcher"
        label = "AIWatcher"
    else:
        cls = "badge-other"
        label = source
    return f'<span class="badge {cls}">{html.escape(label)}</span>'


def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M UTC")
    except ValueError:
        return iso[:16]


def render_index_page(reports: list[dict[str, Any]], *, hub_name: str = "Fleet Intel") -> str:
    cards: list[str] = []
    for r in reports:
        rid = html.escape(str(r.get("id", "")))
        title = html.escape(str(r.get("title", "Untitled")))
        summary = html.escape(str(r.get("summary", ""))[:220])
        created = _fmt_time(str(r.get("created_at", "")))
        badge = _source_badge(str(r.get("source", "")))
        cards.append(
            f'<a class="card" href="/reports/{rid}">'
            f"<h2>{title}</h2>"
            f'<div class="meta">{badge}{created}</div>'
            f'{"<div class=summary>" + summary + "</div>" if summary else ""}'
            f"</a>"
        )

    body = "\n".join(cards) if cards else '<p class="empty">No reports yet.</p>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>{html.escape(hub_name)}</title>
<style>{_BASE_CSS}</style>
</head>
<body>
<div class="wrap">
<header>
<h1>{html.escape(hub_name)}</h1>
<p>Fritz + AIWatcher — readable on iPad via Tailscale or Funnel</p>
</header>
{body}
<div class="footer">Fleet Intel Reports Hub</div>
</div>
</body>
</html>"""


def render_report_page(
    *,
    title: str,
    source: str,
    created_at: str,
    body_html: str,
) -> str:
    badge = _source_badge(source)
    created = _fmt_time(created_at)
    safe_title = html.escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>{safe_title}</title>
<style>{_BASE_CSS}</style>
</head>
<body>
<div class="wrap">
<a class="back" href="/">← All reports</a>
<header>
<h1>{safe_title}</h1>
<p>{badge}<span style="color:var(--muted)">{created}</span></p>
</header>
<article>{body_html}</article>
<div class="footer">Fleet Intel Reports Hub</div>
</div>
</body>
</html>"""


def wrap_markdown_report(
    *,
    title: str,
    source: str,
    markdown: str,
    summary: str = "",
) -> str:
    from datetime import UTC, datetime

    body = markdown_to_html(markdown)
    return render_report_page(
        title=title,
        source=source,
        created_at=datetime.now(UTC).isoformat(),
        body_html=body,
    )
