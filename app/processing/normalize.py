from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models import CandidateItem

TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"}


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode([(key, value) for key, value in parse_qsl(parts.query) if not key.startswith("utm_") and key.lower() not in TRACKING_KEYS])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", value.lower())).strip()


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def normalize_candidate(item: CandidateItem) -> CandidateItem:
    item.url = canonical_url(item.url)
    item.title = " ".join(item.title.split())
    item.text = " ".join(item.text.split())
    return item

