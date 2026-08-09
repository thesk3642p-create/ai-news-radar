from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.collectors.news import GdeltCollector, GoogleNewsCollector
from app.collectors.rss import OfficialPageCollector, RssCollector
from app.collectors.x import XCollector
from app.config import Config
from app.delivery.telegram import TelegramDelivery, format_event, split_messages
from app.models import StoryEvent, utc_now
from app.processing.normalize import normalize_candidate
from app.processing.scoring import score_event
from app.processing.stories import cluster, relevant
from app.storage.state import StateStore

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger(__name__)


def collect_all(config: Config, x_enabled: bool) -> tuple[list, dict]:
    timeout = config.settings["request_timeout_seconds"]
    collectors = [RssCollector(source, timeout) if source.get("feed_url") else OfficialPageCollector(source, timeout) for source in config.sources]
    query = " OR ".join(["OpenAI", "Anthropic", "Google DeepMind", "Gemini", "DeepSeek", "Qwen", "Mistral AI", "xAI"])
    collectors.extend([GdeltCollector(query, timeout), GoogleNewsCollector("AI model release OR AI agent OR frontier AI", timeout), XCollector(config.x_handles, x_enabled)])
    candidates, health = [], {}
    for collector in collectors:
        try:
            gathered = collector.collect()
            candidates.extend(gathered)
            health[collector.name] = {"status": "ok", "count": len(gathered), "checked_at": utc_now().isoformat()}
        except Exception as error:  # collection failures are intentionally isolated
            LOG.warning("Collector %s failed: %s", collector.name, error)
            health[collector.name] = {"status": "error", "error": str(error)[:200], "checked_at": utc_now().isoformat()}
    return candidates, health


def run(dry_run: bool = False, x_enabled: bool = False) -> int:
    config = Config.load(ROOT / "config" / "sources.json")
    store = StateStore(ROOT / "state" / "radar_state.json", config.settings["event_retention_days"], config.settings["sent_retention_days"])
    state = store.load()
    candidates, health = collect_all(config, x_enabled)
    new_items = []
    for item in candidates:
        item = normalize_candidate(item)
        if not item.url or item.url in state["processed_urls"] or not relevant(item, config.keywords, config.entities):
            continue
        new_items.append(item)
        state["processed_urls"][item.url] = utc_now().isoformat()
    existing = [StoryEvent.from_dict(data) for data in state["events"]]
    events = cluster(new_items, existing)
    historical_titles = [event.headline.lower() for event in existing]
    for event in events:
        score_event(event, config.keywords, config.entities, historical_titles)
    state["source_health"] = health
    qualified = sorted((event for event in events if event.score >= config.settings["digest_threshold"]), key=lambda event: event.score, reverse=True)
    delivery = TelegramDelivery(dry_run=dry_run)
    for event in qualified:
        is_breakout = event.score >= config.settings["breakout_score_threshold"] and event.early_signal >= config.settings["breakout_early_threshold"] and event.confidence >= 60
        if is_breakout and not event.breakout_sent:
            delivery.send(format_event(event, breakout=True))
            event.breakout_sent = True
            state["sent_alerts"][f"breakout:{event.id}"] = utc_now().isoformat()
    digest_events = qualified[: config.settings["max_digest_items"]]
    unsent_digest = [event for event in digest_events if f"digest:{event.id}" not in state["sent_alerts"]]
    if unsent_digest:
        header = "<b>AI News Radar — hourly digest</b>"
        for message in split_messages(header, [format_event(event) for event in unsent_digest]):
            delivery.send(message)
        for event in unsent_digest:
            state["sent_alerts"][f"digest:{event.id}"] = utc_now().isoformat()
    state["events"] = [event.to_dict() for event in events]
    if not dry_run:
        store.save(state)
    LOG.info("Collected %s candidates; %s new; %s qualifying events", len(candidates), len(new_items), len(qualified))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print Telegram output and do not save state")
    parser.add_argument("--x-enabled", action="store_true", help="Enable the optional Twikit adapter")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return run(dry_run=args.dry_run, x_enabled=args.x_enabled)


if __name__ == "__main__":
    raise SystemExit(main())

