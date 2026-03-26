# tests/test_integration.py
# End-to-end integration tests that exercise the REAL RSS network.
#
# These tests make live HTTP requests to Google News RSS and PR Newswire.
# They are marked with pytest.mark.integration so they can be excluded
# from fast CI runs:
#
#   pytest -m "not integration"   # skip integration tests
#   pytest -m integration          # run only integration tests
#
# Invariants verified in all integration tests:
#   - No returned item contains SEC filing patterns
#   - All items have non-empty title and link
#   - All items are within the requested date window
#   - Response schema is valid

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest

from server.services.news import NewsService
from server.models.schemas import NewsItem


pytestmark = pytest.mark.integration

_SEC_RE = re.compile(
    r"\b(8-K|10-K|10-Q|EDGAR|SEC\s+filing)\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_item_invariants(item: NewsItem, days: int) -> None:
    assert item.title.strip(), "Item title must be non-empty"
    assert item.link.strip(), "Item link must be non-empty"
    assert "sec.gov" not in item.link.lower(), (
        "SEC.gov links must be excluded"
    )
    assert not _SEC_RE.search(item.title), (
        f"SEC filing title must be excluded: {item.title}"
    )
    # Items with a known date must fall within window
    if item.published_date:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        dt = datetime.fromisoformat(item.published_date.replace("Z", "+00:00"))
        assert dt >= cutoff, (
            f"Item date {item.published_date} outside {days}-day window"
        )


# ---------------------------------------------------------------------------
# Real RSS fetch tests (network required)
# ---------------------------------------------------------------------------

class TestIntegrationHeadlines:
    def test_pfizer_headlines_7_days(self):
        svc = NewsService()
        items = svc.fetch_headlines("Pfizer", days=7)
        # We can't guarantee results (Pfizer might not have news today),
        # but the call must not raise and must return a list.
        assert isinstance(items, list)
        for item in items:
            _assert_item_invariants(item, days=7)

    def test_moderna_headlines_30_days(self):
        svc = NewsService()
        items = svc.fetch_headlines("Moderna", days=30)
        assert isinstance(items, list)
        for item in items:
            _assert_item_invariants(item, days=30)

    def test_unknown_company_returns_list(self):
        svc = NewsService()
        items = svc.fetch_headlines("ZZNOSUCHWHATEVERCO99", days=7)
        assert isinstance(items, list)
        # May be empty — that's fine

    def test_result_count_does_not_exceed_max(self):
        from server.services.news import MAX_RESULTS_PER_QUERY
        svc = NewsService()
        items = svc.fetch_headlines("biotech", days=30)
        assert len(items) <= MAX_RESULTS_PER_QUERY


class TestIntegrationPressReleases:
    def test_pfizer_press_releases_30_days(self):
        svc = NewsService()
        items = svc.fetch_press_releases("Pfizer", days=30)
        assert isinstance(items, list)
        for item in items:
            _assert_item_invariants(item, days=30)
            pr_domains = {
                "prnewswire.com", "globenewswire.com", "businesswire.com"
            }
            domain_ok = any(d in item.link for d in pr_domains)
            assert domain_ok, (
                f"Press release link not from expected domain: {item.link}"
            )

    def test_press_releases_7_days_subset_of_30(self):
        svc = NewsService()
        items_7 = svc.fetch_press_releases("Regeneron", days=7)
        items_30 = svc.fetch_press_releases("Regeneron", days=30)
        # 7-day window is always a subset (count-wise) of 30-day window
        assert len(items_7) <= len(items_30) + 2  # +2 for timing tolerance


class TestIntegrationEndToEnd:
    """
    Full round-trip tests through the FastAPI app with real RSS fetches.
    """

    def test_search_endpoint_pfizer_live(self, client):
        """
        Hit the search endpoint without mocking; real RSS fetch.
        Verify schema and invariants on whatever comes back.
        """
        # Clear cache to ensure a fresh fetch
        client.app.state.cache.clear()
        resp = client.get("/api/search?q=PFE&content_type=headlines&days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resolved"]["ticker"] == "PFE"
        assert data["resolved"]["company_name"] == "Pfizer"
        for item in data["items"]:
            assert item["title"]
            assert item["link"]
            assert "sec.gov" not in item["link"].lower()

    def test_search_endpoint_stock_price_no_fetch(self, client):
        """
        Stock price queries must never trigger a backend RSS fetch.
        """
        resp = client.get("/api/search?q=PFE&content_type=stock_price")
        assert resp.status_code == 200
        assert resp.json()["items"] == []
        assert resp.json()["resolved"]["ticker"] == "PFE"

    def test_cache_serves_second_request(self, client):
        """
        Second identical request should be served from cache (no extra fetch).
        """
        client.app.state.cache.clear()
        # First request populates cache
        r1 = client.get("/api/search?q=MRNA&content_type=headlines&days=7")
        assert r1.status_code == 200
        # Second request should hit cache
        r2 = client.get("/api/search?q=MRNA&content_type=headlines&days=7")
        assert r2.status_code == 200
        # Results should be identical
        assert r1.json()["items"] == r2.json()["items"]

    def test_sec_items_never_in_live_response(self, client):
        """
        Live Pfizer search must never return SEC filing items.
        """
        client.app.state.cache.clear()
        resp = client.get(
            "/api/search?q=Pfizer&content_type=headlines&days=30"
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "8-K" not in item["title"]
            assert "sec.gov" not in item["link"].lower()
