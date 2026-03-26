# tests/test_search_route.py
# TDD tests for GET /api/search

from __future__ import annotations

from unittest.mock import patch

import pytest

from server.models.schemas import ContentType, NewsItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pfizer_item():
    return NewsItem(
        title="Pfizer reports positive results",
        link="https://example.com/pfizer",
        source="example.com",
        published_date="2026-03-19T10:00:00Z",
        summary_snippet="Pfizer announced...",
    )


# ---------------------------------------------------------------------------
# A. Specification tests
# ---------------------------------------------------------------------------

class TestSearchRouteSpec:
    def test_health_check_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_search_headlines_returns_200(self, client):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[_pfizer_item()],
        ):
            resp = client.get("/api/search?q=PFE&content_type=headlines&days=7")
        assert resp.status_code == 200

    def test_search_response_has_required_keys(self, client):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[_pfizer_item()],
        ):
            resp = client.get("/api/search?q=PFE")
        data = resp.json()
        for key in ("query", "resolved", "content_type", "days", "items"):
            assert key in data, f"Missing key: {key}"

    def test_search_resolves_known_ticker(self, client):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = client.get("/api/search?q=PFE")
        data = resp.json()
        assert data["resolved"]["found"] is True
        assert data["resolved"]["ticker"] == "PFE"
        assert data["resolved"]["company_name"] == "Pfizer"

    def test_search_unknown_query_found_false(self, client):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = client.get("/api/search?q=ZZZUNKNOWN")
        data = resp.json()
        assert data["resolved"]["found"] is False
        assert data["resolved"]["ticker"] is None

    def test_search_stock_price_returns_empty_items(self, client):
        resp = client.get("/api/search?q=PFE&content_type=stock_price")
        data = resp.json()
        assert resp.status_code == 200
        assert data["items"] == []
        assert data["content_type"] == "stock_price"

    def test_search_30_day_window(self, client):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = client.get("/api/search?q=PFE&days=30")
        assert resp.status_code == 200
        assert resp.json()["days"] == 30

    def test_search_press_releases_calls_correct_method(self, client):
        called_with = {}
        original = client.app.state.news_service.fetch_press_releases

        def _mock(company, days):
            called_with["company"] = company
            called_with["days"] = days
            return []

        with patch.object(
            client.app.state.news_service,
            "fetch_press_releases",
            side_effect=_mock,
        ):
            resp = client.get("/api/search?q=PFE&content_type=press_releases")
        assert resp.status_code == 200
        assert called_with.get("company") == "Pfizer"

    def test_search_items_have_correct_schema(self, client):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[_pfizer_item()],
        ):
            resp = client.get("/api/search?q=PFE")
        items = resp.json()["items"]
        assert len(items) == 1
        for key in ("title", "link", "source"):
            assert key in items[0]


# ---------------------------------------------------------------------------
# B. Adversarial tests
# ---------------------------------------------------------------------------

class TestSearchRouteAdversarial:
    def test_empty_query_returns_400(self, client):
        resp = client.get("/api/search?q=")
        assert resp.status_code in (400, 422)

    def test_missing_query_returns_422(self, client):
        resp = client.get("/api/search")
        assert resp.status_code == 422

    def test_xss_query_sanitized_and_proceeds(self, client):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = client.get("/api/search?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E")
        # Should either return 400 (empty after sanitize) or 200 with empty items
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            assert resp.json()["items"] == []

    def test_invalid_content_type_returns_422(self, client):
        resp = client.get("/api/search?q=PFE&content_type=invalid_type")
        assert resp.status_code == 422

    def test_invalid_days_returns_422(self, client):
        resp = client.get("/api/search?q=PFE&days=99")
        assert resp.status_code == 422

    def test_very_long_query_returns_422_or_sanitized(self, client):
        long_q = "A" * 200
        resp = client.get(f"/api/search?q={long_q}")
        assert resp.status_code in (200, 400, 422)


# ---------------------------------------------------------------------------
# C. Invariant checks
# ---------------------------------------------------------------------------

class TestSearchRouteInvariants:
    def test_response_content_type_matches_request(self, client):
        for ct in ("headlines", "press_releases", "stock_price"):
            with patch.object(
                client.app.state.news_service,
                "fetch_headlines",
                return_value=[],
            ):
                with patch.object(
                    client.app.state.news_service,
                    "fetch_press_releases",
                    return_value=[],
                ):
                    resp = client.get(
                        f"/api/search?q=PFE&content_type={ct}"
                    )
            assert resp.json()["content_type"] == ct

    def test_security_headers_present(self, client):
        resp = client.get("/api/health")
        assert "content-security-policy" in {
            k.lower() for k in resp.headers
        }
        assert "x-content-type-options" in {k.lower() for k in resp.headers}

    def test_response_never_leaks_traceback(self, client):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            side_effect=RuntimeError("boom"),
        ):
            resp = client.get("/api/search?q=PFE")
        if resp.status_code == 500:
            body = resp.text
            assert "Traceback" not in body
            assert "RuntimeError" not in body
