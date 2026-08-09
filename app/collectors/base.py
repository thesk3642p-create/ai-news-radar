from __future__ import annotations

from abc import ABC, abstractmethod
import time

import httpx

from app.models import CandidateItem


class Collector(ABC):
    name: str

    @abstractmethod
    def collect(self) -> list[CandidateItem]:
        """Return candidates or raise a collector-specific exception."""


def get_with_retries(url: str, *, timeout: int, headers: dict[str, str], params: dict | None = None) -> httpx.Response:
    """Bounded retries for transport failures and server/rate-limit responses."""
    error: Exception | None = None
    for attempt in range(3):
        try:
            response = httpx.get(url, timeout=timeout, headers=headers, params=params)
            if response.status_code < 400:
                return response
            if response.status_code not in (429, 500, 502, 503, 504):
                response.raise_for_status()
            error = httpx.HTTPStatusError("retryable response", request=response.request, response=response)
            retry_after = response.headers.get("Retry-After")
            delay = min(8, int(retry_after)) if retry_after and retry_after.isdigit() else 2**attempt
        except (httpx.TransportError, httpx.HTTPStatusError) as caught:
            error = caught
            delay = 2**attempt
        if attempt < 2:
            time.sleep(delay)
    assert error is not None
    raise error
