from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import sys

from loguru import logger

from src.config import load_settings
from src.db import NewsDatabase
from src.fetchers import HackerNewsFetcher, default_rss_fetchers
from src.fetchers.googlenews import GoogleNewsFetcher
from src.generator import DraftGenerator
from src.models import RawItem
from src.notifier import build_text_report, send_email
from src.scorer import KeywordScorer


async def fetch_all() -> list[RawItem]:
    fetchers = [*default_rss_fetchers(), HackerNewsFetcher(), GoogleNewsFetcher()]
    results = await asyncio.gather(*(fetcher.fetch() for fetcher in fetchers), return_exceptions=True)
    items: list[RawItem] = []
    for fetcher, result in zip(fetchers, results, strict=True):
        if isinstance(result, Exception):
            logger.warning("{} failed: {}", fetcher.source_name, result)
            continue
        logger.info("{} returned {} items", fetcher.source_name, len(result))
        items.extend(result)
    return items


async def run() -> int:
    settings = load_settings()
    _configure_stdio()
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level=settings.log_level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logger.info("Starting AI news scraper at {}", datetime.now(timezone.utc).isoformat())

    db = NewsDatabase(settings.database_path)
    await db.init()

    raw_items = await fetch_all()
    seen_urls = await db.seen_urls([item.url for item in raw_items])
    fresh_candidates = [item for item in raw_items if item.url not in seen_urls]
    logger.info("{} raw items, {} unseen candidates", len(raw_items), len(fresh_candidates))

    scorer = KeywordScorer(
        min_score=settings.min_relevance_score,
        max_age_hours=settings.max_item_age_hours,
    )
    scored_items = scorer.score_candidates(fresh_candidates, limit=max(settings.posts_per_day * 20, 100))
    eligible_items = [
        item for item in scored_items if item.score >= settings.min_relevance_score
    ]
    top_items = eligible_items[: settings.posts_per_day]
    if len(top_items) < settings.posts_per_day:
        high_score_count = len(top_items)
        selected_urls = {item.url for item in top_items}
        filler_items = [
            item
            for item in scored_items
            if item.url not in selected_urls
        ]
        top_items.extend(filler_items[: settings.posts_per_day - len(top_items)])
        if len(top_items) >= settings.posts_per_day:
            logger.warning(
                "Filled {} posts from below MIN_RELEVANCE_SCORE={} to keep {} total posts",
                len(top_items) - high_score_count,
                settings.min_relevance_score,
                settings.posts_per_day,
            )
    if len(top_items) < settings.posts_per_day:
        logger.warning(
            "Only {} fresh items found; requested {}",
            len(top_items),
            settings.posts_per_day,
        )
    if not settings.dry_run:
        await db.store_items(top_items)

    if not top_items:
        logger.info("No relevant fresh items found")
        return 0

    generator = DraftGenerator(settings)
    drafts = await generator.generate(top_items)
    if not settings.dry_run:
        await db.store_posts(drafts)

    if settings.dry_run:
        print(build_text_report(drafts))
    else:
        send_email(settings, drafts)
    return 0


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
