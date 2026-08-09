from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CandidateItem:
    title: str
    url: str
    source_name: str
    source_tier: str
    source_type: str
    published_at: str | None = None
    text: str = ""
    media_url: str | None = None


@dataclass
class StoryEvent:
    id: str
    headline: str
    summary: str
    created_at: str
    last_seen_at: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    score: int = 0
    early_signal: int = 0
    confidence: int = 0
    breakout_sent: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoryEvent":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

