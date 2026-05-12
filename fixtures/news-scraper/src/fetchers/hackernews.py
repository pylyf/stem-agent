from __future__ import annotations

from datetime import datetime, timezone

import httpx
from loguru import logger

from src.fetchers.base import BaseFetcher
from src.models import RawItem


class HackerNewsFetcher(BaseFetcher):
    source_name = "Hacker News"
    url = "https://hn.algolia.com/api/v1/search?tags=story&query=AI"

    async def fetch(self) -> list[RawItem]:
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(self.url)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("HN fetch failed: {}", exc)
            return []

        items: list[RawItem] = []
        for hit in payload.get("hits", []):
            title = (hit.get("title") or hit.get("story_title") or "").strip()
            url = (hit.get("url") or hit.get("story_url") or "").strip()
            if not title or not url:
                continue

            summary_parts = []
            if hit.get("author"):
                summary_parts.append(f"Author: {hit['author']}")
            if hit.get("points") is not None:
                summary_parts.append(f"Points: {hit['points']}")
            if hit.get("num_comments") is not None:
                summary_parts.append(f"Comments: {hit['num_comments']}")

            items.append(
                RawItem(
                    url=url,
                    title=title,
                    source=self.source_name,
                    summary=". ".join(summary_parts),
                    published=_parse_datetime(hit.get("created_at")),
                )
            )
        return items


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None

