"""Tests for Intel Reports Hub store + render."""


from fleet_agent.intel_hub.render import markdown_to_html, render_index_page, wrap_markdown_report
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
