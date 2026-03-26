# tests/test_upload_route.py
# TDD tests for POST /api/upload

from __future__ import annotations

import io
from unittest.mock import patch

import pytest

from server.models.schemas import NewsItem


def _item(title="Test", link="https://example.com/test", source="example.com"):
    return NewsItem(
        title=title,
        link=link,
        source=source,
        published_date="2026-03-19T10:00:00Z",
    )


def _upload(client, csv_bytes: bytes, **kwargs):
    """Helper to POST to /api/upload with a CSV file."""
    files = {"file": ("companies.csv", io.BytesIO(csv_bytes), "text/csv")}
    return client.post("/api/upload", files=files, data=kwargs)


# ---------------------------------------------------------------------------
# A. Specification tests
# ---------------------------------------------------------------------------

class TestUploadSpec:
    def test_valid_csv_returns_200(self, client, valid_csv_bytes):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = _upload(client, valid_csv_bytes)
        assert resp.status_code == 200

    def test_response_has_required_keys(self, client, valid_csv_bytes):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = _upload(client, valid_csv_bytes)
        data = resp.json()
        for key in ("total_requested", "results", "errors"):
            assert key in data

    def test_total_requested_matches_csv_rows(self, client, valid_csv_bytes):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = _upload(client, valid_csv_bytes)
        assert resp.json()["total_requested"] == 3  # PFE, MRNA, REGN

    def test_results_count_matches_queries(self, client, valid_csv_bytes):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[_item()],
        ):
            resp = _upload(client, valid_csv_bytes)
        data = resp.json()
        assert len(data["results"]) == 3

    def test_stock_price_content_type_returns_empty_items(
        self, client, valid_csv_bytes
    ):
        resp = _upload(
            client, valid_csv_bytes, content_type="stock_price"
        )
        data = resp.json()
        assert resp.status_code == 200
        for result in data["results"]:
            assert result["items"] == []

    def test_press_releases_type_calls_correct_method(
        self, client, valid_csv_bytes
    ):
        # Clear cache so prior tests don't cause cache hits here
        client.app.state.cache.clear()
        called = []

        def _mock_pr(company, days):
            called.append(company)
            return []

        with patch.object(
            client.app.state.news_service,
            "fetch_press_releases",
            side_effect=_mock_pr,
        ):
            resp = _upload(
                client, valid_csv_bytes, content_type="press_releases"
            )
        assert resp.status_code == 200
        assert len(called) == 3


# ---------------------------------------------------------------------------
# B. Adversarial tests
# ---------------------------------------------------------------------------

class TestUploadAdversarial:
    def test_oversized_file_returns_400(self, client, oversized_csv_bytes):
        resp = _upload(client, oversized_csv_bytes)
        assert resp.status_code == 400
        assert "size" in resp.json()["detail"].lower()

    def test_too_many_rows_returns_400(self, client, too_many_rows_csv_bytes):
        resp = _upload(client, too_many_rows_csv_bytes)
        assert resp.status_code == 400
        assert "rows" in resp.json()["detail"].lower()

    def test_malformed_utf8_returns_400(self, client, malformed_csv_bytes):
        resp = _upload(client, malformed_csv_bytes)
        assert resp.status_code == 400
        assert "encoding" in resp.json()["detail"].lower()

    def test_empty_file_returns_400(self, client):
        resp = _upload(client, b"")
        assert resp.status_code == 400

    def test_xss_in_csv_values_sanitized(self, client):
        csv_data = b"company\n<script>alert(1)</script>\nPFE\n"
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = _upload(client, csv_data)
        assert resp.status_code == 200
        for result in resp.json()["results"]:
            assert "<script>" not in result["query"]

    def test_csv_with_only_header_returns_400(self, client):
        resp = _upload(client, b"company\n")
        assert resp.status_code == 400

    def test_invalid_content_type_ignored_or_default(self, client, valid_csv_bytes):
        """Invalid form content_type should fall back or return error, not 500."""
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = _upload(
                client, valid_csv_bytes, content_type="not_valid"
            )
        assert resp.status_code in (200, 422)


# ---------------------------------------------------------------------------
# C. Invariant checks
# ---------------------------------------------------------------------------

class TestUploadInvariants:
    def test_errors_list_is_always_present(self, client, valid_csv_bytes):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = _upload(client, valid_csv_bytes)
        assert isinstance(resp.json()["errors"], list)

    def test_results_list_is_always_present(self, client, valid_csv_bytes):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            return_value=[],
        ):
            resp = _upload(client, valid_csv_bytes)
        assert isinstance(resp.json()["results"], list)

    def test_response_never_leaks_traceback(self, client, valid_csv_bytes):
        with patch.object(
            client.app.state.news_service,
            "fetch_headlines",
            side_effect=RuntimeError("boom"),
        ):
            resp = _upload(client, valid_csv_bytes)
        if resp.status_code >= 500:
            assert "Traceback" not in resp.text
            assert "RuntimeError" not in resp.text
