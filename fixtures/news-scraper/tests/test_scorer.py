from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.models import RawItem
from src.scorer import KeywordScorer, dedupe_raw_items


def test_keyword_scorer_keeps_relevant_items() -> None:
    item = RawItem(
        url="https://example.com/agent",
        title="New AI agent benchmark for developer tools",
        source="Hacker News",
        summary="LLM automation workflow with API support",
        published=datetime.now(timezone.utc),
    )

    scored = KeywordScorer(min_score=0.1).score([item], limit=3)

    assert len(scored) == 1
    assert scored[0].score >= 0.6
    assert "agent" in scored[0].matched_keywords


def test_keyword_scorer_filters_old_items() -> None:
    item = RawItem(
        url="https://example.com/old",
        title="AI agent news",
        source="Example",
        published=datetime.now(timezone.utc) - timedelta(days=10),
    )

    assert KeywordScorer(max_age_hours=24).score([item], limit=3) == []


def test_dedupe_raw_items_by_url_and_title() -> None:
    items = [
        RawItem(url="https://example.com/a", title="Same title", source="A"),
        RawItem(url="https://example.com/a", title="Different title", source="B"),
        RawItem(url="https://example.com/b", title="Same title", source="C"),
    ]

    unique = dedupe_raw_items(items)

    assert [item.source for item in unique] == ["A"]
