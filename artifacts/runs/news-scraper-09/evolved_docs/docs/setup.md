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
