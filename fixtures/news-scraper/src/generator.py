from __future__ import annotations

import re

from loguru import logger
from openai import AsyncOpenAI

from src.config import Settings
from src.models import PostDraft, ScoredItem


SYSTEM_PROMPT = """You are writing Czech LinkedIn posts on behalf of Filip, a 22-year-old AI developer
and consultant targeting Czech founders, freelancers, marketers, and SMB owners. He works on RAG systems,
LLM integrations, and AI automation for Czech businesses.

Language: Czech only. Do not write the post in English, except for unavoidable product names or technical terms.
Voice: technical but accessible, opinionated, first-person, practical, no corporate fluff.
Never use: "v dnešním rychle se měnícím světě", "game-changer", "revoluční", "s radostí oznamuji", "jsem nadšený".
Always use: specific numbers when available, personal takes, developer perspective, practical Czech-market relevance.

Post structure:
- Hook (1 Czech sentence: surprising fact, contrarian take, or specific number)
- Context (2-3 Czech sentences: what happened, why it matters for Czech companies or creators)
- Filip's take (2-3 Czech sentences: personal insight from his dev/consultant perspective)
- CTA or question (1 Czech sentence)
- 3-5 lowercase hashtags, Czech or widely used AI terms

Length: 120-220 Czech words. LinkedIn optimal engagement length."""


class DraftGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if settings.openai_api_key
            else None
        )

    async def generate(self, items: list[ScoredItem]) -> list[PostDraft]:
        drafts: list[PostDraft] = []
        for item in items:
            if self.settings.can_generate and self.client is not None:
                drafts.append(await self._generate_with_openai(item))
            else:
                drafts.append(self._generate_dry_run(item))
        return drafts

    async def _generate_with_openai(self, item: ScoredItem) -> PostDraft:
        prompt = f"""Here is a news item. The source content can be English, but the LinkedIn posts must be Czech.
Title: {item.title}
Source: {item.source}
Summary: {item.summary}
URL: {item.url}

Write a Czech LinkedIn post from Filip's perspective about this, tailored to the Czech market.
Generate 2 variants:
- Variant A: Educational/insight angle
- Variant B: Opinionated/take angle

Keep labels exactly "Variant A:" and "Variant B:"."""

        response = await self.client.responses.create(
            model=self.settings.openai_model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
            max_output_tokens=self.settings.openai_max_output_tokens,
            reasoning={"effort": self.settings.openai_reasoning_effort},
        )
        if response.status == "incomplete":
            reason = response.incomplete_details.reason if response.incomplete_details else "unknown"
            raise RuntimeError(
                "OpenAI returned an incomplete draft "
                f"(reason: {reason}, max_output_tokens: {self.settings.openai_max_output_tokens}). "
                "Increase OPENAI_MAX_OUTPUT_TOKENS or lower OPENAI_REASONING_EFFORT."
            )
        text = response.output_text
        draft_a, draft_b = split_variants(text)
        validate_drafts(draft_a, draft_b)
        tokens_used = None
        if response.usage is not None:
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
        return PostDraft(item=item, draft_a=draft_a, draft_b=draft_b, tokens_used=tokens_used)

    def _generate_dry_run(self, item: ScoredItem) -> PostDraft:
        logger.info("DRY_RUN: generating local placeholder draft for '{}'", item.title)
        hook = f"{item.title} stojí za pozornost, protože se dotýká reálných workflow, ne jen AI hype."
        context = item.summary or "Zdroj neposkytl detailní shrnutí."
        draft_a = f"""{hook}

{context}

Můj praktický pohled: zajímavý není samotný headline, ale to, jestli tahle věc umí ubrat ruční práci v RAG systémech, LLM integracích nebo automatizaci procesů. U českých firem bych to hodnotil jednou otázkou: odstraní to konkrétní krok z workflow, nebo jen přidá další dashboard?

Co byste u toho otestovali jako první, kdybyste měli 30 minut?

#ai #llm #automatizace #vyvoj"""
        draft_b = f"""Většina AI novinek je šum. Tohle má o něco jasnější signál: {item.title}

Z vývojářského pohledu mě méně zajímá oznámení a víc implementační detail. Pokud to zlepší latenci, spolehlivost, evaluaci nebo práci s nástroji, může to mít smysl i v produkci. Pokud to jen dobře vypadá v demu, rychle to zapadne.

Moje sázka: české firmy budou platit za AI nástroje, které šetří měřitelné hodiny. Ne za nástroje, které jen dobře vypadají v launch postu.

Brali byste to jako užitečnou infrastrukturu, nebo jen další experiment?

#ai #aiagenti #llm #automatizace"""
        return PostDraft(item=item, draft_a=draft_a, draft_b=draft_b)


def split_variants(text: str) -> tuple[str, str]:
    match = re.search(r"Variant A[:\-\s]*(.*?)(?:Variant B[:\-\s]*)(.*)", text, re.I | re.S)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return text.strip(), text.strip()


def validate_drafts(draft_a: str, draft_b: str) -> None:
    missing = []
    if not _looks_complete(draft_a):
        missing.append("Variant A")
    if not _looks_complete(draft_b):
        missing.append("Variant B")
    if missing:
        raise RuntimeError(
            "OpenAI returned an incomplete-looking draft: "
            + ", ".join(missing)
            + ". The draft is missing a hashtag block or is too short."
        )


def _looks_complete(text: str) -> bool:
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    return len(words) >= 60 and "#" in text[-160:]
