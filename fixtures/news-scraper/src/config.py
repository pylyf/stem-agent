from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str
    openai_max_output_tokens: int
    openai_reasoning_effort: str
    smtp_host: str
    smtp_port: int
    smtp_user: str | None
    smtp_password: str | None
    email_from: str | None
    email_to: str | None
    database_path: Path
    posts_per_day: int
    min_relevance_score: float
    max_item_age_hours: int
    dry_run: bool
    send_email: bool
    log_level: str

    @property
    def can_generate(self) -> bool:
        return bool(self.openai_api_key) and not self.dry_run

    @property
    def can_send_email(self) -> bool:
        return (
            self.send_email
            and not self.dry_run
            and bool(self.smtp_host)
            and bool(self.smtp_user)
            and bool(self.smtp_password)
            and bool(self.email_to)
        )


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        openai_max_output_tokens=int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "4000")),
        openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "minimal"),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        email_from=os.getenv("EMAIL_FROM") or os.getenv("SMTP_USER"),
        email_to=os.getenv("EMAIL_TO"),
        database_path=Path(os.getenv("DATABASE_PATH", "data/news.db")),
        posts_per_day=int(os.getenv("POSTS_PER_DAY", "10")),
        min_relevance_score=float(os.getenv("MIN_RELEVANCE_SCORE", "0.6")),
        max_item_age_hours=int(os.getenv("MAX_ITEM_AGE_HOURS", "36")),
        dry_run=_bool_env("DRY_RUN", True),
        send_email=_bool_env("SEND_EMAIL", True),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
