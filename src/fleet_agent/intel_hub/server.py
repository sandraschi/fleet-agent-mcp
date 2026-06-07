"""Mini HTTP server for Fleet Intel Reports — iPad / Tailscale access."""

from __future__ import annotations

import os

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from .render import render_index_page, wrap_markdown_report
from .store import get_report_html, hub_meta, list_reports, publish_report

DEFAULT_PORT = 11027
DEFAULT_HOST = "0.0.0.0"


def hub_host() -> str:
    return os.environ.get("INTEL_REPORTS_HUB_HOST", DEFAULT_HOST)


def hub_port() -> int:
    raw = os.environ.get("INTEL_REPORTS_HUB_PORT", str(DEFAULT_PORT))
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_PORT


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

    title = (body.get("title") or "").strip()
    source = (body.get("source") or "fleet").strip()
    html_body = body.get("html") or ""
    markdown = body.get("markdown") or ""
    summary = (body.get("summary") or "")[:500]
    tags = body.get("tags") if isinstance(body.get("tags"), list) else []

    if not title:
        return JSONResponse({"success": False, "error": "title required"}, status_code=400)

    if not html_body and markdown:
        html_body = wrap_markdown_report(
            title=title, source=source, markdown=markdown, summary=summary,
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
            Route("/health", api_health),
            Route("/api/health", api_health),
            Route("/api/reports", api_reports_list),
            Route("/api/reports/publish", api_reports_publish, methods=["POST"]),
            Route("/reports/{report_id}", page_report),
        ],
    )
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
    print(f"Intel Reports Hub on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
