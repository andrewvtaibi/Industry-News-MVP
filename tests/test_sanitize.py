# tests/test_sanitize.py
# TDD tests for server/security/sanitize.py
# Written BEFORE implementation (red phase).

from __future__ import annotations

import io
import pytest

from server.security.sanitize import sanitize_query, validate_csv


# ---------------------------------------------------------------------------
# A. Specification tests — sanitize_query
# ---------------------------------------------------------------------------

class TestSanitizeQuery:
    def test_plain_company_name_unchanged(self):
        assert sanitize_query("Pfizer") == "Pfizer"

    def test_plain_ticker_unchanged(self):
        assert sanitize_query("PFE") == "PFE"

    def test_strips_leading_trailing_whitespace(self):
        assert sanitize_query("  Pfizer  ") == "Pfizer"

    def test_allows_ampersand(self):
        result = sanitize_query("Johnson & Johnson")
        assert "Johnson" in result

    def test_allows_hyphen(self):
        result = sanitize_query("Bristol-Myers Squibb")
        assert "Bristol" in result

    def test_allows_period(self):
        result = sanitize_query("Abbott Labs.")
        assert "Abbott" in result

    def test_truncates_to_100_chars(self):
        long = "A" * 150
        result = sanitize_query(long)
        assert len(result) <= 100

    def test_empty_string_returns_empty(self):
        assert sanitize_query("") == ""

    def test_none_coerced_to_empty(self):
        assert sanitize_query(None) == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# B. Adversarial tests — sanitize_query
# ---------------------------------------------------------------------------

class TestSanitizeQueryAdversarial:
    def test_strips_html_script_tag(self):
        result = sanitize_query("<script>alert(1)</script>")
        assert "<script>" not in result
        assert "alert" not in result

    def test_strips_html_img_tag(self):
        result = sanitize_query('<img src=x onerror="alert(1)">')
        assert "<img" not in result
        assert "onerror" not in result

    def test_strips_angle_brackets(self):
        result = sanitize_query("<Pfizer>")
        assert "<" not in result
        assert ">" not in result

    def test_strips_single_quotes(self):
        result = sanitize_query("'; DROP TABLE items; --")
        assert "'" not in result

    def test_strips_semicolons(self):
        result = sanitize_query("Pfizer; rm -rf /")
        assert ";" not in result

    def test_strips_double_quotes(self):
        result = sanitize_query('"Pfizer"')
        assert '"' not in result

    def test_null_byte_removed(self):
        result = sanitize_query("Pfizer\x00Inc")
        assert "\x00" not in result

    def test_newline_removed(self):
        result = sanitize_query("Pfizer\nInc")
        assert "\n" not in result

    def test_tab_removed(self):
        result = sanitize_query("Pfizer\tInc")
        assert "\t" not in result

    def test_url_encoded_brackets_stripped(self):
        result = sanitize_query("%3Cscript%3E")
        assert "<" not in result
        assert ">" not in result


# ---------------------------------------------------------------------------
# A. Specification tests — validate_csv
# ---------------------------------------------------------------------------

class TestValidateCsv:
    def test_valid_single_column_tickers(self, valid_csv_bytes):
        result = validate_csv(io.BytesIO(valid_csv_bytes))
        assert isinstance(result, list)
        assert "PFE" in result
        assert "MRNA" in result
        assert "REGN" in result

    def test_header_row_excluded(self, valid_csv_bytes):
        """The header 'company' must not appear in output."""
        result = validate_csv(io.BytesIO(valid_csv_bytes))
        assert "company" not in result

    def test_single_column_no_header(self):
        data = b"PFE\nMRNA\nREGN\n"
        result = validate_csv(io.BytesIO(data))
        assert "PFE" in result

    def test_empty_rows_skipped(self):
        data = b"company\nPFE\n\nMRNA\n\n"
        result = validate_csv(io.BytesIO(data))
        assert "" not in result
        assert len(result) == 2

    def test_whitespace_stripped_from_values(self):
        data = b"company\n  PFE  \n MRNA\n"
        result = validate_csv(io.BytesIO(data))
        assert "PFE" in result
        assert "MRNA" in result

    def test_csv_with_multiple_columns_uses_first(self):
        data = b"ticker,name\nPFE,Pfizer\nMRNA,Moderna\n"
        result = validate_csv(io.BytesIO(data))
        assert "PFE" in result
        assert "MRNA" in result


# ---------------------------------------------------------------------------
# B. Adversarial tests — validate_csv
# ---------------------------------------------------------------------------

class TestValidateCsvAdversarial:
    def test_oversized_file_raises(self, oversized_csv_bytes):
        import pytest
        with pytest.raises(ValueError, match="size"):
            validate_csv(io.BytesIO(oversized_csv_bytes))

    def test_too_many_rows_raises(self, too_many_rows_csv_bytes):
        with pytest.raises(ValueError, match="rows"):
            validate_csv(io.BytesIO(too_many_rows_csv_bytes))

    def test_malformed_utf8_raises(self, malformed_csv_bytes):
        with pytest.raises(ValueError, match="encoding"):
            validate_csv(io.BytesIO(malformed_csv_bytes))

    def test_empty_file_raises(self):
        with pytest.raises(ValueError, match="empty"):
            validate_csv(io.BytesIO(b""))

    def test_xss_values_sanitized(self):
        data = b"company\n<script>alert(1)</script>\nPFE\n"
        result = validate_csv(io.BytesIO(data))
        for val in result:
            assert "<script>" not in val

    def test_sql_injection_values_sanitized(self):
        data = b"company\nPFE\n'; DROP TABLE items; --\n"
        result = validate_csv(io.BytesIO(data))
        for val in result:
            assert "'" not in val


# ---------------------------------------------------------------------------
# C. Invariant checks
# ---------------------------------------------------------------------------

class TestSanitizeInvariants:
    def test_sanitize_query_never_raises(self):
        """sanitize_query must not raise for any string input."""
        for payload in [
            "", "   ", "Pfizer", "<script>", "A" * 1000,
            "\x00\x01\x02", "'; DROP TABLE x; --",
        ]:
            sanitize_query(payload)  # must not raise

    def test_validate_csv_result_entries_are_strings(self, valid_csv_bytes):
        result = validate_csv(io.BytesIO(valid_csv_bytes))
        assert all(isinstance(v, str) for v in result)

    def test_validate_csv_result_no_empty_strings(self, valid_csv_bytes):
        result = validate_csv(io.BytesIO(valid_csv_bytes))
        assert all(len(v) > 0 for v in result)
