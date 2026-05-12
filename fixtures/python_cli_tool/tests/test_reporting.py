from src.reporting import summarize_rows


def test_summarize_rows():
    assert summarize_rows([{"name": "Ada", "city": "London"}]) == {"row_count": 1, "column_count": 2}
