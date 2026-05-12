from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import AsyncOpenAI

from src.config import load_settings


async def main() -> int:
    settings = load_settings()
    if not settings.openai_api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in environment or .env")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.responses.create(
        model=settings.openai_model,
        instructions="You are a terse API smoke test. Reply in Czech.",
        input="Reply with exactly: OpenAI API funguje",
        max_output_tokens=80,
        reasoning={"effort": settings.openai_reasoning_effort},
    )
    print(response.output_text.strip())
    if response.usage is not None:
        total = response.usage.input_tokens + response.usage.output_tokens
        print(f"Model: {settings.openai_model} | Tokens: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
