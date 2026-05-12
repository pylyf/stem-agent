from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RawItem:
    url: str
    title: str
    source: str
    summary: str = ""
    published: datetime | None = None


@dataclass(frozen=True)
class ScoredItem(RawItem):
    score: float = 0.0
    matched_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class PostDraft:
    item: ScoredItem
    draft_a: str
    draft_b: str
    tokens_used: int | None = None
    cost_usd: float | None = None

