from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_settings
from src.notifier import send_test_email


def main() -> int:
    settings = load_settings()
    send_test_email(settings)
    print(f"SMTP test email sent to {settings.email_to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

