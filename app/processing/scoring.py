from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone

from app.models import StoryEvent
from app.processing.normalize import normalize_title, parse_time

IMPORTANT = ("launch", "release", "introduc", "announc", "open source", "benchmark", "breakthrough", "partnership", "api", "agent", "model")
VISUAL = ("demo", "video", "benchmark", "compare", "image", "voice", "coding", "agent", "model")
TIER_WEIGHT = {"official": 10, "trusted": 7, "unknown": 3}


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase.lower())}(?!\w)", text) is not None


def score_event(event: StoryEvent, keywords: list[str], entities: list[str], existing_titles: list[str]) -> StoryEvent:
    combined = normalize_title(f"{event.headline} {event.summary}")
    relevance_hits = sum(_contains(combined, term) for term in keywords + entities)
    relevance = min(30, relevance_hits * 5)
    age_hours = max(0, (datetime.now(timezone.utc) - parse_time(event.created_at)).total_seconds() / 3600)
    freshness = round(20 * math.exp(-age_hours / 36))
    importance = min(15, sum(term in combined for term in IMPORTANT) * 3)
    sources = event.sources
    reliability = min(10, max((TIER_WEIGHT.get(source.get("source_tier", "unknown"), 3) for source in sources), default=0))
    novelty = 10 if normalize_title(event.headline) not in existing_titles else 2
    visual = min(10, 3 + sum(term in combined for term in VISUAL))
    publishers = {source.get("source_name") for source in sources}
    corroboration = min(5, max(0, len(publishers) - 1) * 2)
    event.score = min(100, relevance + freshness + importance + reliability + novelty + visual + corroboration)
    event.confidence = min(100, reliability * 6 + corroboration * 4)
    event.early_signal = early_signal(event, freshness, novelty)
    return event


def early_signal(event: StoryEvent, freshness: int, novelty: int) -> int:
    sources = event.sources
    publishers = {source.get("source_name") for source in sources}
    velocity = min(25, max(0, len(sources) - 1) * 8)
    diversity = min(20, max(0, len(publishers) - 1) * 8)
    trust = min(15, max((15 if source.get("source_tier") == "official" else 8 for source in sources), default=0))
    return min(100, round(freshness * 1.5) + velocity + diversity + trust + novelty)

