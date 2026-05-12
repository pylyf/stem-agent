from __future__ import annotations

from src.models import PostDraft, ScoredItem
from src.notifier import build_text_report


def test_text_report_contains_drafts() -> None:
    item = ScoredItem(
        url="https://example.com",
        title="AI agent launch",
        source="Example",
        summary="Summary",
        score=0.8,
    )
    report = build_text_report([PostDraft(item=item, draft_a="A", draft_b="B")])

    assert "AI agent launch" in report
    assert "Variant A" in report
    assert "Variant B" in report

