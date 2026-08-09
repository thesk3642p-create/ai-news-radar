from __future__ import annotations

from datetime import timedelta

from rapidfuzz.fuzz import token_set_ratio

from app.models import CandidateItem, StoryEvent, utc_now
from app.processing.normalize import fingerprint, normalize_title, parse_time


def relevant(item: CandidateItem, keywords: list[str], entities: list[str]) -> bool:
    haystack = normalize_title(f"{item.title} {item.text}")
    return any(normalize_title(term) in haystack for term in keywords + entities)


def source_record(item: CandidateItem) -> dict:
    return {"url": item.url, "title": item.title, "source_name": item.source_name, "source_tier": item.source_tier, "source_type": item.source_type, "published_at": item.published_at, "media_url": item.media_url}


def _same_event(item: CandidateItem, event: StoryEvent) -> bool:
    if any(source["url"] == item.url for source in event.sources):
        return True
    title = normalize_title(item.title)
    if token_set_ratio(title, normalize_title(event.headline)) >= 87:
        return True
    item_time = parse_time(item.published_at)
    event_time = parse_time(event.created_at)
    same_window = abs(item_time - event_time) <= timedelta(hours=72)
    title_words = set(title.split())
    event_words = set(normalize_title(event.headline).split())
    return same_window and len(title_words & event_words) >= 3


def cluster(items: list[CandidateItem], existing: list[StoryEvent]) -> list[StoryEvent]:
    events = existing[:]
    for item in items:
        matched = next((event for event in events if _same_event(item, event)), None)
        now = utc_now().isoformat()
        if matched:
            if not any(source["url"] == item.url for source in matched.sources):
                matched.sources.append(source_record(item))
            matched.last_seen_at = now
            continue
        summary = item.text[:360].strip() or item.title
        events.append(StoryEvent(id=fingerprint(f"{normalize_title(item.title)}:{item.url}"), headline=item.title, summary=summary, created_at=item.published_at or now, last_seen_at=now, sources=[source_record(item)]))
    return events

