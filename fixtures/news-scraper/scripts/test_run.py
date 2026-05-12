from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["DRY_RUN"] = "true"

from main import run


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
