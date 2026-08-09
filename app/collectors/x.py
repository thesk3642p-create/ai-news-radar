from __future__ import annotations

import os
import json

from app.collectors.base import Collector
from app.models import CandidateItem


class XCollector(Collector):
    """Optional Twikit adapter. No bypassing or account-rotation behavior is implemented."""

    name = "x"

    def __init__(self, handles: list[dict], enabled: bool) -> None:
        self.handles = handles
        self.enabled = enabled

    def collect(self) -> list[CandidateItem]:
        if not self.enabled:
            return []
        cookies_json = os.environ.get("X_COOKIES_JSON")
        cookie_path = os.environ.get("X_COOKIES_FILE")
        if not cookies_json and not cookie_path:
            raise RuntimeError("X_COOKIES_JSON or X_COOKIES_FILE is required when the X collector is enabled")
        try:
            from twikit import Client
        except ImportError as error:
            raise RuntimeError("Twikit is not installed") from error

        import asyncio

        async def fetch() -> list[CandidateItem]:
            client = Client(language="en-US")
            if cookies_json:
                client.set_cookies(json.loads(cookies_json))
            else:
                client.load_cookies(cookie_path)
            results: list[CandidateItem] = []
            for configured in self.handles:
                user = await client.get_user_by_screen_name(configured["handle"])
                tweets = await client.get_user_tweets(user.id, "Tweets", count=10)
                for tweet in tweets:
                    tweet_id = str(tweet.id)
                    results.append(CandidateItem(title=(tweet.full_text or "")[:160], text=tweet.full_text or "", url=f"https://x.com/{configured['handle']}/status/{tweet_id}", source_name=f"@{configured['handle']}", source_tier=configured["tier"], source_type="x", published_at=str(tweet.created_at)))
            return results

        return asyncio.run(fetch())
