from __future__ import annotations

import os
from pathlib import Path


class LLMUnavailable(RuntimeError):
    pass


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or Path.cwd() / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def complete(prompt: str, model: str = "gpt-4.1-mini", system: str | None = None) -> str:
    """Call OpenAI for agent differentiation and documentation generation."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
    if not api_key:
        raise LLMUnavailable("OPENAI_API_KEY or OPENAI_KEY is not set.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMUnavailable("Install the llm extra to use OpenAI.") from exc
    client = OpenAI(api_key=api_key)
    input_payload = prompt if system is None else [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    response = client.responses.create(model=model, input=input_payload)
    return response.output_text
