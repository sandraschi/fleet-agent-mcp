"""Mini HTTP server for Fleet Intel Reports — iPad / Tailscale access."""

from __future__ import annotations

import base64
import hmac
import os
from datetime import UTC, datetime
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from .render import render_index_page, wrap_markdown_report
from .store import get_report_html, hub_meta, list_reports, publish_report

DEFAULT_PORT = 11027
DEFAULT_HOST = "0.0.0.0"

# Paths reachable without credentials. /health stays open for the watchdog and
# fleet probes; /public is the deliberately harmless page for public funnel
# access. Everything else (index, reports, API) requires HTTP Basic auth.
PUBLIC_PATHS = ("/public", "/health")


def hub_host() -> str:
    return os.environ.get("INTEL_REPORTS_HUB_HOST", DEFAULT_HOST)


def hub_port() -> int:
    raw = os.environ.get("INTEL_REPORTS_HUB_PORT", str(DEFAULT_PORT))
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_PORT


def hub_root_path() -> str:
    """URL prefix uvicorn strips before routing (e.g. '/intel' when the hub
    sits behind a tailscale funnel subpath). Empty string = no prefix.
    """
    return os.environ.get("INTEL_REPORTS_HUB_ROOT_PATH", "").strip()


def hub_auth_credentials() -> tuple[str, str] | None:
    """Return (user, password) when HTTP Basic auth is configured.

    Auth is enabled when either INTEL_REPORTS_HUB_USER or INTEL_REPORTS_HUB_PASS
    is set. If neither is set, the hub serves unauthenticated and logs a loud
    warning at startup - never silently assume auth is on.
    """
    user = os.environ.get("INTEL_REPORTS_HUB_USER", "").strip()
    password = os.environ.get("INTEL_REPORTS_HUB_PASS", "").strip()
    if user or password:
        return user, password
    return None


def _ascii_normalize(text: str) -> str:
    """Normalize LLM-prose punctuation to ASCII (fleet hygiene rule).

    Em/en dashes and mojibake replacement chars -> plain hyphen; smart
    quotes -> straight quotes. Everything else is kept.
    """
    return (
        text.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\ufffd", "-")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        {"success": False, "error": "unauthorized"},
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Fleet Intel Reports"'},
    )


class _BasicAuthMiddleware:
    """HTTP Basic auth gate for the hub.

    Only enforces when credentials are configured; PUBLIC_PATHS bypass it.
    """

    def __init__(self, app, credentials: tuple[str, str] | None):
        self.app = app
        self.credentials = credentials

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or self.credentials is None:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if any(path == p or path.startswith(p + "/") for p in PUBLIC_PATHS):
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        header = headers.get(b"authorization", b"")
        expected_user, expected_pass = self.credentials
        authorized = False
        if header.lower().startswith(b"basic "):
            try:
                decoded = base64.b64decode(header.split(b" ", 1)[1]).decode("utf-8")
                user, _, password = decoded.partition(":")
                authorized = hmac.compare_digest(user, expected_user) and hmac.compare_digest(
                    password, expected_pass
                )
            except Exception:
                authorized = False

        if not authorized:
            # 401 with WWW-Authenticate (no redirect): the browser pops the
            # Basic auth dialog and retries WITH credentials, so authenticated
            # visitors can reach / (the index) from outside the tailnet too.
            # Anyone without credentials goes to /public explicitly - the
            # landing page links there. PUBLIC_PATHS stay open above.
            await _unauthorized()(scope, receive, send)
            return
        await self.app(scope, receive, send)


async def api_health(request: Request) -> JSONResponse:
    meta = hub_meta()
    return JSONResponse({"status": "ok", **meta})


async def api_reports_list(request: Request) -> JSONResponse:
    limit = int(request.query_params.get("limit", 50))
    reports = list_reports(limit=limit)
    return JSONResponse({"reports": reports, "count": len(reports)})


async def api_reports_publish(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "invalid JSON"}, status_code=400)

    # Boundary hygiene (fleet rule: generated prose MUST be ASCII): em/en
    # dashes, smart quotes, and mojibake replacement chars (U+FFFD, which
    # appears when an em dash survives a bad decode) become plain ASCII.
    title = _ascii_normalize((body.get("title") or "").strip())
    source = (body.get("source") or "fleet").strip()
    html_body = body.get("html") or ""
    markdown = body.get("markdown") or ""
    summary = _ascii_normalize((body.get("summary") or "")[:500])
    tags = body.get("tags") if isinstance(body.get("tags"), list) else []

    if not title:
        return JSONResponse({"success": False, "error": "title required"}, status_code=400)

    if not html_body and markdown:
        html_body = wrap_markdown_report(
            title=title,
            source=source,
            markdown=markdown,
            summary=summary,
        )
    if not html_body:
        return JSONResponse(
            {"success": False, "error": "html or markdown required"},
            status_code=400,
        )

    try:
        result = publish_report(
            title=title,
            source=source,
            html=html_body,
            summary=summary,
            tags=tags,
        )
        return JSONResponse(result)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)


async def page_index(request: Request) -> HTMLResponse:
    reports = list_reports(limit=80)
    return HTMLResponse(render_index_page(reports))


async def page_public(request: Request) -> HTMLResponse:
    """Public funnel page — serves the generated public site when present,
    otherwise the minimal status card."""
    public_index = Path.home() / ".fleet-intel" / "public" / "index.html"
    if public_index.is_file():
        try:
            return HTMLResponse(public_index.read_text(encoding="utf-8"))
        except OSError:
            pass

    meta = hub_meta()
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Fleet Intel - Public</title>
<style>
  body {{ margin:0; background:#0f1419; color:#e6e6e6; font-family:system-ui,sans-serif;
         display:flex; align-items:center; justify-content:center; min-height:100vh; }}
  .card {{ background:#1a2332; border:1px solid #2a3648; border-radius:12px;
           padding:2rem; max-width:420px; text-align:center; }}
  h1 {{ font-size:1.25rem; margin:0 0 .5rem; }}
  p {{ color:#9aa7b8; font-size:.9rem; margin:.25rem 0; }}
  a {{ color:#58a6ff; text-decoration:none; }}
</style>
</head>
<body>
<div class="card">
  <h1>Fleet Intel Reports</h1>
  <p>Service operational - {meta.get("reports_count", 0)} reports stored.</p>
  <p>Generated {now}</p>
  <p><a href="/">Sign in to view reports</a></p>
</div>
</body>
</html>"""
    )


async def page_report(request: Request) -> HTMLResponse:
    report_id = request.path_params["report_id"]
    html_content = get_report_html(report_id)
    if not html_content:
        return HTMLResponse("<p>Report not found</p>", status_code=404)
    return HTMLResponse(html_content)


def build_app() -> Starlette:
    app = Starlette(
        routes=[
            Route("/", page_index),
            Route("/public", page_public),
            Route("/health", api_health),
            Route("/api/health", api_health),
            Route("/api/reports", api_reports_list),
            Route("/api/reports/publish", api_reports_publish, methods=["POST"]),
            Route("/reports/{report_id}", page_report),
        ],
    )
    app.add_middleware(_BasicAuthMiddleware, credentials=hub_auth_credentials())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def main() -> None:
    import uvicorn

    app = build_app()
    port = hub_port()
    host = hub_host()
    root_path = hub_root_path()
    credentials = hub_auth_credentials()
    if credentials:
        print(f"Intel Reports Hub on http://{host}:{port} (HTTP Basic auth: user={credentials[0]})")
    else:
        print(
            "WARNING: Intel Reports Hub serving WITHOUT authentication - set "
            "INTEL_REPORTS_HUB_USER/INTEL_REPORTS_HUB_PASS to enable HTTP Basic auth"
        )
    if root_path:
        print(f"root_path: {root_path} (paths stripped before routing - tailscale funnel subpath)")
    uvicorn.run(app, host=host, port=port, root_path=root_path, log_level="info")


if __name__ == "__main__":
    main()
