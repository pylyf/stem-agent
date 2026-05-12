from __future__ import annotations

from email.message import EmailMessage
from html import escape
import smtplib

from loguru import logger

from src.config import Settings
from src.models import PostDraft


def build_html_email(drafts: list[PostDraft]) -> str:
    sections = []
    for index, draft in enumerate(drafts, start=1):
        item = draft.item
        sections.append(
            f"""
            <section style="margin:0 0 28px 0;padding:18px;border:1px solid #ddd;border-radius:8px;">
              <h2 style="margin:0 0 8px 0;">{index}. {escape(item.title)}</h2>
              <p style="margin:0 0 8px 0;color:#555;">
                {escape(item.source)} | score {item.score:.2f} | <a href="{escape(item.url)}">source</a>
              </p>
              <h3>Variant A - educational</h3>
              <p><strong>--- COPY FROM HERE ---</strong></p>
              <pre style="white-space:pre-wrap;font-family:Arial,sans-serif;">{escape(draft.draft_a)}</pre>
              <p><strong>--- COPY UNTIL HERE ---</strong></p>
              <h3>Variant B - opinionated</h3>
              <p><strong>--- COPY FROM HERE ---</strong></p>
              <pre style="white-space:pre-wrap;font-family:Arial,sans-serif;">{escape(draft.draft_b)}</pre>
              <p><strong>--- COPY UNTIL HERE ---</strong></p>
            </section>
            """
        )

    return f"""
    <html>
      <body style="font-family:Arial,sans-serif;line-height:1.5;color:#111;">
        <h1>Daily AI LinkedIn Drafts</h1>
        <p>Top {len(drafts)} fresh AI stories with LinkedIn draft variants.</p>
        {''.join(sections)}
      </body>
    </html>
    """


def build_text_report(drafts: list[PostDraft]) -> str:
    chunks = ["Daily AI LinkedIn Drafts", ""]
    for index, draft in enumerate(drafts, start=1):
        item = draft.item
        chunks.extend(
            [
                f"{index}. {item.title}",
                f"{item.source} | score {item.score:.2f}",
                item.url,
                "",
                "Variant A:",
                draft.draft_a,
                "",
                "Variant B:",
                draft.draft_b,
                "",
                "-" * 60,
                "",
            ]
        )
    return "\n".join(chunks)


def send_email(settings: Settings, drafts: list[PostDraft]) -> None:
    if not settings.can_send_email:
        logger.info("Email sending skipped")
        return

    message = EmailMessage()
    message["Subject"] = "Daily AI LinkedIn Drafts"
    message["From"] = settings.email_from or settings.smtp_user or ""
    message["To"] = settings.email_to or ""
    message.set_content(build_text_report(drafts))
    message.add_alternative(build_html_email(drafts), subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user or "", settings.smtp_password or "")
        smtp.send_message(message)
    logger.info("Email sent to {}", settings.email_to)


def send_test_email(settings: Settings) -> None:
    missing = [
        name
        for name, value in {
            "SMTP_HOST": settings.smtp_host,
            "SMTP_USER": settings.smtp_user,
            "SMTP_PASSWORD": settings.smtp_password,
            "EMAIL_TO": settings.email_to,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing SMTP settings: {', '.join(missing)}")

    message = EmailMessage()
    message["Subject"] = "AI News Scraper SMTP test"
    message["From"] = settings.email_from or settings.smtp_user or ""
    message["To"] = settings.email_to or ""
    message.set_content(
        "SMTP test passed. If you received this, AI News Scraper can send emails."
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user or "", settings.smtp_password or "")
        smtp.send_message(message)
    logger.info("SMTP test email sent to {}", settings.email_to)
