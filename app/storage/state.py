from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from app.models import StoryEvent, utc_now
from app.processing.normalize import parse_time


class StateStore:
    def __init__(self, path: Path, event_days: int, sent_days: int) -> None:
        self.path = path
        self.event_days = event_days
        self.sent_days = sent_days

    def load(self) -> dict:
        if not self.path.exists():
            return {"version": 1, "processed_urls": {}, "events": [], "sent_alerts": {}, "source_health": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def compact(self, state: dict) -> dict:
        now = utc_now()
        event_cutoff = now - timedelta(days=self.event_days)
        sent_cutoff = now - timedelta(days=self.sent_days)
        state["events"] = [event for event in state["events"] if parse_time(event["last_seen_at"]) >= event_cutoff]
        state["processed_urls"] = {key: stamp for key, stamp in state["processed_urls"].items() if parse_time(stamp) >= event_cutoff}
        state["sent_alerts"] = {key: stamp for key, stamp in state["sent_alerts"].items() if parse_time(stamp) >= sent_cutoff}
        return state

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.compact(state), indent=2, sort_keys=True) + "\n", encoding="utf-8")
