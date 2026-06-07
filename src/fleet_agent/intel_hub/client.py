"""Publish reports to the Intel Hub (HTTP with filesystem fallback)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .render import wrap_markdown_report
from .server import hub_port
from .store import publish_report

logger = logging.getLogger("fleet_agent.intel_hub.client")


def hub_base_url() -> str:
    return os.environ.get("INTEL_REPORTS_HUB_URL", f"http://127.0.0.1:{hub_port()}").rstrip("/")


async def publish_to_hub(
    *,
    title: str,
    source: str = "fritz",
    markdown: str = "",
    html: str = "",
    summary: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """POST to hub API; fall back to direct store write if hub is down."""
    if not html and markdown:
        html = wrap_markdown_report(title=title, source=source, markdown=markdown, summary=summary)

    payload = {
        "title": title,
        "source": source,
        "html": html,
        "markdown": markdown,
        "summary": summary,
        "tags": tags or [],
    }

    url = f"{hub_base_url()}/api/reports/publish"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                data["via"] = "http"
                return data
            logger.warning("Hub publish HTTP %s: %s", resp.status_code, resp.text[:200])
    except httpx.HTTPError as exc:
        logger.info("Hub unreachable (%s), writing to store directly", exc)

    try:
        result = publish_report(
            title=title,
            source=source,
            html=html,
            summary=summary,
            tags=tags,
        )
        result["via"] = "filesystem"
        result["hub_url"] = hub_base_url()
        return result
    except ValueError as exc:
        return {"success": False, "message": str(exc), "via": "none"}
