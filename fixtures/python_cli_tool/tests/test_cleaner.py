from src.cleaner import normalize_rows


def test_normalize_rows(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text(" name \n alice \n", encoding="utf-8")
    assert normalize_rows(str(path))[0]["name"] == "alice"
