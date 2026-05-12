from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from src.models import PostDraft, ScoredItem


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    source TEXT,
    summary TEXT,
    published TIMESTAMP,
    score REAL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT REFERENCES items(id),
    draft_a TEXT,
    draft_b TEXT,
    selected TEXT,
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,
    tokens_used INTEGER,
    cost_usd REAL
);
"""


class NewsDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def seen_urls(self, urls: list[str]) -> set[str]:
        if not urls:
            return set()
        placeholders = ",".join("?" for _ in urls)
        query = f"SELECT url FROM items WHERE url IN ({placeholders})"
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(query, urls)
            rows = await cursor.fetchall()
        return {row[0] for row in rows}

    async def store_items(self, items: list[ScoredItem]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (
                item_id(item.url),
                item.url,
                item.title,
                item.source,
                item.summary,
                item.published.isoformat() if item.published else None,
                item.score,
                now,
            )
            for item in items
        ]
        async with aiosqlite.connect(self.path) as db:
            await db.executemany(
                """
                INSERT OR IGNORE INTO items
                    (id, url, title, source, summary, published, score, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            await db.commit()

    async def store_posts(self, drafts: list[PostDraft]) -> None:
        rows = [
            (
                item_id(draft.item.url),
                draft.draft_a,
                draft.draft_b,
                draft.tokens_used,
                draft.cost_usd,
            )
            for draft in drafts
        ]
        async with aiosqlite.connect(self.path) as db:
            await db.executemany(
                """
                INSERT INTO posts (item_id, draft_a, draft_b, tokens_used, cost_usd)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            await db.commit()


def item_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

