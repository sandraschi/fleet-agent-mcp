"""Tests for Intel Reports Hub store + render."""

from fleet_agent.intel_hub.public_site import _parse_tags
from fleet_agent.intel_hub.render import (
    markdown_to_html,
    render_index_page,
    render_report_page,
    wrap_markdown_report,
)
from fleet_agent.intel_hub.server import _route_path
from fleet_agent.intel_hub.store import list_reports, publish_report


class TestIntelHubRender:
    def test_markdown_headings(self):
        html = markdown_to_html("# Title\n\n## Section\n\n- item one")
        assert "<h1>Title</h1>" in html
        assert "<h2>Section</h2>" in html
        assert "<li>" in html

    def test_wrap_report_has_doctype(self):
        page = wrap_markdown_report(
            title="Test Report",
            source="fritz",
            markdown="# Hello\n\nBody text.",
        )
        assert "<!DOCTYPE html>" in page
        assert "Test Report" in page
        assert "Fritz" in page

    def test_index_page_empty(self):
        page = render_index_page([])
        assert "No reports yet" in page

    def test_index_card_links_use_funnel_base(self):
        """Card taps must survive the funnel subpath (iPad white-page bug).

        A bare relative "reports/..." resolves to /reports/... when the index
        URL is /intel (no trailing slash) - outside the funnel mapping.
        """
        reports = [
            {"id": "abc123", "title": "T", "summary": "S", "source": "fritz", "created_at": ""}
        ]
        page = render_index_page(reports, base="/intel")
        assert 'href="/intel/reports/abc123"' in page
        assert 'href="reports/' not in page

    def test_index_card_links_without_base(self):
        reports = [
            {"id": "abc123", "title": "T", "summary": "", "source": "fritz", "created_at": ""}
        ]
        assert 'href="/reports/abc123"' in render_index_page(reports)

    def test_report_back_link_uses_funnel_base(self):
        page = render_report_page(
            title="R", source="fritz", created_at="", body_html="<p>x</p>", base="/intel"
        )
        assert 'href="/intel/"' in page
        plain = render_report_page(title="R", source="fritz", created_at="", body_html="<p>x</p>")
        assert 'class="back" href="/"' in plain


class TestRoutePathStripping:
    """uvicorn keeps root_path prepended in scope["path"]; auth + links must
    compare the stripped route path so /intel/health stays public."""

    def test_strips_funnel_prefix(self):
        assert _route_path({"path": "/intel/health", "root_path": "/intel"}) == "/health"
        assert _route_path({"path": "/intel/", "root_path": "/intel"}) == "/"
        assert _route_path({"path": "/intel", "root_path": "/intel"}) == "/"

    def test_leaves_other_paths_alone(self):
        assert _route_path({"path": "/health", "root_path": ""}) == "/health"
        assert _route_path({"path": "/health", "root_path": "/intel"}) == "/health"
        assert _route_path({"path": "/intelreports/x", "root_path": "/intel"}) == "/intelreports/x"


class TestIntelHubStore:
    def test_publish_and_list(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INTEL_REPORTS_DIR", str(tmp_path))
        html = wrap_markdown_report(
            title="Pulse",
            source="fritz",
            markdown="# Fleet Pulse",
        )
        result = publish_report(title="Fleet Pulse", source="fritz", html=html)
        assert result["success"] is True
        assert result["id"]

        reports = list_reports(limit=10)
        assert len(reports) == 1
        assert reports[0]["title"] == "Fleet Pulse"
        assert reports[0]["source"] == "fritz"


class TestPublicSiteTagParsing:
    """The dev-diary digest groups entries by repo via their `repo:` tag.

    vla_mcp stores tags as a JSON array; parsing it as comma-separated text
    swallowed every repo tag into a single "other" bucket. These tests lock
    the JSON-array parsing so the per-repo drilldown actually has rows.
    """

    def test_parse_json_array_tags(self):
        assert _parse_tags('["repo:vla-mcp", "spec"]') == ["repo:vla-mcp", "spec"]

    def test_parse_legacy_csv_tags(self):
        assert _parse_tags("repo:plex-mcp, feature") == ["repo:plex-mcp", "feature"]

    def test_parse_empty_and_none(self):
        assert _parse_tags("") == []
        assert _parse_tags(None) == []
        assert _parse_tags("   ") == []

    def test_parse_malformed_json_falls_back(self):
        # Not valid JSON but not CSV either; should not raise and not crash.
        assert isinstance(_parse_tags('["unterminated'), list)
