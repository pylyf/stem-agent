from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_settings
from src.db import NewsDatabase


async def main() -> None:
    settings = load_settings()
    await NewsDatabase(settings.database_path).init()
    print(f"Database initialized: {settings.database_path}")


if __name__ == "__main__":
    asyncio.run(main())
