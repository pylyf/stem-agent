import csv


def normalize_rows(input_path: str, uppercase: bool = False) -> list[dict[str, str]]:
    with open(input_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    normalized = []
    for row in rows:
        item = {key.strip(): value.strip() for key, value in row.items()}
        if uppercase:
            item = {key: value.upper() for key, value in item.items()}
        normalized.append(item)
    return normalized
