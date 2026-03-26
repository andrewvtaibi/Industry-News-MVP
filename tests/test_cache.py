# tests/test_cache.py
# TDD tests for server/services/cache.py
# Written BEFORE implementation (red phase).

from __future__ import annotations

import time
import pytest

from server.services.cache import NewsCache


# ---------------------------------------------------------------------------
# A. Specification tests
# ---------------------------------------------------------------------------

class TestNewsCacheBasic:
    def test_set_and_get_returns_value(self):
        cache = NewsCache(default_ttl=60)
        cache.set("key1", [{"title": "Test"}])
        result = cache.get("key1")
        assert result == [{"title": "Test"}]

    def test_missing_key_returns_none(self):
        cache = NewsCache(default_ttl=60)
        assert cache.get("nonexistent") is None

    def test_overwrite_updates_value(self):
        cache = NewsCache(default_ttl=60)
        cache.set("key1", "first")
        cache.set("key1", "second")
        assert cache.get("key1") == "second"

    def test_different_keys_independent(self):
        cache = NewsCache(default_ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.get("a") == 1
        assert cache.get("b") == 2

    def test_none_value_can_be_stored(self):
        """Explicitly storing None should be retrievable."""
        cache = NewsCache(default_ttl=60)
        cache.set("key1", None)
        # None stored -> get returns None, but we can distinguish using has()
        assert cache.has("key1") is True

    def test_has_returns_false_for_missing(self):
        cache = NewsCache(default_ttl=60)
        assert cache.has("missing") is False

    def test_has_returns_true_for_present(self):
        cache = NewsCache(default_ttl=60)
        cache.set("present", "value")
        assert cache.has("present") is True

    def test_delete_removes_entry(self):
        cache = NewsCache(default_ttl=60)
        cache.set("key1", "data")
        cache.delete("key1")
        assert cache.get("key1") is None
        assert cache.has("key1") is False

    def test_delete_nonexistent_is_safe(self):
        cache = NewsCache(default_ttl=60)
        cache.delete("ghost")  # must not raise

    def test_clear_empties_cache(self):
        cache = NewsCache(default_ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_size_reflects_entries(self):
        cache = NewsCache(default_ttl=60)
        assert cache.size() == 0
        cache.set("a", 1)
        assert cache.size() == 1
        cache.set("b", 2)
        assert cache.size() == 2

    def test_make_key_is_deterministic(self):
        k1 = NewsCache.make_key("Pfizer", "headlines", 7)
        k2 = NewsCache.make_key("Pfizer", "headlines", 7)
        assert k1 == k2

    def test_make_key_differs_for_different_args(self):
        k1 = NewsCache.make_key("Pfizer", "headlines", 7)
        k2 = NewsCache.make_key("Pfizer", "headlines", 30)
        k3 = NewsCache.make_key("Pfizer", "press_releases", 7)
        assert k1 != k2
        assert k1 != k3

    def test_make_key_case_insensitive_query(self):
        """Same query, different case -> same key."""
        k1 = NewsCache.make_key("pfizer", "headlines", 7)
        k2 = NewsCache.make_key("PFIZER", "headlines", 7)
        assert k1 == k2


# ---------------------------------------------------------------------------
# B. TTL expiry tests
# ---------------------------------------------------------------------------

class TestNewsCacheTtl:
    def test_expired_entry_returns_none(self):
        cache = NewsCache(default_ttl=1)   # 1 second TTL
        cache.set("key1", "data")
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_non_expired_entry_still_accessible(self):
        cache = NewsCache(default_ttl=10)
        cache.set("key1", "data")
        time.sleep(0.05)
        assert cache.get("key1") == "data"

    def test_custom_ttl_overrides_default(self):
        cache = NewsCache(default_ttl=60)
        cache.set("key1", "data", ttl=1)
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_has_respects_ttl(self):
        cache = NewsCache(default_ttl=1)
        cache.set("key1", "data")
        time.sleep(1.1)
        assert cache.has("key1") is False


# ---------------------------------------------------------------------------
# C. Eviction / cleanup tests
# ---------------------------------------------------------------------------

class TestNewsCacheEviction:
    def test_prune_removes_expired_entries(self):
        cache = NewsCache(default_ttl=1)
        cache.set("exp", "data")
        cache.set("fresh", "data", ttl=60)
        time.sleep(1.1)
        removed = cache.prune()
        assert removed >= 1
        assert cache.has("exp") is False
        assert cache.has("fresh") is True

    def test_prune_returns_count_removed(self):
        cache = NewsCache(default_ttl=1)
        cache.set("a", 1)
        cache.set("b", 2)
        time.sleep(1.1)
        removed = cache.prune()
        assert removed == 2

    def test_size_decreases_after_prune(self):
        cache = NewsCache(default_ttl=1)
        cache.set("a", 1)
        cache.set("b", 2)
        time.sleep(1.1)
        cache.prune()
        assert cache.size() == 0


# ---------------------------------------------------------------------------
# D. Invariant checks
# ---------------------------------------------------------------------------

class TestNewsCacheInvariants:
    def test_get_never_raises_for_any_key(self):
        cache = NewsCache(default_ttl=60)
        for key in ["", None, "A" * 1000, "<script>", 12345]:
            try:
                cache.get(key)
            except Exception as exc:
                pytest.fail(f"cache.get raised unexpectedly: {exc}")

    def test_size_never_negative(self):
        cache = NewsCache(default_ttl=60)
        cache.delete("nonexistent")
        assert cache.size() >= 0
