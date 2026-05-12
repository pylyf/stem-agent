from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import re

from src.models import RawItem, ScoredItem


KEYWORD_WEIGHTS: dict[str, float] = {
    "agent": 0.18,
    "agents": 0.18,
    "ai agent": 0.28,
    "automation": 0.2,
    "llm": 0.24,
    "large language model": 0.24,
    "rag": 0.24,
    "retrieval": 0.16,
    "developer tool": 0.22,
    "coding": 0.16,
    "open source": 0.14,
    "model": 0.1,
    "benchmark": 0.12,
    "inference": 0.14,
    "fine-tuning": 0.14,
    "anthropic": 0.16,
    "openai": 0.16,
    "google": 0.08,
    "microsoft": 0.08,
    "meta": 0.08,
    "hugging face": 0.16,
    "startup": 0.1,
    "api": 0.14,
    "workflow": 0.12,
}


class KeywordScorer:
    def __init__(self, min_score: float = 0.6, max_age_hours: int = 36) -> None:
        self.min_score = min_score
        self.max_age = timedelta(hours=max_age_hours)

    def score(self, items: list[RawItem], limit: int) -> list[ScoredItem]:
        scored = self.score_candidates(items, limit)
        return [item for item in scored if item.score >= self.min_score]

    def score_candidates(self, items: list[RawItem], limit: int) -> list[ScoredItem]:
        fresh_items = [item for item in dedupe_raw_items(items) if self._is_fresh(item)]
        scored = [self._score_item(item) for item in fresh_items]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

    def _score_item(self, item: RawItem) -> ScoredItem:
        text = normalize_text(f"{item.title} {item.summary} {item.source}")
        matched: list[str] = []
        raw_score = 0.0
        for keyword, weight in KEYWORD_WEIGHTS.items():
            if keyword in text:
                matched.append(keyword)
                raw_score += weight

        source_bonus = 0.08 if any(src in item.source.lower() for src in ["arxiv", "hacker news", "hugging"]) else 0.0
        title_bonus = min(0.2, len(set(re.findall(r"[a-z0-9]+", item.title.lower()))) / 100)
        score = min(1.0, raw_score + source_bonus + title_bonus)
        return ScoredItem(
            url=item.url,
            title=item.title,
            source=item.source,
            summary=item.summary,
            published=item.published,
            score=round(score, 3),
            matched_keywords=tuple(matched),
        )

    def _is_fresh(self, item: RawItem) -> bool:
        if item.published is None:
            return True
        published = item.published
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - published.astimezone(timezone.utc) <= self.max_age


def dedupe_raw_items(items: list[RawItem]) -> list[RawItem]:
    seen_urls: set[str] = set()
    seen_titles: Counter[str] = Counter()
    unique: list[RawItem] = []
    for item in items:
        normalized_url = item.url.strip().lower().rstrip("/")
        normalized_title = normalize_text(item.title)
        if normalized_url in seen_urls or seen_titles[normalized_title] > 0:
            continue
        seen_urls.add(normalized_url)
        seen_titles[normalized_title] += 1
        unique.append(item)
    return unique


def normalize_text(value: str) -> str:
    return " ".join(value.lower().replace("-", " ").split())
