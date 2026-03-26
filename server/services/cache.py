# server/services/cache.py
# TTL-based in-memory cache for RSS fetch results.
#
# Inputs:  arbitrary Python values (lists of NewsItem dicts, etc.)
# Outputs: cached value or None on miss / expiry
# Assumptions:
#   - Single-process; no distributed/shared cache needed for MVP.
#   - Entries expire passively (on get) or actively (via prune()).
#   - Thread-safe via a single threading.Lock (sufficient for Uvicorn
#     single-worker or FastAPI's sync+async mix).

from __future__ import annotations

import hashlib
import time
import threading
from typing import Any, Optional


class NewsCache:
    """
    Simple TTL key-value cache.

    Entry lifecycle:
        set(key, value)   -> stored with expiry = now + ttl
        get(key)          -> returns value if not expired, else None
        prune()           -> explicitly removes all expired entries
    """

    def __init__(self, default_ttl: int = 900) -> None:
        """
        Args:
            default_ttl: seconds before entries expire (default 15 min).
        """
        self._default_ttl = default_ttl
        # _store: key -> (value, expiry_timestamp)
        self._store: dict[Any, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        """Store *value* under *key* with the given TTL (seconds)."""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expiry = time.monotonic() + effective_ttl
        with self._lock:
            self._store[key] = (value, expiry)

    def get(self, key: Any) -> Any:
        """
        Return the cached value for *key*, or None if absent / expired.
        Expired entries are lazily removed on access.
        """
        try:
            with self._lock:
                entry = self._store.get(key)
                if entry is None:
                    return None
                value, expiry = entry
                if time.monotonic() > expiry:
                    del self._store[key]
                    return None
                return value
        except Exception:
            return None

    def has(self, key: Any) -> bool:
        """Return True if *key* exists and has not expired."""
        return self.get(key) is not None or self._has_unexpired(key)

    def delete(self, key: Any) -> None:
        """Remove *key* from the cache. No-op if absent."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        """Return the number of entries (including potentially expired ones)."""
        with self._lock:
            return len(self._store)

    def prune(self) -> int:
        """
        Remove all expired entries. Returns the number removed.
        Call periodically to prevent unbounded memory growth.
        """
        now = time.monotonic()
        removed = 0
        with self._lock:
            expired_keys = [
                k for k, (_, exp) in self._store.items() if now > exp
            ]
            for k in expired_keys:
                del self._store[k]
                removed += 1
        return removed

    # ------------------------------------------------------------------
    # Key construction
    # ------------------------------------------------------------------

    @staticmethod
    def make_key(query: str, content_type: str, days: int) -> str:
        """
        Build a deterministic cache key from search parameters.
        Query is normalized to lowercase so "Pfizer" == "pfizer".
        """
        normalized = f"{(query or '').lower()}|{content_type}|{days}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _has_unexpired(self, key: Any) -> bool:
        """Check presence without consuming the value."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            _, expiry = entry
            if time.monotonic() > expiry:
                del self._store[key]
                return False
            return True
