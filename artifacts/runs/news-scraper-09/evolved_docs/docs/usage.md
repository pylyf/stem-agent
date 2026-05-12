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
