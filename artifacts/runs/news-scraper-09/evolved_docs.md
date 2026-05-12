# docs/setup.md

```markdown
# Setup Guide for AI News Scraper Project

This document provides the instructions to set up, install dependencies, and configure the environment for the AI News Scraper project.

---

## Prerequisites

- Python 3.11 or newer is required to run this project, as specified in `pyproject.toml`.
- Ensure `pip` is installed and up to date.

---

## Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd news-scraper
   ```

2. **Install dependencies**

   All Python dependencies are listed in `requirements.txt`. Install them using pip:

   ```bash
   pip install -r requirements.txt
   ```

3. **Install the project in editable mode**

   This allows for local development and testing of changes without reinstalling:

   ```bash
   pip install -e .
   ```

---

## Running Tests

Run the test suite to verify the installation:

```bash
pytest
```

---

## Configuration Environment Variables

The project uses environment variables for runtime configuration, managed via `src/config.py` and the `Settings` class.

To configure the environment:

1. Create a `.env` file in the project root or set environment variables directly.

2. Typical configurable variables include (based on config usage patterns and utility functions):

   - Variables controlling feature toggles such as generation and email sending, detected by:

     - `can_generate()` — enables/disables content generation.
     - `can_send_email()` — enables/disables email notifications.

   - Boolean environment variables parsed with a helper `_bool_env(name: str, default: bool) -> bool`, suggesting variables follow a `true/false` or `1/0` pattern.

3. Example `.env` entries (adjust according to your environment):

   ```
   GENERATE_CONTENT=true
   SEND_EMAIL=false
   DATABASE_PATH=./data/news.db
   OPENAI_API_KEY=your_openai_api_key_here
   SMTP_SERVER=smtp.example.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@example.com
   SMTP_PASSWORD=your_smtp_password
   ```

Refer to the `src/config.py` module for the exact variable names and their defaults by inspecting the `Settings` class and `load_settings()` function.

---

## Database Setup

To initialize or reset the SQLite database used for storing news items, run the provided script:

```bash
python scripts/setup_db.py
```

---

## Entry Point

Run the main application using:

```bash
python main.py
```

---

## Summary

- Python 3.11+ required
- Install dependencies from `requirements.txt`
- Install editable package with `pip install -e .`
- Configure environment with `.env` file or environment variables
- Initialize database with `scripts/setup_db.py`
- Run tests with `pytest`
- Start application with `python main.py`

This documentation should help you get started smoothly with the AI News Scraper project.

---
```

# docs/usage.md

```markdown
# Usage Guide

This document details the main usage flow and orchestration behavior from the primary entrypoint `main.py` of the AI News Scraper project. It explains how the system integrates configuration settings, data fetching, scoring, draft generation, and notification to produce daily AI news LinkedIn post drafts.

---

## Entrypoint: `main.py`

The script `main.py` serves as the application entrypoint. Its role is to coordinate the entire workflow from retrieving news items, filtering and scoring them for relevance, generating LinkedIn post draft variants, and finally sending notifications with generated drafts.

Key orchestration steps include:

1. **Configuration Setup**
   - Loads runtime configuration via the `Settings` class from `src/config.py`.
   - Configuration controls:
     - Which sources to fetch from.
     - Scoring parameters.
     - Draft generation toggles (`can_generate`).
     - Email notification toggles (`can_send_email`).

2. **Data Fetching**
   - Multiple fetchers implement the abstract base `BaseFetcher` (`src/fetchers/base.py`).
   - Built-in fetchers include:
     - RSS feeds (`src/fetchers/rss.py`).
     - Hacker News aggregator (`src/fetchers/hackernews.py`).
     - Potentially Google News (`src/fetchers/googlenews.py`).
   - Fetchers collect `RawItem` objects containing article metadata and URLs.
   - The items are then deduplicated and filtered to keep relevant content.

3. **Scoring**
   - Using scoring logic from `src/scorer.py`, raw news items are enriched to `ScoredItem` instances.
   - The scorer applies keyword weighting and heuristics to assess the relevance and quality of items.
   - Only scored items meeting thresholds continue to draft generation.

4. **Draft Generation**
   - Controlled by the configuration flag `Settings.can_generate`.
   - Uses `DraftGenerator` from `src/generator.py` to create two variant draft posts (`PostDraft` models).
   - Uses OpenAI APIs to generate natural language post drafts summarizing or commenting on news items.
   - Validates draft outputs to ensure quality and completeness.

5. **Notification**
   - Controlled by the configuration flag `Settings.can_send_email`.
   - Drafts are formatted into email messages.
   - Uses `src/notifier.py` utilities to build email contents and send via SMTP.
   - Notifications deliver the draft posts to recipients for manual LinkedIn publishing.

---

## Configuration: `src/config.py`

- `Settings` class loads environment variables (often via `.env` files).
- Provides typed access to:
  - Source lists and parameters.
  - Email server settings.
  - Feature toggles like `can_generate()` and `can_send_email()` methods.
- Ensures the application can be flexibly reconfigured without code changes.

---

## Summary of Flow

```text
Settings load
     ↓
Fetch data using multiple fetchers
     ↓
RawItem deduplication and filtering
     ↓
Apply scoring to produce ScoredItem
     ↓
If enabled, generate post drafts (two variants)
     ↓
If enabled, send notification emails with drafts
```

---

## Notes

- The entire flow is asynchronous, enabling efficient fetching and processing of multiple sources.
- Post draft generation leverages OpenAI APIs as configured.
- The system currently outputs posts as emails; manual LinkedIn publishing is expected.
- The modular design eases extensibility with new data sources or notification channels.

---

This document aims to guide maintainers and integrators on how the main script orchestrates the system components to produce LinkedIn draft posts for daily AI news.
```

# docs/components.md

# Components Documentation

This document provides summaries and explanations of the major components of the AI news scraper project, focusing on key modules that handle news fetching, database management, post draft generation, notification, and data modeling.

---

## Fetchers

The fetchers are responsible for retrieving news items from various sources asynchronously. They produce standardized raw news items for further processing.

### Base Fetcher (`src/fetchers/base.py`)

- **Description:** Defines an abstract base class `BaseFetcher` which all specific fetchers inherit from.
- **Core Functionality:** Implements a `source_name` attribute and an abstract asynchronous method `fetch`. The `fetch` method retrieves news items from the source.
- Provides a common interface and structure for all fetcher implementations.

---

### Google News Fetcher (`src/fetchers/googlenews.py`)

- **Description:** Implements `GoogleNewsFetcher` that retrieves news articles from Google News based on configured queries.
- **Features:**
  - Asynchronous fetching of news items.
  - Graceful handling of import and runtime errors.
  - Returns a list of `RawItem` instances containing article URL, title, source, summary, and published datetime.
- **Helpers:** Includes `_parse_datetime` utility to convert date strings into timezone-aware datetime objects.

---

### Hacker News Fetcher (`src/fetchers/hackernews.py`)

- **Description:** Defines `HackerNewsFetcher` inheriting from `BaseFetcher`.
- **Functionality:**
  - Fetches AI-related Hacker News stories via asynchronous HTTP requests to the Hacker News API.
  - Extracts story data such as title, URL, author, points, comments count, and publish date.
  - Returns a list of `RawItem` objects representing each story.
- **Date Handling:** Uses `_parse_datetime` to convert ISO8601 timestamps to UTC datetime objects.

---

### RSS Fetcher (`src/fetchers/rss.py`)

- **Description:** Offers an `RssFetcher` class that fetches and parses content from multiple RSS feeds related to AI topics.
- **Capabilities:**
  - Asynchronous fetching and parsing of feed entries.
  - Cleans HTML content into plain text summaries.
  - Parses the publication datetime from feed entries.
- **Extras:** Defines a set of default RSS sources for AI news and utilities to assist parsing and cleaning feed data.

---

## Generator

### Draft Generator (`src/generator.py`)

- **Role:** Responsible for generating Czech-language LinkedIn post drafts on behalf of Filip, a 22-year-old AI developer and consultant.
- **Characteristics:**
  - Supports generating two variants of posts asynchronously using OpenAI’s API: educational and opinionated styles.
  - Can produce placeholder drafts locally if API generation is disabled.
  - Structured posts include components such as hook, context, Filip's personal take, and call to action.
  - Implements strict language style and formatting rules tailored for Czech business audiences.
- **Helper Methods:** Includes functions to split and validate the generated draft variants.

---

## Database

### News Database (`src/db.py`)

- **Purpose:** Manages asynchronous storage and retrieval of news items and associated LinkedIn post drafts using SQLite via `aiosqlite`.
- **Schema Highlights:**
  - `items`: Stores fields such as URL, title, source, summary, published date, score, and fetch time.
  - `posts`: Linked to items; includes draft text, publication status, tokens used, and cost details.
- **Functionalities:**
  - Initialize and migrate database schema.
  - Check if a URL has been seen before.
  - Insert new news items and store generated post drafts.
- **Utility:** Provides `item_id` function generating a unique hash ID from the news item URL.

---

## Models

### Data Classes (`src/models.py`)

Defines data structures to uniformly represent news and draft data:

- **`RawItem`:** Basic representation of a news item with essential fields like URL, title, source, summary, and published datetime.
- **`ScoredItem`:** Extends `RawItem` with additional scoring information and matched keywords.
- **`PostDraft`:** Represents a LinkedIn post draft associated with a scored item, including draft text variants, token usage, and cost metadata.

---

## Notifier

### Email Notification (`src/notifier.py`)

- **Function:** Manages the composition and dispatch of daily AI news LinkedIn draft emails.
- **Capabilities:**
  - Generates both HTML and plain-text email content from lists of post drafts.
  - Sends emails via SMTP using configured settings.
  - Supports sending test emails to validate SMTP configuration.
- **Formatting:** Ensures clear segmentation of educational and opinionated draft variants in the email content.

---

This component-centric documentation summarizes the primary building blocks of the AI news scraper project, underpinning how news data is sourced, processed, stored, drafted, and communicated effectively.

# docs/api_reference.md

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
