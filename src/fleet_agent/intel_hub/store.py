"""Filesystem-backed catalog for Fritz + AIWatcher intel reports."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import settings

_DEFAULT_ROOT = Path.home() / ".fleet-intel"


def reports_root() -> Path:
    env = __import__("os").environ.get("INTEL_REPORTS_DIR", "").strip()
    root = Path(env) if env else _DEFAULT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    (root / "reports").mkdir(parents=True, exist_ok=True)
    return root


def _catalog_path() -> Path:
    return reports_root() / "index.json"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "report"


def _load_catalog() -> list[dict[str, Any]]:
    path = _catalog_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_catalog(entries: list[dict[str, Any]]) -> None:
    path = _catalog_path()
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def publish_report(
    *,
    title: str,
    source: str,
    html: str,
    summary: str = "",
    tags: list[str] | None = None,
    report_id: str | None = None,
) -> dict[str, Any]:
    """Write HTML report + update catalog. Returns metadata dict."""
    if not title.strip():
        raise ValueError("title is required")
    if not html.strip():
        raise ValueError("html is required")

    rid = report_id or str(uuid.uuid4())[:12]
    now = datetime.now(UTC).isoformat()
    slug = _slugify(title)
    html_path = reports_root() / "reports" / f"{rid}.html"
    html_path.write_text(html, encoding="utf-8")

    entry = {
        "id": rid,
        "title": title[:200],
        "source": source,
        "summary": summary[:500],
        "tags": tags or [],
        "slug": slug,
        "created_at": now,
        "html_path": str(html_path),
    }

    catalog = _load_catalog()
    catalog = [e for e in catalog if e.get("id") != rid]
    catalog.insert(0, entry)
    catalog = catalog[:200]
    _save_catalog(catalog)

    return {
        "success": True,
        "id": rid,
        "title": entry["title"],
        "source": source,
        "url_path": f"/reports/{rid}",
        "created_at": now,
        "reports_dir": str(reports_root()),
    }


def list_reports(*, limit: int = 50) -> list[dict[str, Any]]:
    catalog = _load_catalog()
    return catalog[: max(1, limit)]


def get_report(report_id: str) -> dict[str, Any] | None:
    for entry in _load_catalog():
        if entry.get("id") == report_id:
            return entry
    return None


def get_report_html(report_id: str) -> str | None:
    entry = get_report(report_id)
    if not entry:
        path = reports_root() / "reports" / f"{report_id}.html"
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return None
    path = Path(entry.get("html_path") or "")
    if path.is_file():
        return path.read_text(encoding="utf-8")
    fallback = reports_root() / "reports" / f"{report_id}.html"
    if fallback.is_file():
        return fallback.read_text(encoding="utf-8")
    return None


def hub_meta() -> dict[str, Any]:
    return {
        "name": "Fleet Intel Reports",
        "agent": settings.agent_name,
        "reports_count": len(_load_catalog()),
        "reports_dir": str(reports_root()),
    }
