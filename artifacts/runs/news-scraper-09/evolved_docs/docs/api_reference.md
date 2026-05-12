```markdown
# API Reference

This document catalogs the public interfaces, classes, and methods of the AI News Scraper project for developer reference.

---

## main.py

### `def _configure_stdio() -> None`

Configure standard input/output streams for the application environment.

---

## scripts/test_smtp.py

### `def main() -> int`

Entry point to run SMTP test, returning an integer exit status.

---

## src/config.py

### Class `Settings`

Configuration settings class managing environment and runtime options.

#### Methods:

- `def can_generate(self) -> bool`

  Returns `True` if content generation is enabled based on settings.

- `def can_send_email(self) -> bool`

  Returns `True` if sending emails is enabled based on settings.

### `def _bool_env(name: str, default: bool) -> bool`

Helper function to read a boolean environment variable by name, with a default fallback.

### `def load_settings() -> Settings`

Loads and returns the application settings from environment variables and configuration files.

---

## src/db.py

### Class `NewsDatabase`

Handles database operations related to news items.

#### Methods:

- `def __init__(self, path: Path) -> None`

  Initialize the database connection at the specified file system path.

- `def item_id(url: str) -> str`

  Generates a unique identifier string for a news item given its URL.

---

## src/fetchers/base.py

### Abstract Class `BaseFetcher(ABC)`

Base class for all news fetchers providing the interface and common behavior.

---

## src/fetchers/googlenews.py

### Class `GoogleNewsFetcher(BaseFetcher)`

News fetcher implementation querying Google News.

#### Methods:

- `def __init__(self, queries: list[str] | None = None, max_results_per_query: int = 20) -> None`

  Create a GoogleNewsFetcher with optional query list and maximum results per query.

- `def _parse_datetime(value: str | None) -> datetime | None`

  Parse a datetime string from Google News into a `datetime` object or return `None` if parsing fails.

---

## src/fetchers/hackernews.py

### Class `HackerNewsFetcher(BaseFetcher)`

News fetcher for Hacker News source.

#### Methods:

- `def _parse_datetime(value: str | None) -> datetime | None`

  Parse a datetime string from Hacker News into a `datetime` object or return `None`.

---

## src/fetchers/rss.py

### Class `RssFetcher(BaseFetcher)`

RSS feed news fetcher.

#### Methods:

- `def __init__(self, source_name: str, url: str, timeout: float = 20.0) -> None`

  Initialize an RSS fetcher for the given source name and feed URL, with a configurable timeout.

- `def _clean_html(value: str) -> str`

  Utility to clean HTML tags and entities from a string.

- `def _parse_entry_datetime(entry: object) -> datetime | None`

  Extract and parse the publication date from an RSS entry object.

### `def default_rss_fetchers() -> list[RssFetcher]`

Return a default list of configured `RssFetcher` instances for common sources.

---

## src/generator.py

### Class `DraftGenerator`

Generates draft LinkedIn posts from fetched news items.

#### Methods:

- `def __init__(self, settings: Settings) -> None`

  Initialize a DraftGenerator with application settings.

- `def _generate_dry_run(self, item: ScoredItem) -> PostDraft`

  Generate a non-persistent draft for preview or testing.

- `def _looks_complete(text: str) -> bool`

  Heuristic to check if generated text appears complete.

- `def split_variants(text: str) -> tuple[str, str]`

  Splits a draft text into two variant strings.

- `def validate_drafts(draft_a: str, draft_b: str) -> None`

  Validates two draft variants for coherence and quality.

---

## src/models.py

### Class `RawItem`

Data class representing a raw news item.

#### Attributes:

- `url: str`

  The URL of the news article.

### Class `ScoredItem(RawItem)`

Extension of `RawItem` with scoring metadata.

### Class `PostDraft`

Data class representing a generated LinkedIn post draft.

---

# End of API Reference
```
