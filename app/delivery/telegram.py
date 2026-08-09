from __future__ import annotations

import html
import os
import sys

import httpx

from app.models import StoryEvent


def _escape(value: str) -> str:
    return html.escape(value, quote=False)


def format_event(event: StoryEvent, breakout: bool = False) -> str:
    prefix = "🚨 <b>BREAKOUT</b> — " if breakout else "🔥 "
    sources = " · ".join(dict.fromkeys(source["source_name"] for source in event.sources))
    original = event.sources[0]["url"]
    early = "HIGH" if event.early_signal >= 70 else "MEDIUM" if event.early_signal >= 45 else "LOW"
    return (f"{prefix}<b>{_escape(event.headline)}</b>\n\n{_escape(event.summary[:380])}\n\n"
            f"⚡ Early signal: <b>{early}</b> ({event.early_signal}/100)\n"
            f"🔥 Content potential: <b>{event.score}/100</b>\n"
            f"Sources: {_escape(sources)}\n"
            f"🔗 <a href=\"{html.escape(original, quote=True)}\">Original link</a>")


def split_messages(header: str, entries: list[str], limit: int = 3900) -> list[str]:
    messages: list[str] = []
    current = header
    for entry in entries:
        candidate = f"{current}\n\n{entry}"
        if len(candidate) > limit and current != header:
            messages.append(current)
            current = f"{header}\n\n{entry}"
        else:
            current = candidate
    if current != header:
        messages.append(current)
    return messages


class TelegramDelivery:
    def __init__(self, dry_run: bool = False) -> None:
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        self.dry_run = dry_run

    def send(self, text: str) -> None:
        if self.dry_run:
            sys.stdout.buffer.write(("--- Telegram preview ---\n" + text + "\n").encode("utf-8", errors="replace"))
            return
        if not self.token or not self.chat_id:
            raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured")
        response = httpx.post(f"https://api.telegram.org/bot{self.token}/sendMessage", json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=20)
        response.raise_for_status()
