# tests/test_news_service.py
# TDD tests for server/services/news.py
# All RSS fetches are mocked; no network calls in unit tests.

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

from server.services.news import NewsService
from server.models.schemas import NewsItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rfc(days_ago: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def _make_rss(title: str, link: str, days_ago: int, source: str = "test") -> bytes:
    return f"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>{source}</title>
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <pubDate>{_rfc(days_ago)}</pubDate>
      <description>Summary of {title}.</description>
    </item>
  </channel>
</rss>""".encode("utf-8")


# ---------------------------------------------------------------------------
# A. Specification tests
# ---------------------------------------------------------------------------

class TestNewsServiceFetchHeadlines:
    def test_returns_list_of_news_items(self, mock_rss_headlines):
        with patch("server.services.news._fetch_raw", return_value=mock_rss_headlines):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)
        assert isinstance(results, list)
        assert all(isinstance(item, NewsItem) for item in results)

    def test_items_have_required_fields(self, mock_rss_headlines):
        with patch("server.services.news._fetch_raw", return_value=mock_rss_headlines):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)
        for item in results:
            assert item.title
            assert item.link
            assert item.source

    def test_items_within_7_day_window(self, mock_rss_headlines):
        with patch("server.services.news._fetch_raw", return_value=mock_rss_headlines):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for item in results:
            if item.published_date:
                dt = datetime.fromisoformat(
                    item.published_date.replace("Z", "+00:00")
                )
                assert dt >= cutoff

    def test_items_within_30_day_window(self):
        rss = _make_rss(
            "Pfizer 25-day old story",
            "https://example.com/pfizer-old",
            days_ago=25,
        )
        with patch("server.services.news._fetch_raw", return_value=rss):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=30)
        assert len(results) >= 1

    def test_old_items_excluded_from_7_day_window(self, mock_rss_old_item):
        with patch("server.services.news._fetch_raw", return_value=mock_rss_old_item):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)
        assert len(results) == 0

    def test_empty_bytes_returns_empty_list(self):
        with patch("server.services.news._fetch_raw", return_value=b""):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)
        assert results == []

    def test_fetch_failure_returns_empty_list(self):
        with patch(
            "server.services.news._fetch_raw",
            side_effect=Exception("network error"),
        ):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)
        assert results == []


class TestNewsServiceFetchPressReleases:
    def test_returns_list_of_news_items(self, mock_rss_press_release):
        with patch("server.services.news._fetch_raw", return_value=mock_rss_press_release):
            svc = NewsService()
            results = svc.fetch_press_releases("Pfizer", days=7)
        assert isinstance(results, list)

    def test_press_release_link_from_expected_domains(
        self, mock_rss_press_release
    ):
        with patch("server.services.news._fetch_raw", return_value=mock_rss_press_release):
            svc = NewsService()
            results = svc.fetch_press_releases("Pfizer", days=7)
        pr_domains = {"prnewswire.com", "globenewswire.com", "businesswire.com"}
        for item in results:
            domain_ok = any(d in item.link for d in pr_domains)
            # PR items from the mock should come from prnewswire
            assert domain_ok, f"Unexpected domain in link: {item.link}"


# ---------------------------------------------------------------------------
# B. Adversarial / filtering tests
# ---------------------------------------------------------------------------

class TestNewsServiceFiltering:
    def test_sec_filing_items_excluded(self, mock_rss_sec_item):
        with patch("server.services.news._fetch_raw", return_value=mock_rss_sec_item):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)
        for item in results:
            assert "8-K" not in item.title
            assert "sec.gov" not in item.link.lower()

    def test_arxiv_items_excluded(self):
        rss = _make_rss(
            "arXiv preprint on genomics q-bio",
            "https://arxiv.org/abs/2301.12345",
            days_ago=1,
        )
        with patch("server.services.news._fetch_raw", return_value=rss):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)
        for item in results:
            assert "arxiv" not in item.link.lower()

    def test_duplicate_titles_deduplicated(self):
        rss = _make_rss(
            "Pfizer Q1 Results",
            "https://example.com/pfizer-q1",
            days_ago=1,
        )
        # Return the same feed twice via two separate calls
        with patch(
            "server.services.news._fetch_raw",
            return_value=rss,
        ):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)

        titles = [item.title for item in results]
        assert len(titles) == len(set(titles))


# ---------------------------------------------------------------------------
# C. Invariant checks
# ---------------------------------------------------------------------------

class TestNewsServiceInvariants:
    def test_no_item_has_empty_title(self, mock_rss_headlines):
        with patch("server.services.news._fetch_raw", return_value=mock_rss_headlines):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)
        for item in results:
            assert item.title.strip() != ""

    def test_no_item_has_empty_link(self, mock_rss_headlines):
        with patch("server.services.news._fetch_raw", return_value=mock_rss_headlines):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)
        for item in results:
            assert item.link.strip() != ""

    def test_result_count_bounded(self):
        """Fetch result must not exceed MAX_RESULTS_PER_QUERY."""
        # Build a large RSS with 60 items
        items_xml = "".join(
            f"""<item>
                <title>Item {i}</title>
                <link>https://example.com/{i}</link>
                <pubDate>{_rfc(1)}</pubDate>
              </item>"""
            for i in range(60)
        )
        rss = f"""<?xml version="1.0"?>
<rss version="2.0">
  <channel><title>Test</title>{items_xml}</channel>
</rss>""".encode("utf-8")

        with patch("server.services.news._fetch_raw", return_value=rss):
            svc = NewsService()
            results = svc.fetch_headlines("Pfizer", days=7)

        from server.services.news import MAX_RESULTS_PER_QUERY
        assert len(results) <= MAX_RESULTS_PER_QUERY
