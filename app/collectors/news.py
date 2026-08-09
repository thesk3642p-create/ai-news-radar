from __future__ import annotations

from urllib.parse import quote_plus

import feedparser

from app.collectors.base import Collector, get_with_retries
from app.collectors.rss import USER_AGENT, _clean, _entry_time
from app.models import CandidateItem


class GoogleNewsCollector(Collector):
    name = "google_news"

    def __init__(self, query: str, timeout_seconds: int) -> None:
        self.query = query
        self.timeout_seconds = timeout_seconds

    def collect(self) -> list[CandidateItem]:
        url = f"https://news.google.com/rss/search?q={quote_plus(self.query)}&hl=en-US&gl=US&ceid=US:en"
        response = get_with_retries(url, timeout=self.timeout_seconds, headers={"User-Agent": USER_AGENT})
        feed = feedparser.parse(response.content)
        return [CandidateItem(title=_clean(entry.title), url=entry.link, source_name="Google News", source_tier="trusted", source_type="google_news", published_at=_entry_time(entry), text=_clean(getattr(entry, "summary", ""))) for entry in feed.entries[:30]]


class GdeltCollector(Collector):
    name = "gdelt"

    def __init__(self, query: str, timeout_seconds: int) -> None:
        self.query = query
        self.timeout_seconds = timeout_seconds

    def collect(self) -> list[CandidateItem]:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        response = get_with_retries(url, params={"query": self.query, "mode": "artlist", "format": "json", "maxrecords": 50}, timeout=self.timeout_seconds, headers={"User-Agent": USER_AGENT})
        articles = response.json().get("articles", [])
        return [CandidateItem(title=_clean(article.get("title")), url=article.get("url", ""), source_name=article.get("domain", "GDELT"), source_tier="trusted", source_type="gdelt", published_at=article.get("seendate"), text=_clean(article.get("socialimage", ""))) for article in articles if article.get("title") and article.get("url")]
