from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Config:
    settings: dict[str, Any]
    keywords: list[str]
    entities: list[str]
    sources: list[dict[str, Any]]
    x_handles: list[dict[str, Any]]

    @classmethod
    def load(cls, path: Path) -> "Config":
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return cls(**data)

