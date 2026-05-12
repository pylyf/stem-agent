from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx
from bs4 import BeautifulSoup
from loguru import logger

from src.fetchers.base import BaseFetcher
from src.models import RawItem


RSS_SOURCES: tuple[tuple[str, str], ...] = (
    ("Arxiv cs.AI", "https://arxiv.org/rss/cs.AI"),
    ("Arxiv cs.LG", "https://arxiv.org/rss/cs.LG"),
    ("Product Hunt AI", "https://www.producthunt.com/feed?category=artificial-intelligence"),
    ("Import AI", "https://jack-clark.net/feed/"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
)


class RssFetcher(BaseFetcher):
    def __init__(self, source_name: str, url: str, timeout: float = 20.0) -> None:
        self.source_name = source_name
        self.url = url
        self.timeout = timeout

    async def fetch(self) -> list[RawItem]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(self.url)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("RSS fetch failed for {}: {}", self.source_name, exc)
            return []

        parsed = feedparser.parse(response.text)
        items: list[RawItem] = []
        for entry in parsed.entries:
            url = str(getattr(entry, "link", "")).strip()
            title = str(getattr(entry, "title", "")).strip()
            if not url or not title:
                continue

            summary = _clean_html(
                str(getattr(entry, "summary", "") or getattr(entry, "description", ""))
            )
            items.append(
                RawItem(
                    url=url,
                    title=title,
                    source=self.source_name,
                    summary=summary,
                    published=_parse_entry_datetime(entry),
                )
            )
        return items


def default_rss_fetchers() -> list[RssFetcher]:
    return [RssFetcher(name, url) for name, url in RSS_SOURCES]


def _parse_entry_datetime(entry: object) -> datetime | None:
    for attr in ("published", "updated", "created"):
        raw = getattr(entry, attr, None)
        if not raw:
            continue
        try:
            value = parsedate_to_datetime(str(raw))
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
    return None


def _clean_html(value: str) -> str:
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return " ".join(text.split())

