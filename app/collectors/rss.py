from __future__ import annotations

from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

from app.collectors.base import Collector, get_with_retries
from app.models import CandidateItem

USER_AGENT = "AI-News-Content-Radar/1.0 (+personal research; RSS only)"


def _clean(value: str | None) -> str:
    return " ".join(BeautifulSoup(unescape(value or ""), "html.parser").get_text(" ").split())


def _entry_time(entry: object) -> str | None:
    for key in ("published", "updated"):
        value = getattr(entry, key, None)
        if value:
            try:
                return parsedate_to_datetime(value).isoformat()
            except (TypeError, ValueError):
                return None
    return None


class RssCollector(Collector):
    def __init__(self, source: dict, timeout_seconds: int) -> None:
        self.source = source
        self.timeout_seconds = timeout_seconds
        self.name = f"rss:{source['name']}"

    def collect(self) -> list[CandidateItem]:
        feed_url = self.source.get("feed_url")
        if not feed_url:
            return []
        response = get_with_retries(feed_url, timeout=self.timeout_seconds, headers={"User-Agent": USER_AGENT})
        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            raise ValueError(f"invalid feed: {feed_url}")
        return [
            CandidateItem(
                title=_clean(getattr(entry, "title", "")),
                url=getattr(entry, "link", ""),
                source_name=self.source["name"],
                source_tier=self.source["tier"],
                source_type="rss",
                published_at=_entry_time(entry),
                text=_clean(getattr(entry, "summary", "")),
            )
            for entry in parsed.entries[:30]
            if getattr(entry, "title", "") and getattr(entry, "link", "")
        ]


class OfficialPageCollector(Collector):
    """Small, polite fallback when an official source has no configured RSS feed."""

    def __init__(self, source: dict, timeout_seconds: int) -> None:
        self.source = source
        self.timeout_seconds = timeout_seconds
        self.name = f"page:{source['name']}"

    def collect(self) -> list[CandidateItem]:
        response = get_with_retries(self.source["url"], timeout=self.timeout_seconds, headers={"User-Agent": USER_AGENT})
        parsed = feedparser.parse(response.content)
        discovered = next((link.href for link in parsed.feed.get("links", []) if "rss" in link.get("type", "") or "atom" in link.get("type", "")), None)
        if discovered:
            copied = {**self.source, "feed_url": urljoin(self.source["url"], discovered)}
            return RssCollector(copied, self.timeout_seconds).collect()
        soup = BeautifulSoup(response.text, "html.parser")
        candidates: list[CandidateItem] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            title, url = _clean(anchor.get_text(" ")), urljoin(self.source["url"], anchor["href"])
            if len(title) < 18 or url in seen or not url.startswith(self.source["url"].split("/", 3)[0] + "//" + self.source["url"].split("/", 3)[2]):
                continue
            seen.add(url)
            candidates.append(CandidateItem(title=title, url=url, source_name=self.source["name"], source_tier=self.source["tier"], source_type="official_page"))
            if len(candidates) == 30:
                break
        if candidates:
            return candidates
        return []
