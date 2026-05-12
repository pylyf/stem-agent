from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from loguru import logger

from src.fetchers.base import BaseFetcher
from src.models import RawItem


class GoogleNewsFetcher(BaseFetcher):
    source_name = "Google News"

    def __init__(self, queries: list[str] | None = None, max_results_per_query: int = 10) -> None:
        self.queries = queries or ["artificial intelligence", "LLM", "AI tools"]
        self.max_results_per_query = max_results_per_query

    async def fetch(self) -> list[RawItem]:
        try:
            from gnews import GNews
        except ImportError:
            logger.warning("gnews is not installed; skipping Google News")
            return []

        google_news = GNews(language="en", country="US", max_results=self.max_results_per_query)
        items: list[RawItem] = []
        for query in self.queries:
            try:
                results = google_news.get_news(query)
            except Exception as exc:
                logger.warning("Google News fetch failed for '{}': {}", query, exc)
                continue
            for result in results:
                title = str(result.get("title") or "").strip()
                url = str(result.get("url") or "").strip()
                if not title or not url:
                    continue
                publisher = result.get("publisher") or {}
                source = publisher.get("title") or self.source_name
                items.append(
                    RawItem(
                        url=url,
                        title=title,
                        source=f"{self.source_name}: {source}",
                        summary=str(result.get("description") or f"Matched query: {query}"),
                        published=_parse_datetime(result.get("published date")),
                    )
                )
        return items


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None

