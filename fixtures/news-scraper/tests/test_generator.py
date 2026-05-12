from __future__ import annotations

import pytest

from src.generator import split_variants, validate_drafts


def test_split_variants() -> None:
    text = "Variant A: First draft\n\nVariant B: Second draft"

    draft_a, draft_b = split_variants(text)

    assert draft_a == "First draft"
    assert draft_b == "Second draft"


def test_validate_drafts_rejects_cut_off_text() -> None:
    complete = " ".join(["slovo"] * 65) + "\n\n#ai #automatizace"
    cut_off = "Jako vývojář a konzultant doporučuju přistupovat"

    with pytest.raises(RuntimeError, match="incomplete-looking"):
        validate_drafts(complete, cut_off)
