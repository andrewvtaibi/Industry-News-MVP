# server/services/news.py
# Fetches and filters company-specific headlines and press releases via RSS.
#
# Inputs:  company name string, days (7 or 30)
# Outputs: list[NewsItem] — validated, filtered, deduplicated
# Assumptions:
#   - Google News RSS is the primary source for headlines.
#   - PR Newswire / GlobeNewswire / BusinessWire for press releases.
#   - app/fetch.py (fetch_bytes, parse_and_normalize) handles HTTP + parsing.
#   - All filtering is post-fetch; no pre-fetch scoping beyond the query URL.
#
# Failure modes:
#   - Network errors: return [] (never raise to caller)
#   - Malformed RSS: feedparser handles gracefully, empty list returned
#   - Items outside date window: excluded silently

from __future__ import annotations

import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional

from server.models.schemas import NewsItem

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RESULTS_PER_QUERY = 50

# Patterns that identify SEC filings or EDGAR content
_SEC_PATTERNS = re.compile(
    r"\b(8-K|10-K|10-Q|EDGAR|SEC\s+filing|Form\s+8|Form\s+10|"
    r"proxy\s+statement|DEF\s+14A|S-1\s+filing|prospectus)\b",
    re.IGNORECASE,
)
_SEC_DOMAINS = {"sec.gov", "edgar.sec.gov"}

# arXiv domain
_ARXIV_DOMAIN = "arxiv.org"

# Press-release source domains (used for domain-based filtering)
_PR_DOMAINS = {"prnewswire.com", "globenewswire.com", "businesswire.com"}


# ---------------------------------------------------------------------------
# Internal HTTP helper (thin wrapper so tests can patch a single symbol)
# ---------------------------------------------------------------------------

def _fetch_raw(url: str) -> bytes:
    """
    Fetch *url* and return raw bytes.
    Delegates entirely to app.fetch.fetch_bytes.
    Never raises; returns b"" on any failure.
    """
    try:
        from app.fetch import fetch_bytes
        return fetch_bytes(url, timeout_sec=15, max_retries=2)
    except Exception:
        return b""


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------

def _headlines_url(company: str) -> str:
    q = urllib.parse.quote_plus(company)
    return (
        f"https://news.google.com/rss/search"
        f"?q={q}&hl=en-US&gl=US&ceid=US%3Aen"
    )


def _press_release_url(company: str) -> str:
    q = urllib.parse.quote_plus(
        f"{company} "
        "site:prnewswire.com OR site:globenewswire.com OR site:businesswire.com"
    )
    return (
        f"https://news.google.com/rss/search"
        f"?q={q}&hl=en-US&gl=US&ceid=US%3Aen"
    )


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

def _parse_date(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return None


def _is_within_window(item: dict, cutoff: datetime) -> bool:
    dt = _parse_date(item.get("published_iso"))
    if dt is None:
        return True  # keep items with missing dates (may be very recent)
    return dt >= cutoff


def _is_sec_item(item: dict) -> bool:
    title = item.get("title", "")
    link = item.get("link", "")
    if _SEC_PATTERNS.search(title):
        return True
    try:
        from urllib.parse import urlparse
        domain = urlparse(link).hostname or ""
        return domain in _SEC_DOMAINS
    except Exception:
        return False


def _is_arxiv_item(item: dict) -> bool:
    link = item.get("link", "")
    try:
        from urllib.parse import urlparse
        domain = (urlparse(link).hostname or "").lower()
        return _ARXIV_DOMAIN in domain
    except Exception:
        return False


def _to_news_item(item: dict) -> Optional[NewsItem]:
    """
    Convert a normalized feed dict to a NewsItem.
    Returns None if mandatory fields are missing.
    """
    title = (item.get("title") or "").strip()
    link = (item.get("link") or "").strip()
    if not title or not link:
        return None
    source = (item.get("source") or "").strip() or _domain_from(link)
    summary = (item.get("summary") or "")[:300].strip() or None
    return NewsItem(
        title=title,
        link=link,
        source=source,
        published_date=item.get("published_iso"),
        summary_snippet=summary,
    )


def _domain_from(link: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(link).hostname or ""
    except Exception:
        return ""


def _deduplicate(items: list[dict]) -> list[dict]:
    seen_titles: set[str] = set()
    seen_links: set[str] = set()
    out: list[dict] = []
    for it in items:
        t = (it.get("title") or "").lower().strip()
        l = (it.get("link") or "").lower().strip()
        if t in seen_titles or l in seen_links:
            continue
        if t:
            seen_titles.add(t)
        if l:
            seen_links.add(l)
        out.append(it)
    return out


def _filter_and_convert(
    raw_items: list[dict],
    cutoff: datetime,
    *,
    pr_only: bool = False,
) -> list[NewsItem]:
    """
    Apply date window, SEC/arXiv exclusion, optional press-release domain
    filter, deduplication, and conversion to NewsItem.
    """
    filtered = [
        it for it in raw_items
        if _is_within_window(it, cutoff)
        and not _is_sec_item(it)
        and not _is_arxiv_item(it)
    ]

    # For press releases, scoping is handled by the query URL itself
    # (site:prnewswire.com OR site:globenewswire.com OR site:businesswire.com).
    # Google News returns redirect links (news.google.com/...) for all items,
    # so we cannot reliably filter by link domain here.

    filtered = _deduplicate(filtered)[:MAX_RESULTS_PER_QUERY]

    news_items: list[NewsItem] = []
    for it in filtered:
        ni = _to_news_item(it)
        if ni:
            news_items.append(ni)

    return news_items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class NewsService:
    """
    Fetches company-specific news from RSS feeds.
    All methods are synchronous; they are run in a thread executor
    from the async route handlers.
    """

    def fetch_headlines(self, company: str, days: int) -> list[NewsItem]:
        """
        Fetch recent headlines mentioning *company* from Google News RSS.
        Returns [] on any failure.
        """
        try:
            url = _headlines_url(company)
            raw = _fetch_raw(url)
            if not raw:
                return []
            from app.fetch import parse_and_normalize
            _meta, items = parse_and_normalize(raw)
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            return _filter_and_convert(items, cutoff, pr_only=False)
        except Exception:
            return []

    def fetch_press_releases(self, company: str, days: int) -> list[NewsItem]:
        """
        Fetch recent press releases for *company* scoped to PR wire domains.
        Returns [] on any failure.
        """
        try:
            url = _press_release_url(company)
            raw = _fetch_raw(url)
            if not raw:
                return []
            from app.fetch import parse_and_normalize
            _meta, items = parse_and_normalize(raw)
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            return _filter_and_convert(items, cutoff, pr_only=True)
        except Exception:
            return []
