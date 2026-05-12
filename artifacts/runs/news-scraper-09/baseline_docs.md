# Maintainer Documentation

This repository is a Python project for a daily AI news scraper that generates LinkedIn draft posts.

## Project Overview

- **Main Entrypoint:** `main.py`
- **Programming Language:** Python (requires Python >= 3.11)
- **Purpose:** Scrape AI-related news, generate post drafts, and prepare notifications.
- **Architecture Highlights:**
  - `src/config.py`: Configuration and settings management.
  - `src/db.py`: Database abstraction with `NewsDatabase` class.
  - `src/fetchers/`: Various news fetchers (Google News, Hacker News, RSS).
  - `src/generator.py`: Draft generation for posts.
  - `src/models.py`: Data model classes (`PostDraft`, `RawItem`, `ScoredItem`).
  - `src/notifier.py`: Email notification handling.
  - `scripts/`: Utility scripts for setup, testing, and validation.

## Setup Instructions

Run the following commands to set up the environment:

```bash
pip install -r requirements.txt
pip install -e .
```

## Testing

Run tests using:

```bash
pytest
```

The `.pytest_cache/README.md` explains the pytest cache directory; note that this directory should not be checked into version control.

## Key Components Summary

- **main.py**  
  Application entrypoint that sets up logging and async execution.

- **src/config.py**  
  Contains `Settings` class and helper functions like `_bool_env()` and `load_settings()` to load and manage app configuration.

- **src/db.py**  
  Defines `NewsDatabase` which provides database operations. Includes utility method `item_id(url: str) -> str`.

- **src/fetchers/**  
  Implements various fetchers:
  - `BaseFetcher` (abstract base class)
  - `GoogleNewsFetcher`
  - `HackerNewsFetcher`
  - `RssFetcher` and `default_rss_fetchers()`

- **src/generator.py**  
  Implements the `DraftGenerator` for generating post drafts with methods validating and parsing drafts.

- **src/models.py**  
  Defines core data models: `PostDraft`, `RawItem`, and `ScoredItem`.

- **src/notifier.py**  
  Email notification functionality with `send_test_email`.

- **scripts/**  
  Utility scripts include:
  - `setup_db.py` for database preparation
  - `test_openai_api.py` for OpenAI API testing
  - `test_run.py` for general runtime tests
  - `test_smtp.py` to test email sending (`main()` returns int)

## Maintainer Notes

- Use `main.py` as the entry point for running the scraper application.
- Follow setup commands exactly as specified to ensure proper environment setup.
- The project currently requires Python 3.11 or newer.
- Testing is integrated and should be run frequently during development.
- The repository uses async features and logging via `loguru`.
- Publishing to LinkedIn is currently manual; a placeholder exists in `src/publisher.py` for future automation.

For more information on each component, refer to the respective source files.
