from __future__ import annotations

import json

from stem_doc_agent.llm import complete
from stem_doc_agent.scanner import RepoProfile


def run_basic_agent(profile: RepoProfile, model: str) -> str:
    prompt = f"""
You are a general documentation agent.

Write concise maintainer documentation for this repository. Use only the facts in the repository profile.

Rules:
- Do not invent files, commands, APIs, components, or frameworks.
- Mention setup commands only when they appear in setup_commands.
- Return only Markdown.

Repository profile:
{json.dumps(profile.to_dict(), indent=2)}
"""
    return complete(
        prompt,
        model=model,
        system="You write accurate repository documentation from provided facts only.",
    ).strip() + "\n"
