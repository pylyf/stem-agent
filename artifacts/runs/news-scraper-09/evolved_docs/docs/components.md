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
