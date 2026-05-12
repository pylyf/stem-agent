from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import RawItem


class BaseFetcher(ABC):
    source_name: str

    @abstractmethod
    async def fetch(self) -> list[RawItem]:
        """Fetch news items from one source."""

